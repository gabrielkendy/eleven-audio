"""Prepara a amostra de referencia antes de enviar para o motor.

O problema que isto resolve: motores com estrategia "head" aproveitam apenas os
PRIMEIROS segundos da amostra. Se a fala boa estiver no fim do arquivo, ela e
jogada fora sem ninguem perceber. Motores com estrategia "best_window" escolhem
sozinhos, mas tambem so podem escolher do que recebem.

Entao a preparacao faz tres coisas, uma vez, na criacao do perfil:

1. acha a melhor janela continua de fala e a coloca no comeco do arquivo;
2. corta silencio sobrando nas pontas;
3. acerta o nivel, sem estourar.

Nao inventa qualidade que nao existe: se a amostra for ruim, o diagnostico em
app/referencia.py continua avisando. Aqui so se evita desperdicar o que ja veio.

Trabalha so com a biblioteca padrao e o ffmpeg, igual ao resto do projeto.
"""
from __future__ import annotations

import array
import math
import subprocess
import sys
from pathlib import Path

from app import ffmpeg

TAXA_ANALISE = 16000
QUADROS_POR_JANELA = 400          # 25 ms a 16 kHz
SALTO = 160                       # 10 ms, sobreposicao de 15 ms
PISO_ABSOLUTO = 0.004             # abaixo disto e silencio, em escala 0..1
GANHO_MAXIMO_DB = 12.0            # nunca amplifica mais que isso
ALVO_PICO_DBFS = -1.0


class ErroPreparo(Exception):
    """Falha ao ler ou cortar a referencia."""


def _decodificar(arquivo: Path, limite_s: float | None = None) -> array.array:
    """Decodifica para mono 16 kHz float32. So para analise, nao altera original."""
    comando = [ffmpeg.executavel(), "-v", "error", "-i", str(arquivo)]
    if limite_s:
        comando += ["-t", f"{limite_s:.3f}"]
    comando += ["-ac", "1", "-ar", str(TAXA_ANALISE), "-f", "f32le", "pipe:1"]
    processo = subprocess.run(comando, capture_output=True, timeout=120, check=False)
    if processo.returncode or not processo.stdout:
        raise ErroPreparo("Nao foi possivel decodificar a referencia para analise.")
    amostras = array.array("f")
    amostras.frombytes(processo.stdout)
    if sys.byteorder != "little":
        amostras.byteswap()
    if not amostras:
        raise ErroPreparo("A referencia nao tem audio utilizavel.")
    if not all(math.isfinite(x) for x in amostras):
        raise ErroPreparo("A referencia contem amostras invalidas.")
    return amostras


def _rms_por_quadro(amostras: array.array) -> list[float]:
    quadros = []
    for inicio in range(0, len(amostras) - QUADROS_POR_JANELA + 1, SALTO):
        pedaco = amostras[inicio:inicio + QUADROS_POR_JANELA]
        quadros.append(math.sqrt(sum(x * x for x in pedaco) / len(pedaco)))
    return quadros


def _piso_de_ruido(quadros: list[float]) -> float:
    if not quadros:
        return 0.0
    ordenados = sorted(quadros)
    return ordenados[max(0, int(len(ordenados) * 0.2) - 1)]


def _limites_da_fala(quadros: list[float], fala: list[bool]) -> tuple[int, int]:
    """Primeiro e ultimo quadro marcado como fala."""
    indices = [i for i, e_fala in enumerate(fala) if e_fala]
    if not indices:
        return 0, len(quadros)
    return indices[0], indices[-1] + 1


def _melhor_janela(quadros: list[float], fala: list[bool], janela: int) -> tuple[int, int]:
    """Janela continua com mais fala. Empate resolve pelo nivel medio."""
    if len(quadros) <= janela:
        return _limites_da_fala(quadros, fala)
    melhor, melhor_chave = (0, janela), (-1.0, -1.0)
    for inicio in range(len(quadros) - janela + 1):
        fim = inicio + janela
        proporcao = sum(fala[inicio:fim]) / janela
        nivel = sum(quadros[inicio:fim]) / janela
        chave = (round(proporcao, 4), nivel)
        if chave > melhor_chave:
            melhor_chave, melhor = chave, (inicio, fim)
    return melhor


def analisar(arquivo: Path, limite_s: float = 30.0) -> dict[str, object]:
    """Diz o que a preparacao faria, sem escrever nada."""
    amostras = _decodificar(arquivo)
    quadros = _rms_por_quadro(amostras)
    if not quadros:
        raise ErroPreparo("A referencia e curta demais para analisar.")
    piso = _piso_de_ruido(quadros)
    corte = max(piso * 3, PISO_ABSOLUTO)
    fala = [q >= corte for q in quadros]
    if not any(fala):
        # Sinal de nivel constante, sem silencio real (um tom, por exemplo).
        # Nao ha o que cortar, e tratar tudo como fala evita zerar a medida.
        fala = [True] * len(quadros)
    total_s = len(amostras) / TAXA_ANALISE
    janela_quadros = max(1, int(limite_s * TAXA_ANALISE / SALTO))
    inicio, fim = _melhor_janela(quadros, fala, janela_quadros)
    inicio_s = inicio * SALTO / TAXA_ANALISE
    fim_s = min(fim * SALTO / TAXA_ANALISE, total_s)
    trecho = amostras[int(inicio_s * TAXA_ANALISE):int(fim_s * TAXA_ANALISE)] or amostras
    pico = max(abs(x) for x in trecho)
    return {
        "duracao_s": round(total_s, 3),
        "piso_ruido_dbfs": round(20 * math.log10(max(piso, 1e-8)), 2),
        "pico_janela_dbfs": round(20 * math.log10(max(pico, 1e-8)), 2),
        "fala_pct": round(sum(fala) / len(fala) * 100, 1),
        "inicio_janela_s": round(inicio_s, 3),
        "fim_janela_s": round(fim_s, 3),
        "janela_s": round(fim_s - inicio_s, 3),
        "movida_para_o_comeco": inicio_s > 0.05,
    }


def preparar(
    origem: Path,
    destino: Path,
    *,
    limite_s: float = 30.0,
    normalizar: bool = True,
) -> dict[str, object]:
    """Escreve uma versao preparada da referencia e devolve o que foi feito.

    O arquivo original nunca e tocado. A analise roda a 16 kHz de proposito, e o
    corte e feito no arquivo original, preservando a taxa e a profundidade.
    """
    dados = analisar(origem, limite_s=limite_s)
    inicio = float(dados["inicio_janela_s"])
    duracao = float(dados["janela_s"])
    if duracao < 1.0:
        raise ErroPreparo("A janela de fala encontrada ficou curta demais.")

    comando = [
        ffmpeg.executavel(), "-v", "error", "-y",
        "-i", str(origem),
        "-ss", f"{inicio:.3f}",
        "-t", f"{duracao:.3f}",
        "-ac", "1",
        "-c:a", "pcm_s16le",
    ]
    if normalizar:
        pico_dbfs = float(dados["pico_janela_dbfs"])
        ganho = min(GANHO_MAXIMO_DB, max(0.0, ALVO_PICO_DBFS - pico_dbfs))
        if ganho > 0.5:
            comando += ["-af", f"volume={ganho:.2f}dB"]
            dados["ganho_aplicado_db"] = round(ganho, 2)

    destino.parent.mkdir(parents=True, exist_ok=True)
    comando.append(str(destino))
    processo = subprocess.run(comando, capture_output=True, timeout=300, check=False)
    if processo.returncode or not destino.is_file():
        detalhe = (processo.stderr or b"").decode("utf-8", "replace").strip().splitlines()
        raise ErroPreparo("Nao foi possivel preparar a referencia: " + (detalhe[-1] if detalhe else "erro do ffmpeg"))
    dados["arquivo_preparado"] = str(destino)
    dados["bytes"] = destino.stat().st_size
    return dados


