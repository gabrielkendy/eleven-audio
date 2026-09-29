"""Motores que o app recusa de propósito, com o motivo medido.

Fica em módulo próprio porque duas partes precisam da mesma resposta: o catálogo de
motores (`app/rotas.py`) e o desenho de voz (`app/desenho.py`). Duplicar o texto nos
dois lugares faria as duas mensagens divergirem na primeira mudança.

A base VoiceStudio é de terceiro e não é alterada: o que fazemos é impedir que o
adaptador direcione o usuário para uma rota que quebra.
"""

from __future__ import annotations

MOTORES_BLOQUEADOS: dict[str, str] = {
    # A base anuncia este sidecar como disponível, mas a execução real falha porque o
    # ambiente isolado não possui o pacote omnivoice.
    "omnivoice-subprocess": (
        "Ambiente isolado incompleto. Use OmniVoice direto até este motor ser reparado."
    ),
    # Medido em 29/09/2026: carregar o KittenTTS DERRUBA a base inteira no Windows. O
    # log dela mostra "Error processing file ...\\espeak-ng-data\\phontab: No such file
    # or directory" — o espeak-ng que o phonemizer carrega traz o caminho de compilação
    # Linux embutido, e o phonemizer ainda copia a DLL para uma pasta temporária, longe
    # do espeak-ng-data. Não vale reparar: o modelo é de INGLÊS (language="en-us" fixo
    # no código), então não serve para português nem depois de consertado.
    "kittentts": (
        "Motor de inglês, com defeito no Windows, e derruba a base. "
        "Use OmniVoice ou Chatterbox PT-BR."
    ),
    # Medido em 29/09/2026: gerar com o VoxCPM2 derrubou a base (o app recebia
    # WinError 10054 e em seguida "base esta fora do ar"). O dono também reprovou o
    # resultado pelo ouvido: "médio pra ruim" contra o OmniVoice, que ele aprovou como
    # perfeito. Enquanto a base não tiver um caminho estável para ele, fica fora.
    "voxcpm2": (
        "Derruba a base ao gerar e foi reprovado pelo ouvido. "
        "Use OmniVoice ou Chatterbox PT-BR."
    ),
}


def motivo(motor: str) -> str | None:
    """Motivo do bloqueio, ou None quando o motor pode ser usado."""
    return MOTORES_BLOQUEADOS.get(motor)
