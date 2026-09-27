from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Configuracao:
    porta: int
    motor: str
    dados: Path
    saidas: Path
    base_url: str
    timeout_s: float


def _caminho(valor: str, raiz: Path) -> Path:
    caminho = Path(valor).expanduser()
    if not caminho.is_absolute():
        caminho = raiz / caminho
    return caminho.resolve()


def carregar_config(
    ambiente: Mapping[str, str] | None = None,
    *,
    raiz: Path | None = None,
) -> Configuracao:
    env = os.environ if ambiente is None else ambiente
    raiz_projeto = (raiz or Path(__file__).resolve().parents[1]).resolve()
    porta = int(env.get("ESTUDIO_PORT", "7800"))
    timeout_s = float(env.get("ESTUDIO_TIMEOUT_S", "1800"))
    if not 1 <= porta <= 65_535:
        raise ValueError("ESTUDIO_PORT deve estar entre 1 e 65535")
    if timeout_s <= 0:
        raise ValueError("ESTUDIO_TIMEOUT_S deve ser positivo")

    return Configuracao(
        porta=porta,
        motor=env.get("ESTUDIO_MOTOR", "omnivoice"),
        dados=_caminho(env.get("ESTUDIO_DADOS", "dados"), raiz_projeto),
        saidas=_caminho(env.get("ESTUDIO_SAIDAS", "saidas/audio"), raiz_projeto),
        base_url=env.get("ESTUDIO_BASE_URL", "http://127.0.0.1:3900").rstrip("/"),
        timeout_s=timeout_s,
    )
