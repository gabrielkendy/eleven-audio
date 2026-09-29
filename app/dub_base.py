"""Dublagem pela pipeline completa da base, em vez do caminho simplificado.

Por que existe: o caminho antigo (`app/dublar.py`) transcreve o audio inteiro,
traduz e sintetiza de uma vez. Ele nao preserva o tempo da fala nem mantem a
trilha. Este modulo usa o que a base ja tem e que so foi descoberto lendo o codigo
dela:

  - separacao de voz e fundo (demucs): `vocals.wav` + `no_vocals.wav`
  - transcricao com tempo POR PALAVRA e `speaker_id` (quem falou)
  - geracao por segmento, com a voz escolhida em `profile_id`
  - `timing_strategy`, que estica ou encolhe a fala para caber no tempo

Medido em 29/09/2026, num trecho de 10 s de portugues:

    original  segmentos: [0.87-4.28] e [4.28-9.98]
    dublado   segmentos: [0.85-4.08] e [4.27-9.50]
    duracao do dublado: 10.00 s, igual ao original

A ordem importa e nao e obvia: o upload e ASSINCRONO. Ele roda extract e demucs em
segundo plano e so aceita transcricao depois do evento `ready` no SSE. Transcrever
antes devolve "Job not found", que parece problema de identificador e nao e.

A traducao continua sendo feita por nos, com o modelo local: o `/dub/translate` da
base so tem o Argos pronto nesta maquina, e o provedor LLM dele exige chave paga.
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any

import httpx

from . import saidas, traducao
from .config import Configuracao

# A base limita o quanto a fala pode passar do tempo original do segmento.
ESTRATEGIAS_DE_TEMPO = ("concise", "stretch_video", "strict_slot", "smart_fit")
TEMPO_PADRAO = "smart_fit"

# O preparo roda demucs, que e o passo caro. 20 minutos cobre audio longo.
LIMITE_PREPARO_S = 1200.0
LIMITE_GERACAO_S = 3600.0


class ErroDublagemBase(Exception):
    """Falha na pipeline da base, com mensagem util para quem esta na tela."""


def _abrir(transporte: httpx.BaseTransport | None) -> httpx.Client:
    return httpx.Client(timeout=LIMITE_GERACAO_S, transport=transporte)


def enviar_audio(
    conteudo: bytes,
    nome_arquivo: str,
    config: Configuracao,
    idioma_origem: str = "",
    transporte: httpx.BaseTransport | None = None,
) -> dict[str, str]:
    """Sobe o audio. Devolve `job_id` e `task_id`; o preparo segue em segundo plano."""
    arquivos = {"video": (nome_arquivo, conteudo, "application/octet-stream")}
    dados = {"input_type": "audio"}
    if idioma_origem:
        # O source_lang alimenta a deteccao de idioma do transcritor da base, que
        # tambem so entende codigo valido. Com "pb" ele nao reconhecia.
        dados["source_lang"] = traducao.para_motor(idioma_origem)
    try:
        with _abrir(transporte) as cliente:
            resposta = cliente.post(
                f"{config.base_url}/dub/upload", files=arquivos, data=dados
            )
    except httpx.HTTPError as erro:
        raise ErroDublagemBase(f"nao consegui enviar o audio para a base: {erro}") from erro

    if resposta.status_code >= 400:
        raise ErroDublagemBase(
            f"a base recusou o audio ({resposta.status_code}): {_texto(resposta)}"
        )
    corpo = _json(resposta)
    if not corpo.get("job_id"):
        raise ErroDublagemBase("a base aceitou o audio mas nao devolveu o identificador")
    return {"job_id": str(corpo["job_id"]), "task_id": str(corpo.get("task_id") or "")}


def _texto(resposta: httpx.Response) -> str:
    try:
        corpo = resposta.json()
    except (json.JSONDecodeError, ValueError):
        return resposta.text[:300]
    if isinstance(corpo, dict) and "detail" in corpo:
        detalhe = corpo["detail"]
        return detalhe if isinstance(detalhe, str) else json.dumps(detalhe, ensure_ascii=False)
    return json.dumps(corpo, ensure_ascii=False)[:300]


def _json(resposta: httpx.Response) -> dict[str, Any]:
    try:
        corpo = resposta.json()
    except (json.JSONDecodeError, ValueError) as erro:
        raise ErroDublagemBase("a base devolveu uma resposta invalida") from erro
    if not isinstance(corpo, dict):
        raise ErroDublagemBase("a base devolveu um formato inesperado")
    return corpo


def acompanhar(
    task_id: str,
    config: Configuracao,
    limite_s: float,
    transporte: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    """Le o SSE da base ate o evento final. Devolve o ultimo evento.

    O evento `ready` e o que libera a transcricao. `done` fecha a geracao.
    """
    if not task_id:
        raise ErroDublagemBase("a base nao devolveu a tarefa para acompanhar")

    terminal = {"ready", "done", "complete", "completed", "error", "failed", "aborted"}
    ultimo: dict[str, Any] = {}
    try:
        with _abrir(transporte) as cliente, cliente.stream(
            "GET", f"{config.base_url}/tasks/stream/{task_id}"
        ) as fluxo:
            if fluxo.status_code >= 400:
                raise ErroDublagemBase(
                    f"nao consegui acompanhar o preparo ({fluxo.status_code})"
                )
            for linha in fluxo.iter_lines():
                texto = (linha or "").strip()
                if not texto or texto.startswith(":"):
                    continue
                if texto.startswith("data:"):
                    texto = texto[5:].strip()
                try:
                    evento = json.loads(texto)
                except json.JSONDecodeError:
                    continue
                if isinstance(evento, dict):
                    ultimo = evento
                    if str(evento.get("type", "")).lower() in terminal:
                        return evento
    except httpx.HTTPError as erro:
        raise ErroDublagemBase(f"a conexao com a base caiu durante o preparo: {erro}") from erro

    if not ultimo:
        raise ErroDublagemBase("a base nao mandou nenhum evento do preparo")
    return ultimo


def transcrever(
    job_id: str, config: Configuracao, transporte: httpx.BaseTransport | None = None
) -> dict[str, Any]:
    """Transcreve o job ja preparado. Cada segmento traz tempo e `speaker_id`."""
    try:
        with _abrir(transporte) as cliente:
            resposta = cliente.post(f"{config.base_url}/dub/transcribe/{job_id}")
    except httpx.HTTPError as erro:
        raise ErroDublagemBase(f"a transcricao falhou na base: {erro}") from erro

    if resposta.status_code >= 400:
        raise ErroDublagemBase(
            f"a base nao conseguiu transcrever ({resposta.status_code}): {_texto(resposta)}"
        )
    corpo = _json(resposta)
    if not corpo.get("segments"):
        raise ErroDublagemBase("a base nao encontrou fala nesse audio")
    return corpo


def gerar(
    job_id: str,
    segmentos: list[dict[str, Any]],
    destino: str,
    perfil_id: str,
    config: Configuracao,
    tempo: str = TEMPO_PADRAO,
    velocidade: float = 1.0,
    transporte: httpx.BaseTransport | None = None,
) -> str:
    """Gera o dublado. Devolve o `task_id` para acompanhar.

    `profile_id` vai em TODOS os segmentos de proposito: sem ele a base clona o
    falante original, o que e otimo para dublar outra pessoa e errado quando o
    pedido e sair na voz escolhida.
    """
    if tempo not in ESTRATEGIAS_DE_TEMPO:
        raise ErroDublagemBase(
            f"estrategia de tempo desconhecida: {tempo}. "
            f"Use uma destas: {', '.join(ESTRATEGIAS_DE_TEMPO)}"
        )
    if not segmentos:
        raise ErroDublagemBase("nao ha trechos para gerar")

    corpo = {
        "segments": [{**segmento, "profile_id": perfil_id} for segmento in segmentos],
        # O motor le `language` (nao `language_code`) para saber em que lingua
        # falar: dub_generate.py:2124 faz `lang = req.language` e entrega isso ao
        # backend. Aqui ia `traducao.nome(destino)`, ou seja "Portugues (Brasil)",
        # que o motor nao reconhece — TODA dublagem saia sem indicacao de idioma.
        "language": traducao.para_motor(destino),
        "language_code": traducao.para_motor(destino),
        "timing_strategy": tempo,
        "voice_match": "consistent",
        "speed": velocidade,
    }
    try:
        with _abrir(transporte) as cliente:
            resposta = cliente.post(f"{config.base_url}/dub/generate/{job_id}", json=corpo)
    except httpx.HTTPError as erro:
        raise ErroDublagemBase(f"a base nao aceitou gerar o audio: {erro}") from erro

    if resposta.status_code >= 400:
        raise ErroDublagemBase(
            f"a base recusou a geracao ({resposta.status_code}): {_texto(resposta)}"
        )
    return str(_json(resposta).get("task_id") or "")


def baixar(
    job_id: str,
    destino: Path,
    config: Configuracao,
    transporte: httpx.BaseTransport | None = None,
) -> int:
    """Baixa o dublado. Devolve o tamanho em bytes.

    Usa `/dub/download-audio`: `/dub/audio` devolve o material de ENTRADA, nao o
    dublado. Confundir os dois entrega o audio original com nome de dublado.
    """
    try:
        with _abrir(transporte) as cliente, cliente.stream(
            "GET", f"{config.base_url}/dub/download-audio/{job_id}"
        ) as fluxo:
            if fluxo.status_code >= 400:
                raise ErroDublagemBase(
                    f"a base nao entregou o audio dublado ({fluxo.status_code})"
                )
            destino.parent.mkdir(parents=True, exist_ok=True)
            with destino.open("wb") as saida:
                for pedaco in fluxo.iter_bytes():
                    saida.write(pedaco)
    except httpx.HTTPError as erro:
        raise ErroDublagemBase(f"a conexao caiu ao baixar o dublado: {erro}") from erro

    tamanho = destino.stat().st_size if destino.exists() else 0
    if tamanho < 1024:
        raise ErroDublagemBase("o audio dublado veio vazio")
    return tamanho


def _numero(valor: Any) -> float:
    """A base devolve `start`/`end` como TEXTO ('0.87'), nao como numero.

    Sem converter, o tempo vai como string para a geracao e o encaixe no tempo
    falha em silencio, entregando fala fora de sincronia.
    """
    try:
        return round(float(valor), 6)
    except (TypeError, ValueError):
        return 0.0


def _segmentos_para_gerar(
    segmentos: list[dict[str, Any]], traduzidos: list[str]
) -> list[dict[str, Any]]:
    """Junta o tempo de cada trecho com o texto traduzido."""
    prontos = []
    for original, texto in zip(segmentos, traduzidos, strict=True):
        prontos.append(
            {
                "id": original.get("id") or f"seg_{len(prontos)}",
                "text": texto,
                "start": _numero(original.get("start")),
                "end": _numero(original.get("end")),
                "speaker_id": original.get("speaker_id"),
            }
        )
    return prontos


def dublar_pela_base(
    *,
    conteudo: bytes,
    nome_arquivo: str,
    destino_idioma: str,
    perfil_id: str,
    config: Configuracao,
    origem_idioma: str = "",
    tradutor: str = "auto",
    tempo: str = TEMPO_PADRAO,
    transporte: httpx.BaseTransport | None = None,
    pasta_saida: Path | None = None,
) -> dict[str, Any]:
    """Pipeline completa: separa voz e fundo, transcreve, traduz, gera no tempo.

    A traducao roda aqui com o modelo local (ou o Argos, se pedido), porque o
    tradutor da base nesta maquina so tem o Argos, que erra tempo verbal.
    """
    alvo = traducao.normalizar(destino_idioma)
    if not alvo:
        raise ErroDublagemBase("escolha o idioma de destino")
    if alvo not in traducao.IDIOMAS:
        raise ErroDublagemBase(f"idioma de destino desconhecido: {destino_idioma}")

    envio = enviar_audio(conteudo, nome_arquivo, config, origem_idioma, transporte)
    job_id = envio["job_id"]

    preparo = acompanhar(envio["task_id"], config, LIMITE_PREPARO_S, transporte)
    if str(preparo.get("type", "")).lower() in {"error", "failed"}:
        raise ErroDublagemBase(f"o preparo do audio falhou: {preparo.get('message') or preparo}")

    transcricao = transcrever(job_id, config, transporte)
    segmentos = transcricao["segments"]

    # Nao confiamos no `source_lang` da base: medido em 29/09/2026, ela marcou
    # 'en' num audio claramente em portugues. Detectamos pelo proprio texto, com o
    # modelo local. Se nem isso resolver, paramos com recado claro, porque seguir
    # com o idioma errado produz audio errado e a pessoa so descobre ouvindo.
    idioma_origem = traducao.normalizar(origem_idioma)
    if not idioma_origem:
        texto_corrido = str(transcricao.get("full_transcript") or "").strip()
        if not texto_corrido:
            texto_corrido = " ".join(str(s.get("text") or "") for s in segmentos).strip()
        if texto_corrido:
            deteccao = traducao.detectar_idioma(texto_corrido, config, transporte=transporte)
            if deteccao.get("detectado"):
                idioma_origem = traducao.normalizar(str(deteccao.get("codigo") or ""))
    if not idioma_origem:
        raise ErroDublagemBase(
            "nao consegui descobrir em que idioma o audio esta. "
            "Escolha o idioma de origem na mao e mande de novo."
        )
    if idioma_origem == alvo:
        raise ErroDublagemBase(
            f"o audio ja esta em {traducao.nome(alvo)}; escolha outro idioma de destino"
        )

    traduzidos: list[str] = []
    motores: set[str] = set()
    for segmento in segmentos:
        feita = traducao.traduzir(
            str(segmento.get("text") or ""), idioma_origem, alvo, config, transporte,
            motor=tradutor,
        )
        traduzidos.append(str(feita["texto"]))
        motores.add(str(feita.get("motor") or tradutor))

    tarefa = gerar(
        job_id, _segmentos_para_gerar(segmentos, traduzidos), alvo, perfil_id,
        config, tempo, transporte=transporte,
    )
    fecho = acompanhar(tarefa, config, LIMITE_GERACAO_S, transporte)
    if str(fecho.get("type", "")).lower() in {"error", "failed"}:
        raise ErroDublagemBase(f"a geracao falhou: {fecho.get('message') or fecho}")

    if pasta_saida is None:
        pasta_saida = saidas.pasta_do_dia(config.saidas)
    caminho = pasta_saida / f"{uuid.uuid4().hex[:8]}_dublado-base-{alvo}.wav"
    tamanho = baixar(job_id, caminho, config, transporte)

    falantes = sorted({str(s.get("speaker_id")) for s in segmentos if s.get("speaker_id")})
    return {
        "arquivo": str(caminho),
        "job_id": job_id,
        "origem": idioma_origem,
        "origem_nome": traducao.nome(idioma_origem),
        "destino": alvo,
        "destino_nome": traducao.nome(alvo),
        "tradutor": ", ".join(sorted(motores)),
        "pedacos": len(segmentos),
        "falantes": falantes,
        "varios_falantes": len(falantes) > 1,
        "timing": tempo,
        "tamanho_bytes": tamanho,
        "texto_traduzido": " ".join(traduzidos),
        "texto_original": " ".join(str(s.get("text") or "") for s in segmentos),
        "sync_scores": fecho.get("sync_scores"),
        "perfil_id": perfil_id,
    }


def limpar_job(job_id: str, config: Configuracao, transporte: httpx.BaseTransport | None = None) -> bool:
    """Apaga o job da base. Falha aqui nao pode derrubar a dublagem ja entregue."""
    try:
        with _abrir(transporte) as cliente:
            resposta = cliente.delete(f"{config.base_url}/dub/history/{job_id}")
        return resposta.status_code < 400
    except httpx.HTTPError:
        return False


def copiar_para(caminho: Path, destino: Path) -> Path:
    """Copia o dublado, preservando o original gerado pela base."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(caminho, destino)
    return destino
