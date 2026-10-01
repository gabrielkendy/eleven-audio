"""Saidas: convencao de nome, gravacao e medicao de audio. Contrato compartilhado.

Convencao obrigatoria do PRD: AAAA-MM-DD_HHMMSS_motor_perfil.wav
Audio sempre em arquivo. Nunca no banco.
"""

from __future__ import annotations

import os
import re
import subprocess
import unicodedata
import wave
from datetime import datetime
from pathlib import Path
from typing import BinaryIO


def sanitizar(valor: str, padrao: str = "sem-perfil") -> str:
    """Deixa o trecho seguro para nome de arquivo, sem acento."""
    ascii_puro = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode("ascii")
    limpo = re.sub(r"[^a-zA-Z0-9_-]+", "-", ascii_puro).strip("-").lower()
    return limpo or padrao


def carimbo(quando: datetime | None = None) -> str:
    momento = quando or datetime.now().astimezone()
    return momento.strftime("%Y-%m-%d_%H%M%S")


def nome_arquivo(motor: str, perfil_id: str | None = None, quando: datetime | None = None) -> str:
    """AAAA-MM-DD_HHMMSS_motor_perfil.wav"""
    return f"{carimbo(quando)}_{sanitizar(motor, 'motor')}_{sanitizar(perfil_id or 'padrao')}.wav"


def pasta_do_dia(pasta_base: Path, quando: datetime | None = None) -> Path:
    momento = quando or datetime.now().astimezone()
    destino = Path(pasta_base) / momento.strftime("%Y-%m-%d")
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def medir_duracao(caminho: Path) -> float:
    """Duracao MEDIDA do arquivo. wav pelo proprio Python, o resto por ffprobe."""
    arquivo = Path(caminho)
    if not arquivo.exists():
        raise FileNotFoundError(f"arquivo de audio nao encontrado: {arquivo}")
    if arquivo.suffix.lower() == ".wav":
        with wave.open(str(arquivo), "rb") as leitor:
            return leitor.getnframes() / float(leitor.getframerate())
    saida = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(arquivo),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(saida.stdout.strip())


def tamanho_bytes(caminho: Path) -> int:
    return Path(caminho).stat().st_size


def destino_livre(destino: Path) -> Path:
    """Devolve o caminho, acrescentando -2, -3... se ja existir.

    O nome tem precisao de segundo (`carimbo`). Duas geracoes do mesmo motor
    e do mesmo perfil dentro do mesmo segundo davam o MESMO arquivo: a segunda
    apagava a primeira, calada. Como o nome e' so' AAAA-MM-DD_HHMMSS_motor_perfil,
    apertar Ctrl+Enter duas vezes rapido ja bastava para perder o primeiro audio.
    """
    destino = Path(destino)
    if not destino.exists():
        return destino
    raiz, sufixo = destino.stem, destino.suffix
    for numero in range(2, 1000):
        candidato = destino.with_name(f"{raiz}-{numero}{sufixo}")
        if not candidato.exists():
            return candidato
    raise RuntimeError(f"nao achei nome livre para {destino.name}")


def abrir_destino_exclusivo(destino: Path) -> tuple[Path, BinaryIO]:
    """Reserva e abre um nome sem corrida, inclusive entre processos."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    raiz, sufixo = destino.stem, destino.suffix
    candidatos = (destino, *(destino.with_name(f"{raiz}-{n}{sufixo}") for n in range(2, 1000)))
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    for candidato in candidatos:
        try:
            descritor = os.open(candidato, flags, 0o600)
        except FileExistsError:
            continue
        return candidato, os.fdopen(descritor, "wb")
    raise RuntimeError(f"não achei nome livre para {destino.name}")


def gravar_bytes(destino: Path, dados: bytes) -> Path:
    """Grava sem nunca apagar áudio anterior, inclusive entre threads/processos."""
    candidato, arquivo = abrir_destino_exclusivo(destino)
    try:
        with arquivo:
            arquivo.write(dados)
    except Exception:
        candidato.unlink(missing_ok=True)
        raise
    return candidato


def medir(caminho: Path) -> dict[str, float | int]:
    """Pacote de medicao pronto para gravar na tabela geracao."""
    arquivo = Path(caminho)
    return {
        "arquivo": str(arquivo),
        "duracao_audio_s": round(medir_duracao(arquivo), 3),
        "tamanho_bytes": tamanho_bytes(arquivo),
    }


def abrir_pasta(caminho: Path) -> None:
    """Abre a pasta no explorador do Windows sem depender de shell."""
    destino = Path(caminho)
    destino.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(["explorer", str(destino)])
