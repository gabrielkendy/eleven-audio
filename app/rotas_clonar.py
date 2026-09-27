from __future__ import annotations

from email.parser import BytesParser
from email.policy import default

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.clonar import ErroClonagem, apagar_perfil, criar_perfil, listar_perfis
from app.config import carregar_config

router = APIRouter()


async def _multipart(request: Request) -> tuple[dict[str, str], str, bytes]:
    tipo = request.headers.get("content-type", "")
    if not tipo.startswith("multipart/form-data"):
        raise HTTPException(400, "Envie os campos como multipart/form-data.")
    if int(request.headers.get("content-length", "0") or 0) > 50 * 1024 * 1024:
        raise HTTPException(413, "O clipe excede o limite de 50 MB.")
    corpo = await request.body()
    if len(corpo) > 50 * 1024 * 1024:
        raise HTTPException(413, "O clipe excede o limite de 50 MB.")
    mensagem = BytesParser(policy=default).parsebytes(
        f"Content-Type: {tipo}\r\nMIME-Version: 1.0\r\n\r\n".encode() + corpo
    )
    campos: dict[str, str] = {}
    nome_arquivo = ""
    conteudo = b""
    for parte in mensagem.iter_parts():
        nome = parte.get_param("name", header="content-disposition")
        if not nome:
            continue
        dados = parte.get_payload(decode=True) or b""
        if nome == "arquivo_referencia":
            nome_arquivo = parte.get_filename() or "referencia.wav"
            conteudo = dados
        else:
            campos[nome] = dados.decode(parte.get_content_charset() or "utf-8")
    return campos, nome_arquivo, conteudo


def _config(request: Request):
    return getattr(request.app.state, "configuracao_clonar", None) or carregar_config()


def _cliente(request: Request) -> httpx.Client | None:
    return getattr(request.app.state, "cliente_clonar", None)


@router.post("/api/clonar")
async def clonar(request: Request) -> dict[str, str]:
    campos, nome_arquivo, conteudo = await _multipart(request)
    try:
        return criar_perfil(
            _config(request),
            nome=campos.get("nome", ""),
            nome_arquivo=nome_arquivo,
            conteudo=conteudo,
            transcricao=campos.get("transcricao", ""),
            origem_voz=campos.get("origem_voz", ""),
            aceite_consentimento=campos.get("aceite_consentimento", "").lower()
            in {"1", "true", "sim", "on"},
            cliente=_cliente(request),
        )
    except ErroClonagem as erro:
        raise HTTPException(erro.status, str(erro)) from erro
    except httpx.HTTPError as erro:
        raise HTTPException(502, f"Nao foi possivel falar com a base: {erro}") from erro


@router.get("/api/perfis")
def perfis(request: Request) -> list[dict[str, object]]:
    return listar_perfis(_config(request))


@router.delete("/api/perfis/{perfil_id}")
def excluir(perfil_id: str, request: Request) -> dict[str, str]:
    try:
        return apagar_perfil(_config(request), perfil_id, cliente=_cliente(request))
    except ErroClonagem as erro:
        raise HTTPException(erro.status, str(erro)) from erro
    except httpx.HTTPError as erro:
        raise HTTPException(502, f"Nao foi possivel falar com a base: {erro}") from erro
