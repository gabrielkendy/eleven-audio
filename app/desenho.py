from __future__ import annotations

import json
import time
import unicodedata
from typing import Any

import httpx

from app.cofre import abrir
from app.config import Configuracao
from app.saidas import gravar_bytes, medir, nome_arquivo, pasta_do_dia


class ErroDesenho(Exception):
    def __init__(self, mensagem: str, status: int = 502) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


_TERMOS_PT = (
    (("mulher", "feminina", "narradora"), "female"),
    (("homem", "masculina", "locutor", "senhor"), "male"),
    (("idosa", "idoso", "senhora", "senhor"), "elderly"),
    (("jovem",), "young adult"),
    (("crianca", "infantil"), "child"),
    (("muito grave",), "very low pitch"),
    (("grave",), "low pitch"),
    (("aguda", "agudo"), "high pitch"),
    (("sussurro", "sussurrada"), "whisper"),
    (("britanico", "britanica"), "british accent"),
    (("americano", "americana"), "american accent"),
)


def _descricao_para_base(descricao: str) -> str:
    simples = unicodedata.normalize("NFKD", descricao).encode("ascii", "ignore").decode().lower()
    atributos = [atributo for termos, atributo in _TERMOS_PT if any(termo in simples for termo in termos)]
    return f"{descricao}. {', '.join(dict.fromkeys(atributos))}" if atributos else descricao


def _motivo(resposta: httpx.Response) -> str:
    try:
        detalhe = resposta.json().get("detail")
        if isinstance(detalhe, dict):
            return str(detalhe.get("message") or detalhe.get("error") or detalhe)
        if detalhe:
            return str(detalhe)
    except (ValueError, AttributeError):
        pass
    return resposta.text.strip() or f"A base respondeu HTTP {resposta.status_code}."


def _exigir_sucesso(resposta: httpx.Response) -> httpx.Response:
    if resposta.is_success:
        return resposta
    raise ErroDesenho(_motivo(resposta), resposta.status_code if resposta.status_code < 500 else 502)


def criar_voz(config: Configuracao, *, descricao: str, texto_previa: str, motor: str) -> dict[str, Any]:
    if motor != "voxcpm2":
        raise ErroDesenho("O desenho de voz depende do motor VoxCPM2.", 409)

    try:
        with httpx.Client(base_url=config.base_url, timeout=config.timeout_s) as cliente:
            motores = _exigir_sucesso(cliente.get("/engines/tts")).json().get("backends", [])
            info = next((item for item in motores if item.get("id") == motor), None)
            if not info:
                raise ErroDesenho("O motor VoxCPM2 nao existe nesta instalacao da base.", 409)
            if not info.get("available"):
                raise ErroDesenho(info.get("reason") or "Motor VoxCPM2 indisponivel.", 409)

            descrito = _exigir_sucesso(
                cliente.post("/design/describe", json={"description": _descricao_para_base(descricao)})
            ).json()
            perfil_base = _exigir_sucesso(
                cliente.post(
                    "/profiles",
                    files={
                        "name": (None, descricao[:80]),
                        "kind": (None, "design"),
                        "language": (None, "Auto"),
                        "seed": (None, "42"),
                        "instruct": (None, descrito.get("instruct", "")),
                        "vd_states": (None, json.dumps(descrito["attrs"])),
                    },
                )
            ).json()
            id_na_base = perfil_base["id"]
            inicio = time.perf_counter()
            audio = _exigir_sucesso(
                cliente.post(
                    "/generate",
                    files={
                        "text": (None, texto_previa),
                        "profile_id": (None, id_na_base),
                        "engine": (None, motor),
                    },
                )
            )
            duracao_geracao = round(time.perf_counter() - inicio, 3)
    except ErroDesenho:
        raise
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as erro:
        raise ErroDesenho(f"Falha ao conversar com a base: {erro}") from erro

    destino = pasta_do_dia(config.saidas) / nome_arquivo(motor, id_na_base)
    gravar_bytes(destino, audio.content)
    medidas = medir(destino)
    raiz = config.dados.parent.resolve()
    try:
        arquivo = destino.resolve().relative_to(raiz).as_posix()
    except ValueError:
        arquivo = destino.name

    cofre = abrir(config.dados / "estudio.db")
    try:
        perfil_id = cofre.salvar_perfil(
            nome=descricao[:80],
            origem="desenhado",
            descricao_desenho=descricao,
            id_na_base=id_na_base,
        )
        cofre.registrar_geracao(
            perfil_id=perfil_id,
            motor=motor,
            texto_entrada=texto_previa,
            arquivo_saida=arquivo,
            duracao_audio_s=medidas["duracao_audio_s"],
            duracao_geracao_s=duracao_geracao,
            dispositivo=info.get("effective_device") or "desconhecido",
            tamanho_bytes=medidas["tamanho_bytes"],
        )
    finally:
        cofre.fechar()

    return {
        "perfil_id": perfil_id,
        "id_na_base": id_na_base,
        "arquivo": arquivo,
        "duracao_audio_s": medidas["duracao_audio_s"],
        "duracao_geracao_s": duracao_geracao,
    }


def listar_vozes(config: Configuracao) -> list[dict[str, Any]]:
    cofre = abrir(config.dados / "estudio.db")
    try:
        return [perfil for perfil in cofre.listar_perfis() if perfil["origem"] == "desenhado"]
    finally:
        cofre.fechar()
