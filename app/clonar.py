from __future__ import annotations

import contextlib
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from app import preparo
from app.cofre import abrir
from app.config import Configuracao
from app.saidas import medir_duracao

AVISO_CONSENTIMENTO = """Antes de clonar, confirme: esta voz e sua, ou voce tem autorizacao de quem e dono.
Clonar voz de terceiro sem autorizacao e ilegal e antiético.
O audio que voce gerar e seu, mas cada motor tem licenca propria. Leia antes de uso comercial."""

# Limites da amostra de referencia, em segundos. Fonte unica: a tela le estes
# numeros de /api/estado, entao backend e front nao podem divergir.
#
# O teto e 3 minutos de proposito. Cada motor aproveita um pedaco diferente da
# amostra (ver UsoDaReferencia em app/rotas.py), e amostra maior da mais material
# para o motor escolher. Quem corta e o motor, nao nos.
DURACAO_MINIMA_S = 5.0
DURACAO_MAXIMA_S = 180.0


def descricao_limites() -> str:
    """Texto humano dos limites, reaproveitado nas mensagens de erro."""
    return f"de {DURACAO_MINIMA_S:.0f} segundos a {DURACAO_MAXIMA_S / 60:.0f} minutos"


class ErroClonagem(Exception):
    def __init__(self, mensagem: str, status: int = 400) -> None:
        super().__init__(mensagem)
        self.status = status


def validar_duracao(duracao: float) -> None:
    """Recusa amostra fora da faixa aceita.

    Fica separado do fluxo para poder ser testado sem gerar audio de 3 minutos.
    """
    if not DURACAO_MINIMA_S <= duracao <= DURACAO_MAXIMA_S:
        raise ErroClonagem(
            f"O clipe deve ter {descricao_limites()}, com uma só voz e sem música. "
            f"Duração medida: {duracao:.2f} s.",
            400,
        )


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
) -> dict[str, Any]:
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
    # Declarados antes do try: a limpeza no except precisa deles mesmo quando a
    # validacao recusa a amostra antes de qualquer preparacao acontecer.
    audio_para_base = destino
    preparado: dict[str, object] | None = None
    try:
        try:
            duracao = medir_duracao(destino)
        except (OSError, ValueError, RuntimeError) as erro:
            raise ErroClonagem(f"Nao foi possivel medir o clipe: {erro}") from erro
        validar_duracao(duracao)

        # Prepara a amostra antes de entregar para a base: corta silencio das
        # pontas e acerta o nivel. Isso ajuda principalmente os motores que usam
        # os primeiros segundos da amostra, porque o comeco deixa de ser silencio.
        #
        # Nao reordena nada e nao corta fala, entao a transcricao continua
        # valendo para o audio que a base recebe.
        if config.preparo:
            try:
                preparado = preparo.preparar(
                    destino,
                    destino.with_name(f"{destino.stem}-preparado{destino.suffix}"),
                    limite_s=DURACAO_MAXIMA_S,
                )
                audio_para_base = Path(str(preparado["arquivo_preparado"]))
            except preparo.ErroPreparo:
                # Se a preparacao falhar, a clonagem segue com o arquivo original.
                # Preparar e uma melhoria, nao um requisito.
                preparado = None

        with _sessao(config, cliente) as base:
            if not transcricao:
                with audio_para_base.open("rb") as audio:
                    resposta = base.post(
                        "/transcribe",
                        files={"audio": (audio_para_base.name, audio, "application/octet-stream")},
                        data={"language": "pt", "mode": "reference"},
                    )
                _confirmar(resposta)
                corpo = resposta.json()
                transcricao = str(corpo.get("text") or corpo.get("refined_text") or "").strip()
                if not transcricao:
                    raise ErroClonagem("A base nao devolveu texto para a transcricao.", 502)

            with audio_para_base.open("rb") as audio:
                resposta = base.post(
                    "/profiles",
                    files={"ref_audio": (audio_para_base.name, audio, "application/octet-stream")},
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

            with audio_para_base.open("rb") as audio:
                resposta = base.post(
                    f"/profiles/{quote(perfil_base_id, safe='')}/consent",
                    files={"consent_audio": (audio_para_base.name, audio, "application/octet-stream")},
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
        if preparado and audio_para_base != destino:
            audio_para_base.unlink(missing_ok=True)
        resposta_final: dict[str, object] = {
            "perfil_id": perfil_id,
            "id_na_base": perfil_base_id,
            "aviso": AVISO_CONSENTIMENTO,
        }
        if preparado and float(preparado.get("duracao_s", 0) or 0) > 0:
            resposta_final["preparo"] = {
                "duracao_original_s": preparado["duracao_s"],
                "duracao_enviada_s": preparado["janela_s"],
                "fala_pct": preparado["fala_pct"],
                "ganho_aplicado_db": preparado.get("ganho_aplicado_db"),
                "explicacao": "Silencio das pontas cortado e nivel acertado antes de enviar para o motor.",
            }
        return resposta_final
    except Exception:
        if preparado and audio_para_base != destino:
            audio_para_base.unlink(missing_ok=True)
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
