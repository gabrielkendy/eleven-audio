from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from app.cofre import abrir
from app.config import Configuracao
from app.motor import sintetizar
from app.saidas import gravar_bytes, medir, nome_arquivo, pasta_do_dia


class ComparacaoErro(Exception):
    pass


def _relativo(caminho: Path, config: Configuracao) -> str:
    try:
        return caminho.resolve().relative_to(config.dados.parent.resolve()).as_posix()
    except ValueError:
        return str(caminho.resolve())


def _motivos(client: httpx.Client, motores: list[str]) -> dict[str, dict[str, Any]]:
    reais = [motor for motor in motores if motor != "mock"]
    if not reais:
        return {}
    resposta = client.get("/engines/tts")
    resposta.raise_for_status()
    catalogo = {item["id"]: item for item in resposta.json().get("backends", [])}
    for motor in reais:
        item = catalogo.get(motor)
        if not item:
            raise ComparacaoErro(f"Motor {motor} indisponivel: motor nao informado pela base")
        if not item.get("available"):
            raise ComparacaoErro(f"Motor {motor} indisponivel: {item.get('reason') or item.get('last_error') or 'motivo nao informado pela base'}")
    return catalogo


def _audio_da_resposta(client: httpx.Client, resposta: httpx.Response) -> bytes:
    tipo = resposta.headers.get("content-type", "")
    if tipo.startswith("audio/") or resposta.content[:4] == b"RIFF":
        return resposta.content
    dados = resposta.json()
    url = dados.get("audio_url") or dados.get("url")
    if not url and dados.get("audio_id"):
        url = f"/audio/{dados['audio_id']}.wav"
    if not url:
        raise ComparacaoErro("A base gerou o audio, mas nao informou o caminho do arquivo")
    audio = client.get(url)
    audio.raise_for_status()
    return audio.content


def _gerar_real(
    *,
    client: httpx.Client,
    config: Configuracao,
    texto: str,
    perfil_na_base: str,
    perfil_id: str,
    motor: str,
    dispositivo: str,
) -> dict[str, Any]:
    inicio = time.perf_counter()
    resposta = client.post(
        "/generate",
        files={
            "text": (None, texto),
            "profile_id": (None, perfil_na_base),
            "engine": (None, motor),
            "language": (None, "pt"),
            "speed": (None, "1.0"),
            "seed": (None, "42"),
            "effect_preset": (None, "broadcast"),
        },
    )
    try:
        resposta.raise_for_status()
    except httpx.HTTPStatusError as erro:
        try:
            detalhe = resposta.json().get("detail") or resposta.json().get("error") or resposta.text
        except ValueError:
            detalhe = resposta.text
        raise ComparacaoErro(str(detalhe)) from erro
    duracao_geracao = time.perf_counter() - inicio
    destino = pasta_do_dia(config.saidas) / nome_arquivo(motor, perfil_id)
    gravar_bytes(destino, _audio_da_resposta(client, resposta))
    return {
        **medir(destino),
        "caminho_absoluto": str(destino.resolve()),
        "duracao_geracao_s": round(duracao_geracao, 6),
        "motor": motor,
        "dispositivo": dispositivo,
    }


def comparar(
    *,
    texto: str,
    perfil_id: str,
    motores: list[str],
    config: Configuracao,
    transporte: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    """Gera o par e guarda seus ids em configuracao: grupo_comparacao:<grupo_id>."""
    texto = texto.strip()
    if not texto or len(texto) > 5_000:
        raise ValueError("texto deve ter entre 1 e 5000 caracteres")
    if len(motores) != 2 or motores[0] == motores[1]:
        raise ValueError("informe dois motores diferentes")

    cofre = abrir(config.dados / "estudio.db")
    try:
        perfil = cofre.perfil(perfil_id)
    finally:
        cofre.fechar()
    if not perfil:
        raise ValueError("perfil_id nao encontrado")

    try:
        with httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout_s,
            transport=transporte,
            follow_redirects=True,
        ) as client:
            catalogo = _motivos(client, motores)
            arquivos = []
            for motor in motores:
                if motor == "mock":
                    # sintetizar ja aplica a pasta do dia; nao repetir aqui
                    item = sintetizar(texto, motor="mock", pasta_saida=config.saidas, perfil_id=perfil_id)
                    item["caminho_absoluto"] = str(Path(item["arquivo"]).resolve())
                else:
                    item = _gerar_real(
                        client=client,
                        config=config,
                        texto=texto,
                        perfil_na_base=perfil["id_na_base"],
                        perfil_id=perfil_id,
                        motor=motor,
                        dispositivo=catalogo[motor].get("effective_device") or "desconhecido",
                    )
                arquivos.append(item)
    except (httpx.HTTPError, OSError, ValueError) as erro:
        detalhe = getattr(getattr(erro, "response", None), "text", "") or str(erro)
        raise ComparacaoErro(detalhe) from erro

    grupo_id = f"cmp-{uuid.uuid4().hex[:12]}"
    cofre = abrir(config.dados / "estudio.db")
    try:
        geracoes = []
        for item in arquivos:
            caminho = Path(item.get("arquivo") or item["caminho_absoluto"])
            arquivo = _relativo(caminho, config)
            geracao_id = cofre.registrar_geracao(
                motor=item["motor"],
                texto_entrada=texto,
                arquivo_saida=arquivo,
                duracao_audio_s=item["duracao_audio_s"],
                duracao_geracao_s=item["duracao_geracao_s"],
                dispositivo=item["dispositivo"],
                tamanho_bytes=item["tamanho_bytes"],
                perfil_id=perfil_id,
            )
            item.update({"geracao_id": geracao_id, "arquivo": arquivo, "audio_url": f"/api/comparar/{grupo_id}/audio/{geracao_id}"})
            geracoes.append(geracao_id)
        cofre.gravar_config(f"grupo_comparacao:{grupo_id}", geracoes)
    finally:
        cofre.fechar()
    return {"grupo_id": grupo_id, "texto": texto, "perfil_id": perfil_id, "arquivos": arquivos}


def buscar(grupo_id: str, config: Configuracao) -> dict[str, Any] | None:
    cofre = abrir(config.dados / "estudio.db")
    try:
        ids = cofre.ler_config(f"grupo_comparacao:{grupo_id}")
        if not isinstance(ids, list) or len(ids) != 2:
            return None
        arquivos = [cofre.geracao(geracao_id) for geracao_id in ids]
    finally:
        cofre.fechar()
    if not all(arquivos):
        return None
    for item in arquivos:
        item["audio_url"] = f"/api/comparar/{grupo_id}/audio/{item['id']}"
    return {"grupo_id": grupo_id, "texto": arquivos[0]["texto_entrada"], "perfil_id": arquivos[0]["perfil_id"], "arquivos": arquivos}
