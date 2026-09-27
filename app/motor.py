from __future__ import annotations

import math
import struct
import time
import wave
from pathlib import Path
from typing import Any

from app import base, saidas
from app.config import Configuracao


def sintetizar(
    texto: str,
    *,
    motor: str,
    pasta_saida: Path,
    perfil_id: str | None = None,
    config: Configuracao | None = None,
    idioma: str = "pt",
    velocidade: float = 1.0,
    semente: int | None = None,
) -> dict[str, Any]:
    if not texto.strip():
        raise ValueError("O texto do teste nao pode estar vazio")

    inicio = time.perf_counter()
    arquivo = saidas.pasta_do_dia(pasta_saida) / saidas.nome_arquivo(
        motor, perfil_id
    )

    if motor != "mock":
        if config is None:
            raise ValueError("configuracao obrigatoria para motor real")
        saidas.gravar_bytes(
            arquivo,
            base.gerar_audio(
                config,
                texto=texto,
                motor=motor,
                perfil_id=perfil_id,
                idioma=idioma,
                velocidade=velocidade,
                semente=semente,
            ),
        )
        medicao = saidas.medir(arquivo)
        return {
            "arquivo": str(arquivo),
            "duracao_audio_s": medicao["duracao_audio_s"],
            "duracao_geracao_s": round(time.perf_counter() - inicio, 6),
            "motor": motor,
            "dispositivo": "cuda",
            "tamanho_bytes": medicao["tamanho_bytes"],
        }

    taxa = 24_000
    quantidade_quadros = int(taxa * max(0.6, min(30.0, len(texto) / 14.0)))

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
