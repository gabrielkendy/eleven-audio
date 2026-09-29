"""Rotas de tradução: texto, detecção e áudio para áudio.

Separado de `rotas_transcrever.py` porque são coisas diferentes: transcrever é
ouvir e escrever; traduzir é trocar de idioma, e dublar é as duas coisas mais
falar de novo.
"""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app import dublar as dublagem
from app import traducao
from app.cofre import abrir
from app.config import Configuracao, carregar_config


class PedidoTexto(BaseModel):
    texto: str = Field(min_length=1, max_length=20000)
    origem: str = ""
    destino: str
    # quem traduz: "auto" (modelo local, com Argos de reserva), "llm" ou "argos"
    motor: str = "auto"


class PedidoDeteccao(BaseModel):
    texto: str = Field(min_length=1, max_length=20000)


class PedidoPacotes(BaseModel):
    origem: str = Field(min_length=1)
    destinos: list[str] = Field(min_length=1, max_length=50)


def criar_router(config: Configuracao) -> APIRouter:
    rotas = APIRouter()

    @rotas.get("/api/traduzir/idiomas")
    def idiomas() -> dict[str, object]:
        """Catálogo do tradutor, com os pares que já estão instalados."""
        return {
            "idiomas": traducao.catalogo(),
            "total": len(traducao.IDIOMAS),
            "pivo": traducao.PIVO,
            "nota": (
                "O tradutor é offline. Pares que não existem direto passam pelo "
                f"{traducao.nome(traducao.PIVO)}, o que pode reduzir a qualidade."
            ),
        }

    @rotas.post("/api/traduzir/texto")
    def traduzir_texto(pedido: PedidoTexto) -> dict[str, object]:
        try:
            resultado = traducao.traduzir(
                pedido.texto, pedido.origem, pedido.destino, config, motor=pedido.motor
            )
        except traducao.ErroTraducao as erro:
            raise HTTPException(status_code=422, detail=str(erro)) from erro
        resultado["destino_nome"] = traducao.nome(str(resultado["destino"]))
        resultado["origem_nome"] = traducao.nome(str(resultado["origem"]))
        return resultado

    @rotas.post("/api/traduzir/detectar")
    def detectar(pedido: PedidoDeteccao) -> dict[str, object]:
        return traducao.detectar_idioma(pedido.texto, config)

    @rotas.get("/api/traduzir/pacotes")
    def ver_pacotes(
        origem: Annotated[str, Query(min_length=1)],
        destinos: Annotated[str, Query()] = "",
    ) -> dict[str, object]:
        """Mostra quais idiomas já estão baixados saindo de uma origem."""
        lista = [item for item in destinos.split(",") if item.strip()] or None
        try:
            estado = traducao.pacotes_instalados(origem, config, destinos=lista)
        except traducao.ErroTraducao as erro:
            raise HTTPException(status_code=422, detail=str(erro)) from erro
        instalados = sorted(codigo for codigo, pronto in estado.items() if pronto)
        faltando = sorted(codigo for codigo, pronto in estado.items() if not pronto)
        return {
            "origem": traducao.normalizar(origem),
            "origem_nome": traducao.nome(origem),
            "instalados": instalados,
            "faltando": faltando,
            "instalados_nomes": {c: traducao.nome(c) for c in instalados},
            "faltando_nomes": {c: traducao.nome(c) for c in faltando},
            "total": len(estado),
        }

    @rotas.post("/api/traduzir/pacotes")
    def baixar_pacotes(pedido: PedidoPacotes) -> dict[str, object]:
        """Baixa os pacotes de idioma que faltam, sem sair da tela."""
        try:
            return traducao.instalar_pacotes(
                pedido.origem, pedido.destinos, config
            )
        except traducao.ErroTraducao as erro:
            raise HTTPException(status_code=422, detail=str(erro)) from erro

    @rotas.get("/api/audio")
    def servir_audio(caminho: Annotated[str, Query(min_length=1)]) -> FileResponse:
        """Serve um áudio já gerado, para a tela tocar e baixar.

        Só entrega arquivo que esteja **dentro da pasta de saídas**. Sem isso a
        rota viraria um leitor de qualquer arquivo da máquina, porque o caminho
        vem da tela e a tela pode ser adulterada.
        """
        alvo = Path(caminho)
        try:
            raiz = config.saidas.resolve()
            alvo = alvo.resolve() if alvo.is_absolute() else (config.dados.parent / alvo).resolve()
        except OSError as erro:
            raise HTTPException(status_code=400, detail="Caminho inválido.") from erro

        dentro = False
        for base in {raiz, config.dados.resolve(), (config.dados / "transcricoes").resolve()}:
            try:
                alvo.relative_to(base)
                dentro = True
                break
            except ValueError:
                continue
        if not dentro:
            raise HTTPException(
                status_code=403,
                detail="Só é possível abrir áudios gerados pelo próprio estúdio.",
            )
        if not alvo.is_file():
            raise HTTPException(status_code=404, detail="Áudio não encontrado.")

        tipo = "audio/wav" if alvo.suffix.lower() == ".wav" else "application/octet-stream"
        return FileResponse(alvo, media_type=tipo, filename=alvo.name)

    @rotas.post("/api/dublar")
    def dublar_audio(
        arquivo: Annotated[UploadFile, File()],
        destino: Annotated[str, Form()] = "en",
        origem: Annotated[str, Form()] = "",
        perfil_id: Annotated[str, Form()] = "",
        motor: Annotated[str, Form()] = "",
        tradutor: Annotated[str, Form()] = "auto",
        velocidade: Annotated[float, Form()] = 1.0,
        semente: Annotated[int, Form()] = 2026,
    ) -> dict[str, object]:
        """Áudio para áudio: entende o áudio, traduz e fala de novo."""
        if not arquivo.filename:
            raise HTTPException(status_code=400, detail="Selecione um áudio para dublar.")
        alvo = traducao.normalizar(destino)
        if not alvo:
            raise HTTPException(status_code=422, detail="Escolha o idioma de destino.")
        if alvo not in traducao.IDIOMAS:
            raise HTTPException(
                status_code=422,
                detail=f"Idioma de destino desconhecido: {destino}.",
            )

        banco = abrir(config.dados / "estudio.db")
        try:
            motor_escolhido = motor or str(banco.ler_config("motor_ativo", config.motor))
            perfil_base = None
            if perfil_id:
                perfil = banco.perfil(perfil_id)
                if not perfil:
                    raise HTTPException(status_code=404, detail="Perfil de voz não encontrado.")
                if perfil["origem"] == "clonado" and not banco.tem_consentimento(perfil_id):
                    raise HTTPException(
                        status_code=409,
                        detail="Este perfil não tem consentimento registrado.",
                    )
                perfil_base = perfil["id_na_base"]
        finally:
            banco.fechar()

        try:
            resultado = dublagem.dublar(
                arquivo=arquivo.file,
                nome_arquivo=arquivo.filename,
                destino_idioma=alvo,
                config=config,
                perfil_id=perfil_base,
                origem_idioma=origem,
                motor=motor_escolhido,
                tradutor=tradutor,
                velocidade=velocidade,
                semente=semente,
            )
        except dublagem.ErroDublagem as erro:
            raise HTTPException(status_code=422, detail=str(erro)) from erro

        # guarda no histórico, para a tela de transcrições mostrar o que passou
        banco = abrir(config.dados / "estudio.db")
        try:
            banco.registrar_transcricao(
                arquivo_entrada=str(resultado["arquivo"]),
                motor=f"dublagem:{motor_escolhido}",
                texto_saida=str(resultado["texto_traduzido"]),
                idioma_detectado=str(resultado["origem"]),
            )
        finally:
            banco.fechar()
        return resultado

    return rotas


router = criar_router(carregar_config())
