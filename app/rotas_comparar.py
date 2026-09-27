from __future__ import annotations

from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.comparar import ComparacaoErro, buscar, comparar
from app.config import Configuracao, carregar_config


class PedidoComparacao(BaseModel):
    texto: str = Field(min_length=1, max_length=5_000)
    perfil_id: str = Field(min_length=1)
    motores: list[str] = Field(min_length=2, max_length=2)


def criar_router(
    config: Configuracao,
    *,
    transporte: httpx.BaseTransport | None = None,
) -> APIRouter:
    rotas = APIRouter()

    @rotas.post("/api/comparar")
    def criar(pedido: PedidoComparacao):
        try:
            return comparar(
                texto=pedido.texto,
                perfil_id=pedido.perfil_id,
                motores=pedido.motores,
                config=config,
                transporte=transporte,
            )
        except ValueError as erro:
            raise HTTPException(422, str(erro)) from erro
        except ComparacaoErro as erro:
            raise HTTPException(409, str(erro)) from erro

    @rotas.get("/api/comparar/{grupo_id}")
    def ler(grupo_id: str):
        resultado = buscar(grupo_id, config)
        if not resultado:
            raise HTTPException(404, "comparacao nao encontrada")
        return resultado

    @rotas.get("/api/comparar/{grupo_id}/audio/{geracao_id}")
    def audio(grupo_id: str, geracao_id: str):
        resultado = buscar(grupo_id, config)
        item = next((registro for registro in resultado["arquivos"] if registro["id"] == geracao_id), None) if resultado else None
        if not item:
            raise HTTPException(404, "audio da comparacao nao encontrado")
        caminho = Path(item["arquivo_saida"])
        if not caminho.is_absolute():
            caminho = config.dados.parent / caminho
        if not caminho.is_file():
            raise HTTPException(404, "arquivo de audio nao encontrado")
        return FileResponse(caminho, media_type="audio/wav", filename=caminho.name)

    return rotas


router = APIRouter()
router.include_router(criar_router(carregar_config()))
