"""Áudio -> áudio: transcreve, traduz e fala de novo, na mesma voz.

Como funciona, em quatro passos:
    1. o transcritor da base ouve o áudio e devolve o texto **e o idioma**
    2. o texto é traduzido para o idioma pedido (com cascata pelo inglês)
    3. o motor de voz fala o texto traduzido usando o perfil clonado
    4. os pedaços são juntados num arquivo só

Por que não usar o dublador da própria base (SoniTranslate): ele tem o próprio
ambiente, um servidor separado na porta 7860, e está **não instalado** nesta
máquina. Fazendo aqui, o áudio sai na **sua voz clonada**, que é o ponto do
projeto, e não numa voz genérica do dublador. Além disso aproveita o preparo de
referência que já mede 0,8025 de fidelidade contra 0,7404 sem.

Texto comprido é dividido em pedaços: motores de voz degradam ou recusam textos
longos, e um pedaço que falha não pode derrubar o resto.
"""
from __future__ import annotations

import re
import wave
from pathlib import Path
from typing import Any

from app import base, saidas, traducao
from app.config import Configuracao
from app.motor import sintetizar
from app.transcricao import ErroTranscricao, guardar_arquivo, transcrever

# Acima disto o texto é dividido. Medido: frases de até ~300 caracteres geram
# bem em todos os motores; muito além disso alguns começam a cortar o fim.
TETO_CARACTERES = 280


class ErroDublagem(Exception):
    """Falha ao dublar."""


def dividir_texto(texto: str, teto: int = TETO_CARACTERES) -> list[str]:
    """Divide em pedaços por fim de frase, sem cortar palavra no meio.

    Nunca devolve pedaço vazio, e nunca perde texto: o que sobrar vai no último.
    """
    limpo = re.sub(r"\s+", " ", texto).strip()
    if not limpo:
        return []
    if len(limpo) <= teto:
        return [limpo]

    # quebra depois de . ! ? … mantendo o sinal junto do pedaço
    frases = re.split(r"(?<=[.!?…])\s+", limpo)
    pedacos: list[str] = []
    atual = ""
    for frase in frases:
        frase = frase.strip()
        if not frase:
            continue
        if len(frase) > teto:
            # frase sozinha maior que o teto: quebra por vírgula e, se precisar, no espaço
            if atual:
                pedacos.append(atual)
                atual = ""
            sub = _quebrar_longa(frase, teto)
            pedacos.extend(sub[:-1])
            atual = sub[-1]
            continue
        proposta = f"{atual} {frase}".strip() if atual else frase
        if len(proposta) <= teto:
            atual = proposta
        else:
            pedacos.append(atual)
            atual = frase
    if atual:
        pedacos.append(atual)
    return [p for p in pedacos if p]


def _quebrar_longa(frase: str, teto: int) -> list[str]:
    """Quebra uma frase gigante, primeiro por vírgula, depois por espaço."""
    for separador in (",", ";", ":"):
        if separador in frase:
            partes = [p.strip() for p in frase.split(separador) if p.strip()]
            if all(len(p) <= teto for p in partes):
                return [f"{p}{separador}" if i < len(partes) - 1 else p
                        for i, p in enumerate(partes)]
    palavras = frase.split(" ")
    pedacos: list[str] = []
    atual = ""
    for palavra in palavras:
        proposta = f"{atual} {palavra}".strip() if atual else palavra
        if len(proposta) <= teto:
            atual = proposta
        else:
            if atual:
                pedacos.append(atual)
            atual = palavra
    if atual:
        pedacos.append(atual)
    return pedacos or [frase[:teto]]


def juntar_wavs(caminhos: list[Path], destino: Path) -> Path:
    """Junta vários WAV do mesmo formato num só, sem recodificar.

    Exige o mesmo formato em todos, porque misturar taxas num arquivo só produz
    áudio com velocidade errada. Se algum destoar, o erro diz qual.
    """
    if not caminhos:
        raise ErroDublagem("nada para juntar")
    if len(caminhos) == 1:
        return saidas.gravar_bytes(destino, caminhos[0].read_bytes())

    with wave.open(str(caminhos[0]), "rb") as primeiro:
        formato = (primeiro.getnchannels(), primeiro.getsampwidth(), primeiro.getframerate())

    reservado, arquivo = saidas.abrir_destino_exclusivo(destino)
    try:
        with arquivo, wave.open(arquivo, "wb") as saida:
            saida.setnchannels(formato[0])
            saida.setsampwidth(formato[1])
            saida.setframerate(formato[2])
            for caminho in caminhos:
                with wave.open(str(caminho), "rb") as leitor:
                    atual = (leitor.getnchannels(), leitor.getsampwidth(), leitor.getframerate())
                    if atual != formato:
                        raise ErroDublagem(
                            f"formatos diferentes: {caminhos[0].name} é {formato}, "
                            f"{caminho.name} é {atual}"
                        )
                    saida.writeframes(leitor.readframes(leitor.getnframes()))
    except Exception:
        reservado.unlink(missing_ok=True)
        raise
    return reservado


def _limpar_pedacos(caminhos: list[Path]) -> None:
    """Apaga os pedaços temporários, ignorando o que já não existe."""
    for caminho in caminhos:
        try:
            caminho.unlink(missing_ok=True)
        except OSError:
            pass


def dublar(
    *,
    arquivo: Any,
    nome_arquivo: str,
    destino_idioma: str,
    config: Configuracao,
    perfil_id: str | None = None,
    origem_idioma: str = "",
    motor: str = "omnivoice",
    tradutor: str = "auto",
    velocidade: float = 1.0,
    semente: int | None = 2026,
    transporte: Any = None,
) -> dict[str, Any]:
    """Dubla: áudio de entrada -> áudio no idioma de destino, na voz escolhida.

    `motor` é o motor de VOZ (quem fala). `tradutor` é quem traduz o texto:
    `"auto"` usa o modelo local e cai no Argos, `"llm"` pede o modelo local,
    `"argos"` usa só o tradutor offline.
    """
    alvo = traducao.normalizar(destino_idioma)
    if not alvo:
        raise ErroDublagem("escolha o idioma de destino")
    # Validar aqui, antes de transcrever: sem isto, um idioma escrito errado só
    # aparecia depois da transcrição inteira, e como ErroTraducao não era tratado,
    # virava 500 Internal Server Error em vez de uma mensagem dizendo o problema.
    if alvo not in traducao.IDIOMAS:
        raise ErroDublagem(
            f"idioma de destino desconhecido: {destino_idioma}. "
            f"O estúdio traduz para {len(traducao.IDIOMAS)} idiomas."
        )
    if origem_idioma.strip():
        fonte_pedida = traducao.normalizar(origem_idioma)
        if not fonte_pedida:
            raise ErroDublagem("idioma de origem desconhecido")
        if fonte_pedida not in traducao.IDIOMAS:
            raise ErroDublagem(f"idioma de origem desconhecido: {origem_idioma}")

    # 1) transcrição. Quando o idioma de origem não vem, pedimos "auto": medido em
    # 29/09/2026, o campo `language` que a base devolve é apenas ECO do que foi
    # enviado (mandando "pt" num áudio em inglês, ela respondia "pt"), então ele
    # não serve como detecção. O texto transcrito vem certo nos três casos.
    fonte_pedida = traducao.normalizar(origem_idioma)
    caminho_entrada: Path | None = None
    try:
        caminho_entrada = guardar_arquivo(arquivo, nome_arquivo, config.dados)
        escuta = transcrever(caminho_entrada, fonte_pedida or "auto", config, transporte)
    except ErroTranscricao as erro:
        raise ErroDublagem(f"não deu para entender o áudio de entrada: {erro}") from erro
    finally:
        if caminho_entrada is not None:
            caminho_entrada.unlink(missing_ok=True)

    texto_original = str(escuta.get("texto") or "").strip()
    if not texto_original:
        raise ErroDublagem("o áudio de entrada não tem fala reconhecível")

    # Fonte: o que o usuário escolheu; senão, o que o detector de texto achar
    fonte = fonte_pedida
    deteccao: dict[str, Any] = {}
    if not fonte:
        deteccao = traducao.detectar_idioma(texto_original, config, transporte=transporte)
        if deteccao.get("detectado"):
            fonte = str(deteccao["codigo"])
    if not fonte:
        raise ErroDublagem(
            "não consegui descobrir o idioma do áudio de entrada. "
            'Escolha o idioma no campo "Áudio está em" e tente de novo. '
            f"({deteccao.get('motivo', 'detecção indisponível')})"
        )

    # 2) tradução
    try:
        traducao_feita = traducao.traduzir(
            texto_original, fonte, alvo, config, transporte, motor=tradutor
        )
    except traducao.ErroTraducao as erro:
        # Sem este tratamento, qualquer falha do tradutor (pacote de idioma
        # faltando, por exemplo) subia como erro interno e a tela mostrava
        # "500 Internal Server Error" em vez do motivo.
        raise ErroDublagem(f"não deu para traduzir: {erro}") from erro
    texto_traduzido = str(traducao_feita["texto"])
    if fonte == alvo:
        # já está no idioma pedido: nada a traduzir, mas ainda vale refalar
        texto_traduzido = texto_original

    # 3) fala, em pedaços
    pedacos = dividir_texto(texto_traduzido)
    if not pedacos:
        raise ErroDublagem("a tradução saiu vazia")

    pasta_dia = saidas.pasta_do_dia(config.saidas)
    gerados: list[Path] = []
    tempos: list[float] = []
    try:
        for indice, pedaco in enumerate(pedacos):
            resultado = sintetizar(
                pedaco,
                motor=motor,
                pasta_saida=config.saidas,
                perfil_id=perfil_id,
                config=config,
                idioma=alvo,
                velocidade=velocidade,
                semente=semente,
                ajustes=base.PADROES_FIEIS,
            )
            gerados.append(Path(resultado["arquivo"]))
            tempos.append(float(resultado.get("duracao_geracao_s") or 0.0))
    except (base.ErroBase, ValueError) as erro:
        _limpar_pedacos(gerados)
        raise ErroDublagem(f"o motor de voz recusou a fala traduzida: {erro}") from erro

    # 4) junta tudo num arquivo só
    final = pasta_dia / saidas.nome_arquivo(f"dublado-{motor}", perfil_id).replace(
        ".wav", f"-{alvo}.wav"
    )
    try:
        final = juntar_wavs(gerados, final)
    except ErroDublagem:
        _limpar_pedacos(gerados)
        raise
    if len(gerados) > 1:
        _limpar_pedacos(gerados)

    medicao = saidas.medir(final)
    return {
        "arquivo": str(final),
        "texto_original": texto_original,
        "texto_traduzido": texto_traduzido,
        "origem": fonte,
        "origem_nome": traducao.nome(fonte),
        "destino": alvo,
        "destino_nome": traducao.nome(alvo),
        "caminho_traducao": traducao_feita.get("caminho") or [],
        "saltos": traducao_feita.get("saltos", 0),
        "observacao": traducao_feita.get("observacao"),
        "pedacos": len(pedacos),
        "duracao_audio_s": medicao["duracao_audio_s"],
        "tamanho_bytes": medicao["tamanho_bytes"],
        "duracao_geracao_s": round(sum(tempos), 6),
        "motor": motor,
        "tradutor": traducao_feita.get("motor", tradutor),
        "perfil_id": perfil_id,
        # Não reportamos o `language` da base como "detectado": ele é eco do que
        # enviamos, não detecção. O que vale é como a origem foi decidida.
        #
        # Também NÃO devolvemos o campo `bruto`: ele guarda a resposta crua do
        # modelo, que às vezes traz o rascunho interno em inglês ("The user wants
        # me to identify the language..."). Isso ia para a tela do aluno. O que
        # interessa é o nome do idioma, que já vem em `nome`.
        "origem_decidida_por": "escolhida por você" if fonte_pedida else (
            f"detectada no texto como {deteccao.get('nome') or deteccao.get('codigo') or 'idioma desconhecido'}"
            if deteccao.get("detectado") else "não informada"
        ),
    }
