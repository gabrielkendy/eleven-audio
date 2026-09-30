from __future__ import annotations

import io
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
    ajustes: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not texto.strip():
        raise ValueError("O texto do teste nao pode estar vazio")

    inicio = time.perf_counter()
    arquivo = saidas.pasta_do_dia(pasta_saida) / saidas.nome_arquivo(motor, perfil_id)

    if motor != "mock":
        if config is None:
            raise ValueError("configuracao obrigatoria para motor real")
        audio = base.gerar_audio(
            config,
            texto=texto,
            motor=motor,
            perfil_id=perfil_id,
            idioma=idioma,
            velocidade=velocidade,
            semente=semente,
            ajustes=ajustes,
        )
        base.validar_wav(audio)
        # Guardar o caminho que a gravacao DEVOLVEU, nao o que foi pedido: se
        # ja' existia arquivo com esse nome, gravar_bytes acrescenta sufixo e o
        # nome pedido apontaria para o audio da geracao anterior.
        arquivo = saidas.gravar_bytes(arquivo, audio)
        medicao = saidas.medir(arquivo)
        return {
            "arquivo": str(arquivo),
            "duracao_audio_s": medicao["duracao_audio_s"],
            "duracao_geracao_s": round(time.perf_counter() - inicio, 6),
            "motor": motor,
            # A resposta em bytes não comprova o dispositivo da inferência.
            "dispositivo": "nao_informado",
            "tamanho_bytes": medicao["tamanho_bytes"],
        }

    taxa = 24_000
    quantidade_quadros = int(taxa * max(0.6, min(30.0, len(texto) / 14.0)))

    # Montar o WAV em MEMORIA e gravar por saidas.gravar_bytes: escrever direto
    # com wave.open(str(arquivo), "wb") sobrescrevia a geracao anterior quando as
    # duas caiam no mesmo segundo (o mock e' o motor do modo de teste, e gerar
    # tres vezes seguidas e' o uso normal).
    memoria = io.BytesIO()
    with wave.open(memoria, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(taxa)
        quadros = bytearray()
        for indice in range(quantidade_quadros):
            amostra = int(10_000 * math.sin(2 * math.pi * 440 * indice / taxa))
            quadros.extend(struct.pack("<h", amostra))
        wav.writeframes(quadros)

    arquivo = saidas.gravar_bytes(arquivo, memoria.getvalue())

    return {
        "arquivo": str(arquivo),
        "duracao_audio_s": quantidade_quadros / taxa,
        "duracao_geracao_s": round(time.perf_counter() - inicio, 6),
        "motor": "mock",
        "dispositivo": "cpu",
        "tamanho_bytes": arquivo.stat().st_size,
    }
