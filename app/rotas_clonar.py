from __future__ import annotations

from email.parser import BytesParser
from email.policy import default
from pathlib import Path
from subprocess import TimeoutExpired
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.clonar import ErroClonagem, apagar_perfil, criar_perfil, listar_perfis
from app.cofre import abrir
from app.config import carregar_config
from app.referencia import diagnosticar

router = APIRouter()


def _texto_do_campo(parte, dados: bytes) -> str:
    """Decodifica o campo sem derrubar a requisicao.

    O charset declarado vem primeiro. Depois UTF-8 e, por fim, as codificacoes
    de console do Windows: um cliente que envie acentos sem declarar charset
    nao pode virar erro 500.
    """
    tentativas = [parte.get_content_charset(), "utf-8", "cp1252", "latin-1"]
    for codificacao in tentativas:
        if not codificacao:
            continue
        try:
            return dados.decode(codificacao)
        except (UnicodeDecodeError, LookupError):
            continue
    return dados.decode("utf-8", "replace")


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
            campos[nome] = _texto_do_campo(parte, dados)
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
    return [
        {**perfil, "audio_url": f"/api/perfis/{quote(str(perfil['id']), safe='')}/audio"}
        for perfil in listar_perfis(_config(request))
    ]


def _referencia(request: Request, perfil_id: str) -> Path:
    config = _config(request)
    banco = abrir(config.dados / "estudio.db")
    try:
        perfil = banco.perfil(perfil_id)
    finally:
        banco.fechar()
    if perfil is None:
        raise HTTPException(404, "Perfil não encontrado.")
    nome = str(perfil.get("arquivo_referencia") or "").replace("\\", "/").rsplit("/", 1)[-1]
    raiz = (config.dados / "referencias").resolve()
    caminho = (raiz / nome).resolve()
    if not nome or not caminho.is_relative_to(raiz) or not caminho.is_file():
        raise HTTPException(404, "Este perfil não tem referência local disponível.")
    return caminho


@router.get("/api/perfis/{perfil_id}/audio")
def audio_referencia(perfil_id: str, request: Request) -> FileResponse:
    return FileResponse(_referencia(request, perfil_id))


@router.get("/api/perfis/{perfil_id}/qualidade")
def qualidade_referencia(perfil_id: str, request: Request) -> dict[str, object]:
    arquivo = _referencia(request, perfil_id)
    try:
        return diagnosticar(arquivo)
    except (OSError, ValueError, TimeoutExpired) as erro:
        raise HTTPException(422, str(erro)) from erro


@router.delete("/api/perfis/{perfil_id}")
def excluir(perfil_id: str, request: Request) -> dict[str, str]:
    try:
        return apagar_perfil(_config(request), perfil_id, cliente=_cliente(request))
    except ErroClonagem as erro:
        raise HTTPException(erro.status, str(erro)) from erro
    except httpx.HTTPError as erro:
        raise HTTPException(502, f"Nao foi possivel falar com a base: {erro}") from erro
