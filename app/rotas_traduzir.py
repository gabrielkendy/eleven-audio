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
from pydantic import BaseModel, ConfigDict, Field

from app import dub_base as base_dub
from app import dublar as dublagem
from app import traducao
from app.cofre import abrir
from app.config import Configuracao, carregar_config


class PedidoTexto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto: str = Field(min_length=1, max_length=20000)
    origem: str = ""
    destino: str
    # quem traduz: "auto" (modelo local, com Argos de reserva), "llm" ou "argos"
    motor: str = "auto"


class PedidoDeteccao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto: str = Field(min_length=1, max_length=20000)


class PedidoPacotes(BaseModel):
    model_config = ConfigDict(extra="forbid")

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

        try:
            alvo.relative_to(raiz)
        except ValueError:
            raise HTTPException(
                status_code=403,
                detail="Só é possível abrir áudios gerados pelo próprio estúdio.",
            )
        if not alvo.is_file():
            raise HTTPException(status_code=404, detail="Áudio não encontrado.")

        tipos = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".m4a": "audio/mp4",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
        }
        tipo = tipos.get(alvo.suffix.lower())
        if tipo is None:
            raise HTTPException(
                status_code=403,
                detail="O arquivo solicitado não é um áudio permitido.",
            )
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
                arquivo_entrada=Path(arquivo.filename).name,
                motor=f"dublagem:{motor_escolhido}",
                texto_saida=str(resultado["texto_traduzido"]),
                idioma_detectado=str(resultado["origem"]),
            )
        finally:
            banco.fechar()
        return resultado

    @rotas.post("/api/dublar-completo")
    def dublar_completo(
        arquivo: Annotated[UploadFile, File()],
        destino: Annotated[str, Form()] = "en",
        origem: Annotated[str, Form()] = "",
        perfil_id: Annotated[str, Form()] = "",
        tradutor: Annotated[str, Form()] = "auto",
        timing: Annotated[str, Form()] = base_dub.TEMPO_PADRAO,
    ) -> dict[str, object]:
        """Dublagem completa: separa a voz do fundo, respeita o tempo da fala.

        Diferente de `/api/dublar`, que transcreve, traduz e sintetiza de uma vez,
        esta rota usa a pipeline da base: demucs separa voz e trilha, a
        transcricao traz o tempo de cada trecho, e a geracao encaixa a fala nova
        no tempo do original. E mais lenta e entrega mais.
        """
        if not arquivo.filename:
            raise HTTPException(status_code=400, detail="Selecione um áudio para dublar.")
        alvo = traducao.normalizar(destino)
        if not alvo:
            raise HTTPException(status_code=422, detail="Escolha o idioma de destino.")
        if alvo not in traducao.IDIOMAS:
            raise HTTPException(
                status_code=422, detail=f"Idioma de destino desconhecido: {destino}."
            )

        # O perfil que a tela manda e o id LOCAL; a base conhece outro id, e so a
        # clonagem com consentimento pode ser usada. Mesma resolucao de /api/dublar.
        banco = abrir(config.dados / "estudio.db")
        try:
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

        if not perfil_base:
            raise HTTPException(
                status_code=422,
                detail="Escolha a voz. Cole um áudio de referência na aba Clonar primeiro.",
            )

        try:
            conteudo = dublagem.ler_upload_limitado(arquivo.file)
        except dublagem.ErroTranscricao as erro:
            raise HTTPException(status_code=413, detail=str(erro)) from erro
        try:
            resultado = base_dub.dublar_pela_base(
                conteudo=conteudo,
                nome_arquivo=arquivo.filename,
                destino_idioma=alvo,
                perfil_id=perfil_base,
                config=config,
                origem_idioma=origem,
                tradutor=tradutor,
                tempo=timing,
            )
        except base_dub.ErroDublagemBase as erro:
            raise HTTPException(status_code=422, detail=str(erro)) from erro

        banco = abrir(config.dados / "estudio.db")
        try:
            banco.registrar_transcricao(
                arquivo_entrada=Path(arquivo.filename).name,
                motor=f"dublagem-completa:{resultado.get('timing')}",
                texto_saida=str(resultado["texto_traduzido"]),
                idioma_detectado=str(resultado["origem"]),
            )
        finally:
            banco.fechar()
        return resultado

    return rotas


router = criar_router(carregar_config())
