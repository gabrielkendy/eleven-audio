from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query

from app import ajustes as ajustes_de_qualidade
from app import base, clonar, cofre, marcas, saidas
from app.chatterbox_local import disponivel as chatterbox_disponivel
from app.chatterbox_local import sintetizar_chatterbox
from app.config import Configuracao
from app.motor import sintetizar
from app.rotas_clonar import LIMITE_UPLOAD_MB

MOTORES_BLOQUEADOS = {
    # A base anuncia este sidecar como disponível, mas a execução real falha
    # porque o ambiente isolado não possui o pacote omnivoice. Não alteramos a
    # base: só impedimos que o adaptador direcione o usuário a uma rota quebrada.
    "omnivoice-subprocess": "Ambiente isolado incompleto. Use OmniVoice direto até este motor ser reparado.",
}

# Como cada motor consome a amostra de referencia. A base informa o tamanho do
# pedaco que aproveita em max_ref_seconds e a forma em ref_strategy. Quando nao
# informa, dizemos que nao foi verificado, em vez de supor.
NAO_VERIFICADO = "ainda não verificado quanto ao tamanho da amostra"
NAO_CLONA = "não clona voz"

# Medido em 28/09/2026: o Chatterbox PT-BR recebeu uma amostra de 75 s e gerou
# audio normalmente, sem recusar. Nao isolamos quanto da amostra ele aproveita,
# entao a frase diz o que foi observado e nao mais do que isso.
CHATTERBOX_REFERENCIA = "aceitou amostra de 75 s no teste"


def _uso_da_referencia(estrategia: Any, limite: Any, clonagem: bool = True) -> str:
    if not clonagem:
        return NAO_CLONA
    segundos = float(limite) if isinstance(limite, (int, float)) and float(limite) > 0 else None
    if estrategia == "best_window" and segundos:
        return f"usa a melhor janela de {segundos:.0f} s da amostra"
    if estrategia == "head" and segundos:
        return f"usa os primeiros {segundos:.0f} s da amostra"
    if estrategia == "full":
        return "usa a amostra inteira"
    return NAO_VERIFICADO


def _abrir_cofre(config: Configuracao) -> cofre.Cofre:
    return cofre.abrir(config.dados / "estudio.db")


def _motores(config: Configuracao, base_no_ar: bool) -> list[dict[str, Any]]:
    motores: list[dict[str, Any]] = [
        {
            "id": "mock",
            "nome": "Mock local",
            "disponivel": True,
            "motivo": None,
            "idiomas": ["pt"],
            "clonagem": False,
            "limite_referencia_s": None,
            "uso_da_referencia": NAO_CLONA,
            "dispositivo": "cpu",
        }
    ]
    if chatterbox_disponivel():
        motores.append({"id": "chatterbox-ptbr", "nome": "Chatterbox V3 · Português do Brasil",
                        "disponivel": True, "motivo": None, "idiomas": ["pt"],
                        "clonagem": True, "limite_referencia_s": None,
                        "uso_da_referencia": CHATTERBOX_REFERENCIA,
                        "dispositivo": "auto · CUDA ou CPU"})
    if not base_no_ar:
        for identificador in ("omnivoice", "voxcpm2"):
            motores.append(
                {
                    "id": identificador,
                    "nome": identificador,
                    "disponivel": False,
                    "motivo": "base esta fora do ar",
                    "idiomas": [],
                    "clonagem": True,
                    "limite_referencia_s": None,
                    "uso_da_referencia": NAO_VERIFICADO,
                    "dispositivo": None,
                }
            )
        return motores
    try:
        catalogo = base.listar_motores(config)
    except (httpx.HTTPError, OSError, ValueError) as erro:
        motores.append(
            {
                "id": "omnivoice",
                "nome": "omnivoice",
                "disponivel": False,
                "motivo": str(erro),
                "idiomas": [],
                "clonagem": True,
                "limite_referencia_s": None,
                "uso_da_referencia": NAO_VERIFICADO,
                "dispositivo": None,
            }
        )
        return motores
    for item in catalogo.get("backends", []):
        identificador = str(item["id"])
        bloqueio = MOTORES_BLOQUEADOS.get(identificador)
        clona = bool(item.get("supports_cloning"))
        motores.append(
            {
                "id": identificador,
                "nome": item.get("display_name", identificador),
                "disponivel": bool(item.get("available")) and not bloqueio,
                "motivo": bloqueio or item.get("reason") or item.get("last_error"),
                "idiomas": item.get("supported_language_names") or [],
                "clonagem": clona,
                "limite_referencia_s": item.get("max_ref_seconds"),
                "uso_da_referencia": _uso_da_referencia(
                    item.get("ref_strategy"), item.get("max_ref_seconds"), clona
                ),
                "dispositivo": item.get("effective_device"),
            }
        )
    return motores


def criar_rotas(config: Configuracao, verificar_base: Callable[[], bool]) -> APIRouter:
    rotas = APIRouter(prefix="/api")

    @rotas.get("/motores")
    def motores() -> list[dict[str, Any]]:
        return _motores(config, verificar_base())

    @rotas.post("/motores/ativo")
    def motor_ativo(corpo: dict[str, Any]) -> dict[str, str]:
        motor = str(corpo.get("motor", ""))
        encontrado = next((item for item in motores() if item["id"] == motor), None)
        if not encontrado:
            raise HTTPException(422, "motor desconhecido")
        if not encontrado["disponivel"]:
            raise HTTPException(409, f"motor indisponivel: {encontrado['motivo']}")
        if motor not in {"mock", "chatterbox-ptbr"}:
            try:
                base.selecionar_motor(config, motor)
            except base.ErroBase as erro:
                raise HTTPException(502, f"erro da base: {erro}") from erro
        banco = _abrir_cofre(config)
        try:
            banco.gravar_config("motor_ativo", motor)
        finally:
            banco.fechar()
        return {"motor": motor}

    @rotas.post("/gerar")
    def gerar(corpo: dict[str, Any]) -> dict[str, Any]:
        texto = str(corpo.get("texto", ""))
        if not 1 <= len(texto.strip()) <= 5000:
            raise HTTPException(422, "texto deve ter entre 1 e 5000 caracteres")
        try:
            velocidade = float(corpo.get("velocidade", 1.0))
        except (TypeError, ValueError) as erro:
            raise HTTPException(422, "velocidade deve ser um numero") from erro
        if not 0.5 <= velocidade <= 2.0:
            raise HTTPException(422, "velocidade deve estar entre 0,5 e 2,0")
        try:
            ajustes_pedidos = ajustes_de_qualidade.normalizar(corpo.get("ajustes"))
        except (TypeError, ValueError) as erro:
            raise HTTPException(422, str(erro)) from erro
        banco = _abrir_cofre(config)
        try:
            motor = str(corpo.get("motor") or banco.ler_config("motor_ativo", config.motor))
            perfil_id = corpo.get("perfil_id")
            perfil_base = None
            if perfil_id:
                perfil = banco.perfil(str(perfil_id))
                if not perfil:
                    raise HTTPException(404, "perfil nao encontrado")
                if perfil["origem"] == "clonado" and not banco.tem_consentimento(str(perfil_id)):
                    raise HTTPException(409, "perfil sem consentimento registrado")
                perfil_base = perfil["id_na_base"]
        finally:
            banco.fechar()
        encontrado = next((item for item in motores() if item["id"] == motor), None)
        if not encontrado:
            raise HTTPException(422, "motor desconhecido")
        if not encontrado["disponivel"]:
            raise HTTPException(409, f"motor indisponivel: {encontrado['motivo']}")
        try:
            if motor == "chatterbox-ptbr":
                if not perfil_id:
                    raise HTTPException(422, "Selecione uma voz clonada para o Chatterbox PT-BR.")
                if velocidade != 1 or ajustes_pedidos:
                    raise HTTPException(422, "Chatterbox PT-BR usa seu preset natural e velocidade 1x.")
                if str(corpo.get("idioma", "pt")) not in {"pt", "pt-BR"}:
                    raise HTTPException(422, "Este modelo especializado aceita português do Brasil.")
                semente = corpo.get("semente", 2026)
                if type(semente) is not int or not 0 <= semente <= 2147483647:
                    raise HTTPException(422, "Semente deve ser um inteiro de 0 a 2147483647.")
                resultado = sintetizar_chatterbox(texto, config=config, perfil_id=str(perfil_id), semente=semente)
            else:
                resultado = sintetizar(
                texto,
                motor=motor,
                pasta_saida=config.saidas,
                perfil_id=perfil_base,
                config=config,
                idioma=str(corpo.get("idioma", "pt")),
                velocidade=velocidade,
                semente=corpo.get("semente"),
                ajustes=ajustes_pedidos,
            )
        except base.ErroBase as erro:
            raise HTTPException(502, f"erro da base: {erro}") from erro
        arquivo = Path(resultado["arquivo"])
        resultado.update(saidas.medir(arquivo))
        # O dispositivo real da inferencia nao volta na resposta em bytes, entao
        # "dispositivo" segue como nao_informado, sem inventar. O que da para
        # afirmar e a rota que a base declara para este motor, e isso vai num
        # campo separado, com nome que nao promete mais do que e.
        resultado["dispositivo_base"] = encontrado.get("dispositivo")
        banco = _abrir_cofre(config)
        try:
            identificador = banco.registrar_geracao(
                motor=motor,
                texto_entrada=texto,
                arquivo_saida=str(arquivo),
                duracao_audio_s=float(resultado["duracao_audio_s"]),
                duracao_geracao_s=float(resultado["duracao_geracao_s"]),
                dispositivo=str(resultado["dispositivo"]),
                tamanho_bytes=int(resultado["tamanho_bytes"]),
                perfil_id=str(perfil_id) if perfil_id else None,
            )
        finally:
            banco.fechar()
        relativo = arquivo.relative_to(config.saidas).as_posix()
        return {
            **resultado,
            "geracao_id": identificador,
            "audio_url": f"/saidas/{relativo}",
            "ajustes": ajustes_pedidos,
            "resumo_ajustes": ajustes_de_qualidade.resumo(ajustes_pedidos, velocidade),
        }

    @rotas.get("/gerar/{geracao_id}")
    def geracao(geracao_id: str) -> dict[str, Any]:
        banco = _abrir_cofre(config)
        try:
            registro = banco.geracao(geracao_id)
        finally:
            banco.fechar()
        if not registro:
            raise HTTPException(404, "geracao nao encontrada")
        return {**registro, "estado": "pronto" if registro["status"] == "ok" else "erro"}

    @rotas.get("/saidas")
    def listar_saidas(
        data: str | None = Query(None),
        motor: str | None = Query(None),
        perfil: str | None = Query(None),
    ) -> list[dict[str, Any]]:
        banco = _abrir_cofre(config)
        try:
            registros = banco.listar_geracoes(motor=motor, perfil_id=perfil)
        finally:
            banco.fechar()
        if data:
            registros = [item for item in registros if item["criado_em"].startswith(data)]
        for item in registros:
            arquivo = Path(item["arquivo_saida"])
            if arquivo.is_relative_to(config.saidas):
                item["audio_url"] = f"/saidas/{arquivo.relative_to(config.saidas).as_posix()}"
        return registros

    @rotas.get("/marcas")
    def listar_marcas(motor: str | None = Query(None), texto: str | None = Query(None)) -> dict[str, Any]:
        """Marcas de expressão que o motor aceita e o que o texto atual tem de errado."""
        banco = _abrir_cofre(config)
        try:
            escolhido = motor or banco.ler_config("motor_ativo", config.motor)
        finally:
            banco.fechar()
        return marcas.conferir(texto or "", escolhido)

    @rotas.post("/saidas/abrir")
    def abrir_saidas() -> dict[str, str]:
        """Abre a pasta de saidas no explorador do sistema, para achar o audio na hora."""
        import os
        import subprocess
        import sys

        destino = config.saidas.resolve()
        destino.mkdir(parents=True, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(destino)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(destino)], check=False)
        else:
            subprocess.run(["xdg-open", str(destino)], check=False)
        return {"aberto": str(destino)}

    @rotas.get("/estado")
    def estado() -> dict[str, Any]:
        banco = _abrir_cofre(config)
        try:
            ativo = banco.ler_config("motor_ativo", config.motor)
            ultima = banco.ultima_geracao()
        finally:
            banco.fechar()
        catalogo = motores()
        escolhido = next((item for item in catalogo if item["id"] == ativo), None)
        return {
            "versao": "0.1.0",
            "base": "ok" if verificar_base() else "erro",
            "motores": catalogo,
            "motor_ativo": ativo,
            "dispositivo": (escolhido or {}).get("dispositivo") or "cpu",
            "pasta_saidas": str(config.saidas),
            "tempo_ultima_geracao_s": ultima["duracao_geracao_s"] if ultima else None,
            "limites_clonagem": {
                "minimo_s": clonar.DURACAO_MINIMA_S,
                "maximo_s": clonar.DURACAO_MAXIMA_S,
                "upload_mb": LIMITE_UPLOAD_MB,
                "descricao": clonar.descricao_limites(),
                "uso_por_motor": {
                    item["id"]: item["uso_da_referencia"]
                    for item in catalogo
                    if item.get("clonagem") and item.get("disponivel")
                },
            },
        }

    @rotas.get("/saude")
    def saude() -> dict[str, str | float]:
        livre = shutil.disk_usage(config.dados).free / (1024**3)
        return {
            "nosso_app": "ok",
            "base": "ok" if verificar_base() else "erro",
            "disco_livre_gb": round(livre, 2),
        }

    return rotas
