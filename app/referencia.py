"""Diagnóstico técnico de referência. Não mede identidade nem promete fidelidade."""
from __future__ import annotations

import array
import math
import subprocess
import sys
from pathlib import Path


def diagnosticar(arquivo: Path) -> dict[str, object]:
    """Decodifica no máximo 31s sem alterar o original. Mesmas unidades para todos formatos."""
    processo = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(arquivo), "-t", "31", "-ac", "1",
         "-ar", "16000", "-f", "f32le", "pipe:1"],
        capture_output=True, timeout=30, check=False,
    )
    if processo.returncode or not processo.stdout:
        raise ValueError("Não foi possível analisar a referência de áudio.")
    amostras = array.array("f")
    amostras.frombytes(processo.stdout)
    if sys.byteorder != "little":
        amostras.byteswap()
    if not all(math.isfinite(x) for x in amostras):
        raise ValueError("A referência contém amostras não finitas.")
    pico = max(abs(x) for x in amostras)
    rms = math.sqrt(sum(x * x for x in amostras) / len(amostras))
    db = lambda x: round(20 * math.log10(max(x, 1e-8)), 2)
    clipping = sum(abs(x) >= 0.999 for x in amostras) / len(amostras) * 100
    frames = [amostras[i:i + 320] for i in range(0, len(amostras), 320)]
    baixos = sum(math.sqrt(sum(x*x for x in f)/len(f)) < 0.003162 for f in frames)
    baixo_percentual = baixos / len(frames) * 100
    avisos = []
    if pico < 0.001:
        avisos.append("A referência está praticamente silenciosa. Grave novamente.")
    elif db(rms) < -30:
        avisos.append("Volume médio baixo. Grave mais perto do microfone, sem estourar.")
    if clipping > 0.1:
        avisos.append("Possível saturação. Reduza o ganho e grave novamente.")
    if baixo_percentual > 35:
        avisos.append("Muitas janelas de volume baixo. Confira pausas longas e voz distante.")
    duration = len(amostras) / 16000
    if duration > 20:
        avisos.append("Esta amostra passa de 20 s. O motor pode usar apenas um trecho e realinhar o texto.")
    step = max(1, len(amostras) // 48)
    onda = [round(max(abs(x) for x in amostras[i:i + step]), 5)
            for i in range(0, len(amostras), step)][:48]
    return {"duracao_s": round(duration, 3), "pico_dbfs": db(pico), "rms_dbfs": db(rms),
            "amostras_no_limite_pct": round(clipping, 3),
            "janelas_abaixo_menos50dbfs_pct": round(baixo_percentual, 2),
            "onda": onda, "avisos": avisos,
            "limite": "Diagnóstico de sinal, não nota de voz. Não detecta música, reverberação nem outras pessoas."}
