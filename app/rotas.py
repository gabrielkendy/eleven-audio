from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query

from app import ajustes as ajustes_de_qualidade
from app import base, clonar, cofre, ffmpeg, licencas, marcas, quando, saidas
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


# Modos de qualidade que a tela oferece. O nome viaja no historico para que a
# restauracao devolva a mesma escolha, em vez de adivinhar. Os valores sao os
# mesmos do seletor "Acabamento" da tela: natural, detalhado, broadcast.
MODOS_DE_QUALIDADE = {"natural", "detalhado", "broadcast"}


def _modo_do_pedido(modo: Any, ajustes_efetivos: dict[str, str], motor: str) -> str | None:
    """Rotulo do modo usado na geracao.

    A tela informa o modo escolhido; quando a chamada vem direto pela API, o
    modo e deduzido do que foi realmente enviado a base. Sem ajuste nenhum,
    devolve None e a tela diz "padrao do motor" em vez de supor.
    """
    if isinstance(modo, str) and modo.strip().lower() in MODOS_DE_QUALIDADE:
        return modo.strip().lower()
    if not ajustes_efetivos:
        return None
    if ajustes_efetivos.get("effect_preset") == "broadcast":
        return "broadcast"
    if motor.startswith("omnivoice") and ajustes_efetivos.get("num_step") == "64":
        return "detalhado"
    return "natural"


def _item_historico(
    config: Configuracao,
    registro: dict[str, Any],
    perfis: dict[str, str],
) -> dict[str, Any]:
    """Um item do historico no formato que a tela mostra (lista e detalhe)."""
    configuracao: dict[str, Any] | None = None
    bruto = registro.get("config_json")
    if bruto:
        try:
            dado = json.loads(bruto)
            configuracao = dado if isinstance(dado, dict) else None
        except (TypeError, json.JSONDecodeError):
            configuracao = None

    audio_url: str | None = None
    caminho = Path(str(registro.get("arquivo_saida") or ""))
    if caminho.is_file():
        try:
            audio_url = f"/saidas/{caminho.relative_to(config.saidas).as_posix()}"
        except ValueError:
            audio_url = None

    voz = (configuracao or {}).get("voz") or perfis.get(str(registro.get("perfil_id"))) or "voz do motor"
    return {
        "id": registro.get("id"),
        "perfil_id": registro.get("perfil_id"),
        "voz": voz,
        "motor": registro.get("motor"),
        "motor_nome": (configuracao or {}).get("motor_nome") or registro.get("motor"),
        "texto_entrada": registro.get("texto_entrada"),
        "duracao_audio_s": registro.get("duracao_audio_s"),
        "duracao_geracao_s": registro.get("duracao_geracao_s"),
        "tamanho_bytes": registro.get("tamanho_bytes"),
        "dispositivo": registro.get("dispositivo"),
        "status": registro.get("status"),
        "erro": registro.get("erro"),
        "criado_em": registro.get("criado_em"),
        "quando": quando.relativo(registro.get("criado_em")),
        "arquivo_saida": registro.get("arquivo_saida"),
        "audio_url": audio_url,
        "configuracao": configuracao,
    }


def _com_licenca(motor: dict[str, Any]) -> dict[str, Any]:
    """Acrescenta a licença confirmada e o aviso comercial a um motor.

    Os motores são montados em vários caminhos: mock, chatterbox local, base
    fora do ar, falha ao listar, e o catálogo da base. Centralizar aqui evita o
    defeito que apareceu em 28/09/2026, quando só o caminho do catálogo recebeu
    a licença e mock e chatterbox-ptbr ficaram sem aviso nenhum.
    """
    motor["licenca"] = licencas.da_licenca(str(motor["id"]))
    motor["aviso_licenca"] = licencas.aviso_comercial(str(motor["id"]))
    return motor


def _motores(config: Configuracao, base_no_ar: bool) -> list[dict[str, Any]]:
    motores: list[dict[str, Any]] = [
        _com_licenca(
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
        )
    ]
    if chatterbox_disponivel():
        motores.append(_com_licenca({
            "id": "chatterbox-ptbr", "nome": "Chatterbox V3 · Português do Brasil",
            "disponivel": True, "motivo": None, "idiomas": ["pt"],
            "clonagem": True, "limite_referencia_s": None,
            "uso_da_referencia": CHATTERBOX_REFERENCIA,
            "dispositivo": "auto · CUDA ou CPU",
        }))
    if not base_no_ar:
        for identificador in ("omnivoice", "voxcpm2"):
            motores.append(
                _com_licenca(
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
            )
        return motores
    try:
        catalogo = base.listar_motores(config)
    except (httpx.HTTPError, OSError, ValueError) as erro:
        motores.append(
            _com_licenca(
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
        )
        return motores
    for item in catalogo.get("backends", []):
        identificador = str(item["id"])
        bloqueio = MOTORES_BLOQUEADOS.get(identificador)
        clona = bool(item.get("supports_cloning"))
        motores.append(
            _com_licenca(
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
            perfil_nome = None
            if perfil_id:
                perfil = banco.perfil(str(perfil_id))
                if not perfil:
                    raise HTTPException(404, "perfil nao encontrado")
                if perfil["origem"] == "clonado" and not banco.tem_consentimento(str(perfil_id)):
                    raise HTTPException(409, "perfil sem consentimento registrado")
                perfil_base = perfil["id_na_base"]
                perfil_nome = perfil["nome"]
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
        # O resumo tem que descrever o que a base REALMENTE recebeu, nao so o que
        # veio da tela. Como montar_corpo sempre injeta os padroes fieis, resumir
        # apenas os ajustes pedidos dira "padrao do motor" enquanto a saida vai
        # crua, e a tela passa a mentir sobre o proprio audio.
        ajustes_efetivos = {} if motor == "chatterbox-ptbr" else {**base.PADROES_FIEIS, **ajustes_pedidos}
        # Guardar a configuracao junto da geracao e o que permite o historico
        # mostrar o que foi usado e restaurar depois, como o ElevenLabs faz.
        configuracao_da_geracao = {
            "motor": motor,
            "motor_nome": str(encontrado.get("nome") or motor),
            "voz": perfil_nome or "voz do motor",
            "perfil_id": str(perfil_id) if perfil_id else None,
            "velocidade": velocidade,
            "idioma": str(corpo.get("idioma", "pt")),
            "semente": corpo.get("semente"),
            "modo": _modo_do_pedido(corpo.get("modo"), ajustes_efetivos, motor),
            "preparo": bool(config.preparo),
            "ajustes": ajustes_efetivos,
            "resumo": ajustes_de_qualidade.resumo(ajustes_efetivos, velocidade),
        }
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
                configuracao=configuracao_da_geracao,
            )
        finally:
            banco.fechar()
        relativo = arquivo.relative_to(config.saidas).as_posix()
        return {
            **resultado,
            "geracao_id": identificador,
            "audio_url": f"/saidas/{relativo}",
            "ajustes": ajustes_efetivos,
            "resumo_ajustes": ajustes_de_qualidade.resumo(ajustes_efetivos, velocidade),
            "configuracao": configuracao_da_geracao,
            # Sem isto, quem vende pode gerar com um motor de pesos nao comerciais
            # e so descobrir depois. O aviso viaja junto do audio.
            "aviso_licenca": licencas.aviso_comercial(motor),
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

    @rotas.get("/historico")
    def historico(
        limite: int = Query(50, ge=1, le=500),
        motor: str | None = None,
        perfil_id: str | None = None,
    ) -> dict[str, Any]:
        """Historico das geracoes, da mais nova para a mais antiga."""
        banco = _abrir_cofre(config)
        try:
            registros = banco.listar_geracoes(limite=limite, motor=motor, perfil_id=perfil_id)
            perfis = {str(item["id"]): str(item["nome"]) for item in banco.listar_perfis()}
        finally:
            banco.fechar()
        itens = [_item_historico(config, registro, perfis) for registro in registros]
        return {"itens": itens, "total": len(itens)}

    @rotas.get("/historico/{geracao_id}")
    def historico_um(geracao_id: str) -> dict[str, Any]:
        banco = _abrir_cofre(config)
        try:
            registro = banco.geracao(geracao_id)
            if not registro:
                raise HTTPException(404, "geracao nao encontrada")
            perfis = {str(item["id"]): str(item["nome"]) for item in banco.listar_perfis()}
        finally:
            banco.fechar()
        return _item_historico(config, registro, perfis)

    @rotas.get("/configuracoes")
    def ler_configuracoes() -> dict[str, Any]:
        """O que a aba Configuracoes mostra: padroes da geracao + limites reais."""
        banco = _abrir_cofre(config)
        try:
            motor_ativo = str(banco.ler_config("motor_ativo", config.motor))
            guardados = banco.ler_config("padroes_geracao", {}) or {}
        finally:
            banco.fechar()
        if not isinstance(guardados, dict):
            guardados = {}
        encontrado = next((item for item in motores() if item["id"] == motor_ativo), None)
        velocidade = float(guardados.get("velocidade", 1.0))
        ajustes_guardados: dict[str, str] = {}
        if guardados.get("ajustes"):
            try:
                ajustes_guardados = ajustes_de_qualidade.normalizar(guardados.get("ajustes"))
            except (TypeError, ValueError):
                ajustes_guardados = {}
        ajustes_efetivos = {**base.PADROES_FIEIS, **ajustes_guardados}
        return {
            "motor": motor_ativo,
            "motor_nome": str((encontrado or {}).get("nome") or motor_ativo),
            "motor_disponivel": bool((encontrado or {}).get("disponivel")),
            "velocidade": velocidade,
            "idioma": str(guardados.get("idioma", "pt")),
            "modo": guardados.get("modo"),
            "semente": guardados.get("semente"),
            "preparo": bool(config.preparo),
            "ajustes": ajustes_efetivos,
            "resumo": ajustes_de_qualidade.resumo(ajustes_efetivos, velocidade),
        }

    @rotas.post("/configuracoes")
    def salvar_configuracoes(corpo: dict[str, Any]) -> dict[str, Any]:
        """Grava os padroes de geracao. Nao troca o motor ativo (isso e /motores/ativo)."""
        guardados: dict[str, Any] = {}
        if "velocidade" in corpo and corpo["velocidade"] is not None:
            try:
                velocidade = float(corpo["velocidade"])
            except (TypeError, ValueError) as erro:
                raise HTTPException(422, "velocidade deve ser um numero") from erro
            if not 0.5 <= velocidade <= 2.0:
                raise HTTPException(422, "velocidade deve estar entre 0,5 e 2,0")
            guardados["velocidade"] = velocidade
        if "idioma" in corpo and corpo["idioma"] is not None:
            idioma = str(corpo["idioma"]).strip()
            if not idioma or len(idioma) > 10:
                raise HTTPException(422, "idioma deve ser um codigo curto, por exemplo pt")
            guardados["idioma"] = idioma
        if "modo" in corpo and corpo["modo"] is not None:
            modo = str(corpo["modo"]).strip().lower()
            if modo not in MODOS_DE_QUALIDADE:
                raise HTTPException(422, f"modo deve ser um destes: {', '.join(sorted(MODOS_DE_QUALIDADE))}")
            guardados["modo"] = modo
        if "semente" in corpo and corpo["semente"] is not None:
            semente = corpo["semente"]
            if type(semente) is not int or not 0 <= semente <= 2147483647:
                raise HTTPException(422, "semente deve ser um inteiro de 0 a 2147483647")
            guardados["semente"] = semente
        if "ajustes" in corpo and corpo["ajustes"] is not None:
            try:
                guardados["ajustes"] = ajustes_de_qualidade.normalizar(corpo["ajustes"])
            except (TypeError, ValueError) as erro:
                raise HTTPException(422, str(erro)) from erro

        if not guardados:
            raise HTTPException(422, "nada para salvar: envie velocidade, modo, semente, idioma ou ajustes")
        banco = _abrir_cofre(config)
        try:
            banco.gravar_config("padroes_geracao", guardados)
            banco.registrar_evento("configurar", f"padroes de geracao: {', '.join(sorted(guardados))}")
        finally:
            banco.fechar()
        return ler_configuracoes()

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
        # O ffmpeg entra na saúde de propósito: sem ele o preparo da amostra
        # degrada em silêncio, e o preparo é o que mais melhora a clonagem.
        # Melhor aparecer aqui do que virar um erro obscuro no meio da clonagem.
        tem_ffmpeg, detalhe = ffmpeg.disponivel()
        return {
            "nosso_app": "ok",
            "base": "ok" if verificar_base() else "erro",
            "ffmpeg": "ok" if tem_ffmpeg else "erro",
            # quando está ok, o detalhe é o caminho achado; quando falta, é o que instalar
            "ffmpeg_detalhe": detalhe,
            "disco_livre_gb": round(livre, 2),
        }

    return rotas
