from __future__ import annotations

import math
import re
import struct
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unicodedata import normalize


def _sanitizar_nome(valor: str) -> str:
    ascii_puro = normalize("NFKD", valor).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", ascii_puro).strip("-") or "sem-perfil"


def sintetizar(
    texto: str,
    *,
    motor: str,
    pasta_saida: Path,
    perfil_id: str | None = None,
) -> dict[str, Any]:
    if motor != "mock":
        raise ValueError("A FATIA 0 aceita somente o motor mock")
    if not texto.strip():
        raise ValueError("O texto do teste nao pode estar vazio")

    inicio = time.perf_counter()
    pasta_saida.mkdir(parents=True, exist_ok=True)
    taxa = 24_000
    quantidade_quadros = int(taxa * max(0.6, min(30.0, len(texto) / 14.0)))
    perfil = _sanitizar_nome(perfil_id or "sem-perfil")
    carimbo = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d_%H%M%S")
    arquivo = pasta_saida / f"{carimbo}_mock_{perfil}.wav"

    with wave.open(str(arquivo), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(taxa)
        quadros = bytearray()
        for indice in range(quantidade_quadros):
            amostra = int(10_000 * math.sin(2 * math.pi * 440 * indice / taxa))
            quadros.extend(struct.pack("<h", amostra))
        wav.writeframes(quadros)

    return {
        "arquivo": str(arquivo),
        "duracao_audio_s": quantidade_quadros / taxa,
        "duracao_geracao_s": round(time.perf_counter() - inicio, 6),
        "motor": "mock",
        "dispositivo": "cpu",
        "tamanho_bytes": arquivo.stat().st_size,
    }
