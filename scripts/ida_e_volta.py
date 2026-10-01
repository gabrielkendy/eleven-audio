"""Ida e volta: gera audio de uma frase conhecida e confere se o app entende.

Nao e teste de unidade. E o teste que responde a pergunta que importa para quem
usa: "o que eu falo voltou escrito certo?". Unidade prova que a funcao foi
chamada; isto prova que o texto ATRAVESSOU o app inteiro e voltou coerente.

Percorre a cadeia completa, cada etapa conferida contra o que se esperava:

    1. GERAR      frase de controle -> WAV (motor de verdade, nao o mock)
    2. TRANSCREVER esse WAV -> texto, comparado palavra a palavra com a frase
    3. DUBLAR      o mesmo WAV para ingles -> WAV novo em ingles
    4. CONFERIR    o WAV dublado tem sinal (nao e silencio nem arquivo vazio)
    5. TRANSCREVER o WAV dublado -> texto em ingles, conferido de novo

A frase de controle tem de proposito: "aco" (o par minimo que ja apareceu
errado como "acido" no historico deste projeto), cedilha, nasal, acento
agudo, til e um numero falado.

Um `.wav` de 5 segundos que transcreve certo e uma coisa. Isto aqui pega o que
unidade nao pega: motor trocado calado, chave de payload ignorada em silencio,
retorno com forma diferente, audio que sai mudo.

Uso:
    env -u PYTHONPATH <venv>/Scripts/python.exe scripts/ida_e_volta.py
    env -u PYTHONPATH <venv>/Scripts/python.exe scripts/ida_e_volta.py --motor mock
    env -u PYTHONPATH <venv>/Scripts/python.exe scripts/ida_e_volta.py --guardar

Sai 0 quando a cadeia fecha e 1 quando nao fecha, para poder entrar em hook de
pre-push. Precisa do app no ar (127.0.0.1:7800) e da base no ar (3900).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import uuid
import wave
from pathlib import Path

APP = os.environ.get("ELEVEN_AUDIO_URL", "http://127.0.0.1:7800").rstrip("/")

# Frase de controle. Mexer aqui exige mexer no esperado logo abaixo.
#
# Sem versao em ingles de proposito: o tradutor parafraseia ("in Manchester" virou
# "from Manchester", "aço" virou "steel"), e comparar com uma frase fixa mediria a
# escolha de palavra dele, nao a saude da cadeia.
FRASE = "O aco do Manchester e forte. A menina poe o microfone na mesa e le o numero tres."

falhas: list[str] = []
passos: list[str] = []


def ok(texto: str) -> None:
    passos.append(f"  [ OK ] {texto}")


def falha(texto: str) -> None:
    falhas.append(texto)
    passos.append(f"  [FALHA] {texto}")


def normalizar(texto: str) -> list[str]:
    """Compara por PALAVRA, sem acento e sem maiuscula.

    Pontuacao nao conta e numero escrito e numero falado sao a mesma coisa: o
    transcritor devolve "3" onde se falou "tres" e isso esta certo, nao e erro.
    """
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    palavras = re.split(r"[^a-z0-9]+", sem_acento.lower())
    return [NUMEROS.get(p, p) for p in palavras if p]


# "tres" e "3" sao a mesma palavra para quem le. Sem isto o comparador acusa erro
# onde o app acertou.
NUMEROS = {
    "zero": "0", "um": "1", "uma": "1", "dois": "2", "duas": "2", "tres": "3",
    "quatro": "4", "cinco": "5", "seis": "6", "sete": "7", "oito": "8",
    "nove": "9", "dez": "10",
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
}

# Onde fica a fronteira entre "a cadeia quebrou" e "o modelo tropecou".
#
# MEDIDO, nao chutado. Mesma frase, mesma maquina, 6 rodadas em 30/09: o transcritor
# entregou de 83% a 100%, e o pior caso foi "poe"->"apoia", "le"->"lhe", "tres"->"13"
# de uma vez so. Errar 3 palavras de 18 e comportamento normal deste modelo.
#
# Por isso o limiar e 60% e nao 85%: qualquer coisa acima do pior caso medido e
# comportamento esperado, e um portao dentro da faixa de ruido so gera alarme falso.
# O que este script protege e a CADEIA (motor trocado calado, payload ignorado, audio
# mudo, idioma errado) -- isso derruba a proporcao para perto de zero.
#
# O numero exato sai impresso em toda rodada para dar para ver degradacao a olho.
LIMIAR = 0.60

# Palavras que NENHUMA traducao fiel pode perder. O ingles e etapa derivada: ele
# carrega todo erro do portugues e ainda amplifica (uma palavra ouvida errado vira
# duas ou tres em ingles). Medido em 30/09: o mesmo audio deu 89% numa rodada e 83%
# na seguinte, sem nada quebrado no app -- o transcritor so ouviu "apoia" onde o
# gerador falou "poe", e o tradutor traduziu fielmente a palavra errada.
#
# Entao a comparacao palavra a palavra vale para o PORTUGUES, que e leitura direta
# do audio. Para o ingles, o que se exige e que o sentido sobreviva: se o assunto
# continua sendo o aco do Manchester e a menina com o microfone na mesa, a cadeia
# esta de pe. Palavra solta diferente e ruido do modelo, nao defeito.
CONTEUDO = ("steel", "manchester", "strong", "girl", "microphone", "table", "number")

# Piso, nao meta. Medido em 30/09: numa rodada o tradutor deixou "forte" em portugues
# e engoliu o "na mesa" -- 5 de 7. Isso e qualidade de modelo, nao cadeia quebrada.
# O piso existe para pegar colapso de verdade: audio dublado mudo, saida em outro
# idioma, traducao vazia. Se o sentido de base sumiu, a cadeia quebrou.
PISO_CONTEUDO = 4


def conferir_conteudo(rotulo: str, obtido: str) -> None:
    """O sentido sobreviveu o bastante para a cadeia estar de pe?

    Nao reprova por palavra solta: reporta quantas passaram. Reprova so no colapso.
    """
    vindas = normalizar(obtido)
    faltando = [p for p in CONTEUDO if p not in vindas]
    presentes = len(CONTEUDO) - len(faltando)
    if presentes >= PISO_CONTEUDO:
        ok(f"{rotulo}: {presentes}/{len(CONTEUDO)} palavras de conteudo")
        if faltando:
            print(f"         observacao: nao sobreviveu {faltando}")
    else:
        falha(f"{rotulo}: so {presentes}/{len(CONTEUDO)} palavras de conteudo -- COLAPSO")
        falha(f"    obtido: {vindas}")


def comparar(rotulo: str, alvo: str, obtido: str) -> None:
    """Quanto da frase de controle sobreviveu? Reporta sempre, reprova no colapso.

    Medido em 30/09 nesta maquina, mesma frase, 6 rodadas: o transcritor entregou
    entre 83% e 100%. Nao existe limiar apertado que separe "quebrou" de "o modelo
    tropecou" nessa faixa, entao o veredito sai do colapso e o numero sai sempre.
    """
    esperadas, vindas = normalizar(alvo), normalizar(obtido)
    if not esperadas:
        falha(f"{rotulo}: a frase de controle ficou vazia")
        return
    # Ordem nao importa muito; interessa quantas palavras do alvo apareceram.
    faltando = [p for p in esperadas if p not in vindas]
    acertos = len(esperadas) - len(faltando)
    proporcao = acertos / len(esperadas)
    if not faltando:
        ok(f"{rotulo}: {len(esperadas)} palavras, todas certas")
    elif proporcao >= LIMIAR:
        ok(f"{rotulo}: {acertos}/{len(esperadas)} palavras ({proporcao:.0%})")
        passos.append(f"         observacao: o transcritor ouviu {faltando} diferente")
    else:
        sobrando = [p for p in vindas if p not in esperadas]
        falha(f"{rotulo}: so {acertos}/{len(esperadas)} palavras ({proporcao:.0%}) -- COLAPSO")
        falha(f"    alvo:   {esperadas}")
        falha(f"    obtido: {vindas}")
        if sobrando:
            falha(f"    apareceu o que nao foi falado: {sobrando}")


def multpart(campos: dict[str, str], arquivo: Path | None, nome_campo: str = "arquivo"):
    """Monta multipart/form-data a mao: sem dependencia, e o app come cru."""
    b = "----ida-e-volta" + uuid.uuid4().hex
    partes: list[bytes] = []
    for chave, valor in campos.items():
        partes.append(
            f'--{b}\r\nContent-Disposition: form-data; name="{chave}"\r\n\r\n{valor}\r\n'.encode()
        )
    if arquivo is not None:
        partes.append(
            f'--{b}\r\nContent-Disposition: form-data; name="{nome_campo}"; '
            f'filename="{arquivo.name}"\r\nContent-Type: audio/wav\r\n\r\n'.encode()
        )
        partes.append(arquivo.read_bytes())
    partes.append(f"\r\n--{b}--\r\n".encode())
    return b"".join(partes), f"multipart/form-data; boundary={b}"


def pedir(caminho: str, corpo: bytes, tipo: str, limite: int) -> dict:
    req = urllib.request.Request(APP + caminho, data=corpo, headers={"Content-Type": tipo})
    with urllib.request.urlopen(req, timeout=limite) as resposta:
        return json.loads(resposta.read())


def sobra_de_sinal(caminho: Path) -> tuple[bool, str]:
    """O WAV tem audio de verdade dentro?

    Header valido nao prova sinal: um WAV de 5 s pode estar todo em zero. Le as
    amostras e mede pico e RMS, que e o que separa "arquivo existe" de "audio
    existe".
    """
    try:
        with wave.open(str(caminho), "rb") as w:
            canais, taxa, largura, quadros = (
                w.getnchannels(),
                w.getframerate(),
                w.getsampwidth(),
                w.getnframes(),
            )
            bruto = w.readframes(quadros)
    except (wave.Error, OSError) as erro:
        return False, f"nao abriu como WAV: {erro}"
    if largura != 2:
        return False, f"esperava 16 bits, veio {largura * 8}"
    import struct

    amostras = struct.unpack(f"<{len(bruto) // 2}h", bruto[: len(bruto) // 2 * 2])
    if not amostras:
        return False, "sem amostras"
    pico = max(abs(a) for a in amostras)
    rms = (sum(a * a for a in amostras) / len(amostras)) ** 0.5
    dur = quadros / taxa
    resumo = f"{dur:.2f}s {taxa}Hz {canais}ch pico={pico} rms={rms:.0f}"
    if pico < 1000 or rms < 50:
        return False, f"silencioso -> {resumo}"
    return True, resumo


def main() -> int:
    parser = argparse.ArgumentParser(description="Ida e volta de gerar, transcrever e dublar.")
    parser.add_argument("--motor", default="omnivoice", help="motor de sintese (padrao: omnivoice)")
    parser.add_argument("--perfil-id", default="", help="perfil local exigido por motores clonados")
    parser.add_argument("--guardar", action="store_true", help="nao apaga o WAV no fim")
    parser.add_argument("--limite", type=int, default=900, help="segundos por etapa")
    args = parser.parse_args()

    try:
        with urllib.request.urlopen(APP + "/api/estado", timeout=30) as r:
            estado = json.loads(r.read())
    except (urllib.error.URLError, OSError) as erro:
        print(f"app nao respondeu em {APP}: {erro}")
        print("suba o app antes de rodar isto.")
        return 1

    disponiveis = {m["id"] for m in estado.get("motores", []) if m.get("disponivel")}
    if args.motor not in disponiveis:
        print(f"motor {args.motor!r} nao esta disponivel. Tem: {sorted(disponiveis)}")
        return 1

    print(f"motor: {args.motor}")
    print(f"frase de controle: {FRASE}")
    print()

    gerado: Path | None = None
    dublado: Path | None = None
    try:
        print("1) GERAR")
        t0 = time.time()
        r = pedir(
            "/api/gerar",
            json.dumps({"texto": FRASE, "motor": args.motor, "perfil_id": args.perfil_id}).encode(),
            "application/json",
            args.limite,
        )
        gerado = Path(r["arquivo"])
        if not gerado.is_file():
            falha(f"a resposta apontou {gerado}, que nao existe")
            return resumir()
        bom, resumo = sobra_de_sinal(gerado)
        (ok if bom else falha)(f"audio gerado: {resumo}")
        print(f"   {gerado.name} em {time.time() - t0:.1f}s")
        print()

        print("2) TRANSCREVER o gerado")
        t0 = time.time()
        corpo, tipo = multpart({"idioma": "pt"}, gerado)
        r = pedir("/api/transcrever", corpo, tipo, args.limite)
        print(f"   {r.get('texto')!r} em {time.time() - t0:.1f}s")
        comparar("transcricao pt", FRASE, str(r.get("texto") or ""))
        print()

        print("3) DUBLAR pt -> en")
        t0 = time.time()
        corpo, tipo = multpart(
            {
                "destino": "en",
                "origem": "pt",
                "motor": args.motor,
                "perfil_id": args.perfil_id,
                "tradutor": "auto",
            },
            gerado,
        )
        r = pedir("/api/dublar", corpo, tipo, args.limite)
        print(f"   original:  {r.get('texto_original')!r}")
        print(f"   traduzido: {r.get('texto_traduzido')!r} em {time.time() - t0:.1f}s")
        dublado = Path(str(r.get("arquivo") or ""))
        if not dublado.is_file():
            falha(f"o dublado apontou {dublado}, que nao existe")
            return resumir()
        bom, resumo = sobra_de_sinal(dublado)
        (ok if bom else falha)(f"audio dublado: {resumo}")
        traduzido = str(r.get("texto_traduzido") or "")
        # Derivada: exige o sentido, nao a escolha de palavra do tradutor.
        conferir_conteudo("traducao en", traduzido)
        print()

        print("4) TRANSCREVER o dublado (fecha o ciclo)")
        t0 = time.time()
        corpo, tipo = multpart({"idioma": "en"}, dublado)
        r = pedir("/api/transcrever", corpo, tipo, args.limite)
        print(f"   {r.get('texto')!r} em {time.time() - t0:.1f}s")
        conferir_conteudo("transcricao en", str(r.get("texto") or ""))
        if str(r.get("idioma_detectado") or "") != "en":
            falha(f"idioma detectado no audio em ingles: {r.get('idioma_detectado')!r}")
        else:
            ok("idioma detectado: en")

    except urllib.error.HTTPError as erro:
        corpo = erro.read().decode("utf-8", "replace")[:400]
        falha(f"HTTP {erro.code}: {corpo}")
    except (urllib.error.URLError, OSError, KeyError, ValueError) as erro:
        falha(f"{type(erro).__name__}: {erro}")

    return resumir(gerado, dublado, args.guardar)


def resumir(gerado: Path | None = None, dublado: Path | None = None, guardar: bool = False) -> int:
    print()
    print("-" * 74)
    for linha in passos:
        print(linha)
    print("-" * 74)
    if falhas:
        print(f"  RESULTADO: {len(falhas)} problema(s) na cadeia")
        print("  DECISAO:   QUEBRADO")
        codigo = 1
    else:
        print("  RESULTADO: a cadeia fechou (gerar -> transcrever -> dublar -> transcrever)")
        print("  DECISAO:   OK")
        codigo = 0
    if not guardar:
        for caminho in (gerado, dublado):
            if caminho is not None and caminho.is_file() and caminho.parent.name[:4].isdigit():
                try:
                    caminho.unlink()
                except OSError:
                    pass
    elif gerado or dublado:
        print(f"  arquivos guardados em: {gerado.parent if gerado else dublado.parent}")
    print("-" * 74)
    print()
    print("  Isto mede a cadeia contra uma frase conhecida. Nao mede qualidade de voz:")
    print("  quem julga timbre e entonacao e o ouvido, nao este script.")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
