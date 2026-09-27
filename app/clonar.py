from __future__ import annotations

import contextlib
import uuid
from pathlib import Path
from urllib.parse import quote

import httpx

from app.cofre import abrir
from app.config import Configuracao
from app.saidas import medir_duracao

AVISO_CONSENTIMENTO = """Antes de clonar, confirme: esta voz e sua, ou voce tem autorizacao de quem e dono.
Clonar voz de terceiro sem autorizacao e ilegal e antiético.
O audio que voce gerar e seu, mas cada motor tem licenca propria. Leia antes de uso comercial."""


class ErroClonagem(Exception):
    def __init__(self, mensagem: str, status: int = 400) -> None:
        super().__init__(mensagem)
        self.status = status


def _sessao(config: Configuracao, cliente: httpx.Client | None):
    if cliente is not None:
        return contextlib.nullcontext(cliente)
    return httpx.Client(base_url=config.base_url, timeout=config.timeout_s)


def _motivo(resposta: httpx.Response) -> str:
    try:
        corpo = resposta.json()
        if isinstance(corpo, dict):
            return str(corpo.get("detail") or corpo.get("error") or corpo)
        return str(corpo)
    except ValueError:
        return resposta.text or f"HTTP {resposta.status_code}"


def _confirmar(resposta: httpx.Response) -> None:
    if not resposta.is_success:
        raise ErroClonagem(f"A base recusou a operacao: {_motivo(resposta)}", 502)


def _caminho_registrado(config: Configuracao, arquivo: Path) -> str:
    return str(Path(config.dados.name) / "referencias" / arquivo.name).replace("\\", "/")


def criar_perfil(
    config: Configuracao,
    *,
    nome: str,
    nome_arquivo: str,
    conteudo: bytes,
    transcricao: str,
    origem_voz: str,
    aceite_consentimento: bool,
    cliente: httpx.Client | None = None,
) -> dict[str, str]:
    nome = nome.strip()
    transcricao = transcricao.strip()
    if not aceite_consentimento:
        raise ErroClonagem("O consentimento e obrigatorio para clonar uma voz.", 409)
    if origem_voz not in {"propria", "autorizada"}:
        raise ErroClonagem("Informe se a voz e propria ou autorizada.")
    if not 1 <= len(nome) <= 60:
        raise ErroClonagem("O nome deve ter entre 1 e 60 caracteres.")
    if not conteudo:
        raise ErroClonagem("Envie um clipe de referencia.")

    extensao = Path(nome_arquivo).suffix.lower() or ".wav"
    destino = config.dados / "referencias" / f"{uuid.uuid4().hex}{extensao}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(conteudo)
    perfil_base_id: str | None = None
    try:
        try:
            duracao = medir_duracao(destino)
        except (OSError, ValueError, RuntimeError) as erro:
            raise ErroClonagem(f"Nao foi possivel medir o clipe: {erro}") from erro
        if not 5 <= duracao <= 15:
            raise ErroClonagem(
                f"O clipe deve ter de 5 a 15 segundos. Duracao medida: {duracao:.2f} s."
            )

        with _sessao(config, cliente) as base:
            if not transcricao:
                with destino.open("rb") as audio:
                    resposta = base.post(
                        "/transcribe",
                        files={"audio": (destino.name, audio, "application/octet-stream")},
                        data={"language": "pt", "mode": "reference"},
                    )
                _confirmar(resposta)
                corpo = resposta.json()
                transcricao = str(corpo.get("text") or corpo.get("refined_text") or "").strip()
                if not transcricao:
                    raise ErroClonagem("A base nao devolveu texto para a transcricao.", 502)

            with destino.open("rb") as audio:
                resposta = base.post(
                    "/profiles",
                    files={"ref_audio": (destino.name, audio, "application/octet-stream")},
                    data={
                        "name": nome,
                        "ref_text": transcricao,
                        "kind": "clone",
                        "language": "pt",
                    },
                )
            _confirmar(resposta)
            corpo = resposta.json()
            perfil_base_id = str(corpo.get("profile_id") or corpo.get("id") or "").strip()
            if not perfil_base_id:
                raise ErroClonagem("A base criou o perfil sem devolver o identificador.", 502)

            with destino.open("rb") as audio:
                resposta = base.post(
                    f"/profiles/{quote(perfil_base_id, safe='')}/consent",
                    files={"consent_audio": (destino.name, audio, "application/octet-stream")},
                    data={"consent_text": AVISO_CONSENTIMENTO},
                )
            _confirmar(resposta)

        cofre = abrir(config.dados / "estudio.db")
        try:
            perfil_id = cofre.salvar_perfil(
                nome=nome,
                origem="clonado",
                id_na_base=perfil_base_id,
                arquivo_referencia=_caminho_registrado(config, destino),
                transcricao_referencia=transcricao,
                idioma="pt",
            )
            cofre.salvar_consentimento(
                perfil_id=perfil_id,
                texto_aceito=AVISO_CONSENTIMENTO,
                origem_voz=origem_voz,
            )
        finally:
            cofre.fechar()
        return {"perfil_id": perfil_id, "id_na_base": perfil_base_id, "aviso": AVISO_CONSENTIMENTO}
    except Exception:
        if perfil_base_id:
            try:
                with _sessao(config, cliente) as base:
                    base.delete(f"/profiles/{quote(perfil_base_id, safe='')}")
            except httpx.HTTPError:
                pass
        destino.unlink(missing_ok=True)
        raise


def listar_perfis(config: Configuracao) -> list[dict[str, object]]:
    cofre = abrir(config.dados / "estudio.db")
    try:
        return cofre.listar_perfis()
    finally:
        cofre.fechar()


def apagar_perfil(
    config: Configuracao,
    perfil_id: str,
    *,
    cliente: httpx.Client | None = None,
) -> dict[str, str]:
    cofre = abrir(config.dados / "estudio.db")
    try:
        perfil = cofre.perfil(perfil_id)
        if perfil is None:
            raise ErroClonagem("Perfil nao encontrado.", 404)
        with _sessao(config, cliente) as base:
            resposta = base.delete(f"/profiles/{quote(str(perfil['id_na_base']), safe='')}")
        _confirmar(resposta)
        cofre.apagar_perfil(perfil_id)
    finally:
        cofre.fechar()

    referencia = config.dados / "referencias" / Path(str(perfil["arquivo_referencia"])).name
    referencia.unlink(missing_ok=True)
    return {"apagado": perfil_id}
