from __future__ import annotations

import shutil
from collections.abc import Callable

from fastapi import FastAPI

from app import base
from app.config import Configuracao, carregar_config


def criar_app(
    config: Configuracao,
    *,
    verificar_base: Callable[[], bool] | None = None,
) -> FastAPI:
    config.dados.mkdir(parents=True, exist_ok=True)
    config.saidas.mkdir(parents=True, exist_ok=True)
    consulta_base = verificar_base or (lambda: base.saudavel(config))
    aplicacao = FastAPI(title="Estudio de Voz Local")

    @aplicacao.get("/api/saude")
    def saude() -> dict[str, str | float]:
        livre = shutil.disk_usage(config.dados).free / (1024**3)
        return {
            "nosso_app": "ok",
            "base": "ok" if consulta_base() else "erro",
            "disco_livre_gb": round(livre, 2),
        }

    return aplicacao


configuracao = carregar_config()
app = criar_app(configuracao)
