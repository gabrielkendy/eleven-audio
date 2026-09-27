"""Marcas de expressão aceitas por cada motor.

Fonte: `docs/expressive-speech.md` da base VoiceStudio (lido em 27/09/2026).
Regra que importa: motor que não conhece a marca recebe o texto literal e **fala a marca em voz alta**.
Por isso a tela precisa avisar quando a marca não vale para o motor escolhido.
"""

from __future__ import annotations

import re
from typing import Any

PAUSAS = ("[pause]", "[pause 500ms]", "[pause 1s]")

# 13 marcas nativas do motor padrão (omnivoice/models/omnivoice.py, _NONVERBAL_PATTERN)
REACOES_PADRAO = (
    "[laughter]",
    "[sigh]",
    "[confirmation-en]",
    "[question-en]",
    "[question-ah]",
    "[question-oh]",
    "[question-ei]",
    "[question-yi]",
    "[surprise-ah]",
    "[surprise-oh]",
    "[surprise-wa]",
    "[surprise-yo]",
    "[dissatisfaction-hnn]",
)

MARCAS_POR_MOTOR: dict[str, tuple[str, ...]] = {
    "omnivoice": (*PAUSAS, *REACOES_PADRAO),
    "omnivoice-subprocess": (*PAUSAS, *REACOES_PADRAO),
    "cosyvoice": (*PAUSAS, "[breath]", "[laughter]"),
    "voxcpm2": PAUSAS,
    "mock": (),
}

AVISO_PAUSAS = "Toda pausa vira silêncio costurado de verdade, funciona em qualquer motor, até 10 s."
AVISO_DESCONHECIDA = (
    "Este motor não conhece a marca e vai falar ela em voz alta. Tire a marca ou troque de motor."
)
DICA_REFERENCIA = (
    "A direção da voz vem da gravação de referência: referência animada clona animada, "
    "referência apagada clona apagada."
)

PADRAO_MARCA = re.compile(r"\[[^\[\]]{1,40}\]")


def marcas_do_motor(motor: str | None) -> tuple[str, ...]:
    """Marcas aceitas pelo motor. Motor desconhecido recebe só pausas, que valem em todo motor."""
    if not motor:
        return PAUSAS
    return MARCAS_POR_MOTOR.get(motor.strip().lower(), PAUSAS)


def marcas_no_texto(texto: str) -> list[str]:
    """Todas as marcas que aparecem no texto, na ordem, sem repetir."""
    encontradas: list[str] = []
    for marca in PADRAO_MARCA.findall(texto or ""):
        if marca not in encontradas:
            encontradas.append(marca)
    return encontradas


def conferir(texto: str, motor: str | None) -> dict[str, Any]:
    """Relatório honesto do que vale e do que não vale para o motor escolhido."""
    aceitas = marcas_do_motor(motor)
    usadas = marcas_no_texto(texto)
    validas = [marca for marca in usadas if marca in aceitas]
    invalidas = [marca for marca in usadas if marca not in aceitas]

    if motor and motor.strip().lower() in MARCAS_POR_MOTOR:
        dica = DICA_REFERENCIA
    else:
        dica = f"Motor sem lista própria de marcas: só pausas valem. {DICA_REFERENCIA}"

    return {
        "motor": motor,
        "marcas": list(aceitas),
        "marcas_no_texto": usadas,
        "validas": validas,
        "invalidas": invalidas,
        "aviso": AVISO_DESCONHECIDA if invalidas else None,
        "pausas": list(PAUSAS),
        "nota_pausas": AVISO_PAUSAS,
        "dica": dica,
    }
