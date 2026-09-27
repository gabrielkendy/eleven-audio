from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import (
    base,
    cofre,
    rotas_agente,
    rotas_clonar,
    rotas_comparar,
    rotas_desenhar,
    rotas_transcrever,
)
from app.config import Configuracao, carregar_config
from app.rotas import criar_rotas

ROTAS_DAS_FATIAS = (
    rotas_clonar,
    rotas_comparar,
    rotas_desenhar,
    rotas_transcrever,
    rotas_agente,
)


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
    for modulo in ROTAS_DAS_FATIAS:
        aplicacao.include_router(modulo.router)
    aplicacao.mount("/saidas", StaticFiles(directory=config.saidas), name="saidas")
    web = Path(__file__).resolve().parents[1] / "web"

    @aplicacao.middleware("http")
    async def sem_cache(
        requisicao: Request,
        chamar_proximo: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Estudio local: depois de editar a tela, o navegador nao pode servir a versao velha."""
        resposta = await chamar_proximo(requisicao)
        if requisicao.url.path == "/" or requisicao.url.path.startswith("/web/"):
            resposta.headers["Cache-Control"] = "no-store, must-revalidate"
        return resposta

    if web.exists():
        aplicacao.mount("/web", StaticFiles(directory=web), name="web")

        @aplicacao.get("/")
        def inicio() -> FileResponse:
            return FileResponse(web / "index.html")

    return aplicacao


configuracao = carregar_config()
app = criar_app(configuracao)
