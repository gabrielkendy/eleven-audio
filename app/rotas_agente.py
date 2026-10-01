from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from app.agente import Agente, ErroAgente
from app.config import carregar_config


class _Ligar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cliente_id: str
    perfil_id: str


class _Desligar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cliente_id: str


def _registrar(destino: APIRouter, servico: Agente) -> None:
    @destino.get("/api/agente/status")
    def status() -> dict:
        return servico.status()

    @destino.post("/api/agente/ligar")
    def ligar(corpo: _Ligar) -> dict:
        try:
            return servico.ligar(corpo.cliente_id, corpo.perfil_id)
        except ValueError as erro:
            raise HTTPException(status_code=400, detail=str(erro)) from erro
        except ErroAgente as erro:
            raise HTTPException(status_code=502, detail=str(erro)) from erro

    @destino.post("/api/agente/desligar")
    def desligar(corpo: _Desligar) -> dict:
        try:
            return servico.desligar(corpo.cliente_id)
        except ValueError as erro:
            raise HTTPException(status_code=400, detail=str(erro)) from erro
        except ErroAgente as erro:
            raise HTTPException(status_code=502, detail=str(erro)) from erro


def criar_router(servico: Agente) -> APIRouter:
    novo = APIRouter()
    _registrar(novo, servico)
    return novo


router = APIRouter()
_registrar(router, Agente(carregar_config()))
