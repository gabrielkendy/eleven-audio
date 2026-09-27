from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import base, cofre
from app.config import Configuracao, carregar_config
from app.rotas import criar_rotas


def criar_app(
    config: Configuracao,
    *,
    verificar_base: Callable[[], bool] | None = None,
) -> FastAPI:
    config.dados.mkdir(parents=True, exist_ok=True)
    config.saidas.mkdir(parents=True, exist_ok=True)
    banco = cofre.abrir(config.dados / "estudio.db")
    banco.fechar()
    consulta_base = verificar_base or (lambda: base.saudavel(config))
    aplicacao = FastAPI(title="Estudio de Voz Local")
    aplicacao.include_router(criar_rotas(config, consulta_base))
    aplicacao.mount("/saidas", StaticFiles(directory=config.saidas), name="saidas")
    web = Path(__file__).resolve().parents[1] / "web"
    if web.exists():
        aplicacao.mount("/web", StaticFiles(directory=web), name="web")

        @aplicacao.get("/")
        def inicio() -> FileResponse:
            return FileResponse(web / "index.html")

    return aplicacao


configuracao = carregar_config()
app = criar_app(configuracao)
