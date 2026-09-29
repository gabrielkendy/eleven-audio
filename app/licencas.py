"""Licença de cada motor, verificada na fonte oficial.

Existe porque o dono vende soluções: gerar áudio com um motor cujos pesos proíbem
uso comercial é um risco jurídico silencioso, e nada na tela avisava.

Cada entrada foi lida na fonte primária em 28/09/2026, e a fonte fica registrada
para poder ser reconferida.
"""
from __future__ import annotations

from typing import Any

from app.bloqueios import motivo as motivo_bloqueio

# Só entra aqui o que foi confirmado na fonte oficial. O que não foi confirmado
# fica de fora e é tratado como desconhecido, em vez de suposto.
LICENCAS: dict[str, dict[str, Any]] = {
    "omnivoice": {
        "codigo": "Apache-2.0",
        "pesos": "CC-BY-NC",
        "comercial": False,
        "fonte": "huggingface.co/k2-fsa/OmniVoice (README, secao License)",
        "observacao": (
            "O README do proprio modelo diz: o codigo e Apache-2.0 mas os pesos "
            "sao CC-BY-NC por causa dos dados de treino. Quantizar nao limpa a "
            "licenca, entao as versoes GGUF herdam a mesma restricao."
        ),
    },
    "voxcpm2": {
        "codigo": "Apache-2.0",
        "pesos": "Apache-2.0",
        "comercial": True,
        "fonte": "huggingface.co/openbmb/VoxCPM2 (API do modelo, campo license)",
        "observacao": "Codigo e pesos liberados para uso comercial.",
    },
    "chatterbox-ptbr": {
        "codigo": "MIT",
        "pesos": "MIT",
        "comercial": True,
        "fonte": "huggingface.co/ResembleAI/chatterbox (API do modelo, campo license)",
        "observacao": "MIT nos pesos. Roda em CPU aqui, entao e o mais lento.",
    },
    "kittentts": {
        "codigo": "Apache-2.0",
        "pesos": "Apache-2.0",
        "comercial": True,
        "fonte": "huggingface.co/KittenML/kitten-tts-mini-0.1 (API do modelo)",
        "observacao": "Livre para uso comercial, mas nao clona voz.",
    },
    "mock": {
        "codigo": "proprio",
        "pesos": "proprio",
        "comercial": True,
        "fonte": "codigo deste repositorio",
        "observacao": "Motor de teste, gera tom puro. Nao usa modelo de terceiro.",
    },
}

DESCONHECIDO = "licença não verificada na fonte oficial"

# Sugestão para quando o motor escolhido não permite uso comercial. Ordem por
# qualidade medida e aprovada pelo ouvido do dono. Motor que o app bloqueia
# (`app/bloqueios.py`) NUNCA entra na sugestão: sugerir um motor que derruba a
# base manda o aluno para uma tela que só devolve erro.
ALTERNATIVAS_COMERCIAIS = ("chatterbox-ptbr",)
# `qwen3-tts` ficou de fora: não está no catálogo da base, então citá-lo era a
# mesma armadilha do VoxCPM2 — uma sugestão que não leva a lugar nenhum.


def alternativas_uteis() -> list[str]:
    """Alternativas comerciais que realmente podem ser escolhidas agora.

    Um motor bloqueado tem motivo medido; ele fica fora. Motor que a base não
    oferece também fica de fora, senão o conselho vira promessa vazia.
    """
    return [motor for motor in ALTERNATIVAS_COMERCIAIS if not motivo_bloqueio(motor)]


def da_licenca(motor: str) -> dict[str, Any]:
    """Licença de um motor. Motor fora da lista vira desconhecido, não 'liberado'."""
    if motor in LICENCAS:
        return dict(LICENCAS[motor])
    return {
        "codigo": DESCONHECIDO,
        "pesos": DESCONHECIDO,
        "comercial": None,
        "fonte": None,
        "observacao": "Não há licença confirmada para este motor aqui.",
    }


def bloqueia_comercial(motor: str) -> bool:
    """True só quando a licença foi conferida e proíbe uso comercial."""
    return LICENCAS.get(motor, {}).get("comercial") is False


def aviso_comercial(motor: str) -> str | None:
    """Aviso pronto para a tela, ou None quando não há o que avisar."""
    dados = LICENCAS.get(motor)
    if not dados or dados.get("comercial") is not False:
        return None
    uteis = alternativas_uteis()
    if not uteis:
        return (
            f"O motor {motor} tem pesos {dados['pesos']} e NÃO pode ser usado para "
            "vender. Nenhuma alternativa comercial está disponível nesta máquina agora."
        )
    alternativas = ", ".join(uteis[:3])
    return (
        f"O motor {motor} tem pesos {dados['pesos']} e NÃO pode ser usado para "
        f"vender. Para uso comercial, escolha {alternativas}."
    )
