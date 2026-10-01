from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.config import Configuracao, carregar_config
from app.desenho import ErroDesenho, criar_voz, listar_vozes


class PedidoDesenho(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    descricao: str = Field(min_length=1, max_length=2000)
    texto_previa: str = Field(min_length=1, max_length=5000)
    motor: str = Field(min_length=1)


def criar_router(config: Configuracao) -> APIRouter:
    rotas = APIRouter()

    @rotas.post("/api/desenhar")
    def desenhar(pedido: PedidoDesenho):
        try:
            return criar_voz(config, **pedido.model_dump())
        except ErroDesenho as erro:
            raise HTTPException(status_code=erro.status, detail=erro.mensagem) from erro

    @rotas.get("/api/desenhos")
    def desenhos():
        return listar_vozes(config)

    return rotas


router = criar_router(carregar_config())
