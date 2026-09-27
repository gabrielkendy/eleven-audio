from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.cofre import abrir
from app.config import Configuracao, carregar_config
from app.transcricao import ErroTranscricao, guardar_arquivo, transcrever


def criar_router(config: Configuracao) -> APIRouter:
    rotas = APIRouter()

    @rotas.post("/api/transcrever")
    def postar_transcricao(
        arquivo: Annotated[UploadFile, File()],
        idioma: Annotated[str, Form()] = "pt",
    ) -> dict[str, str | None]:
        if not arquivo.filename:
            raise HTTPException(status_code=400, detail="Selecione um arquivo de áudio ou vídeo.")
        try:
            caminho = guardar_arquivo(arquivo.file, arquivo.filename, config.dados)
            resultado = transcrever(caminho, idioma, config)
        except ErroTranscricao as erro:
            raise HTTPException(status_code=422, detail=f"Erro ao transcrever: {erro}") from erro

        cofre = abrir(config.dados / "estudio.db")
        try:
            transcricao_id = cofre.registrar_transcricao(
                arquivo_entrada=str(caminho),
                motor=resultado["motor"],
                texto_saida=resultado["texto"],
                idioma_detectado=resultado["idioma_detectado"],
            )
        finally:
            cofre.fechar()
        return {
            "transcricao_id": transcricao_id,
            "texto": resultado["texto"],
            "idioma_detectado": resultado["idioma_detectado"],
        }

    @rotas.get("/api/transcricoes")
    def listar_transcricoes() -> list[dict[str, object]]:
        cofre = abrir(config.dados / "estudio.db")
        try:
            return cofre.listar_transcricoes()
        finally:
            cofre.fechar()

    return rotas


router = criar_router(carregar_config())
