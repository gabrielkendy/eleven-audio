from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any, BinaryIO

import httpx

from app.config import Configuracao
from app.traducao import para_motor

LIMITE_UPLOAD_BYTES = 150 * 1024 * 1024
TAMANHO_BLOCO = 1024 * 1024


class ErroTranscricao(Exception):
    pass


def ler_upload_limitado(
    arquivo: BinaryIO,
    limite_bytes: int = LIMITE_UPLOAD_BYTES,
) -> bytes:
    """Lê upload em blocos e interrompe antes de aceitar conteúdo sem limite."""
    arquivo.seek(0)
    partes: list[bytes] = []
    total = 0
    while bloco := arquivo.read(TAMANHO_BLOCO):
        total += len(bloco)
        if total > limite_bytes:
            raise ErroTranscricao(
                f"o arquivo passa do limite de {limite_bytes // (1024 * 1024)} MB"
            )
        partes.append(bloco)
    if not partes:
        raise ErroTranscricao("o arquivo está vazio")
    return b"".join(partes)


def guardar_arquivo(
    arquivo: BinaryIO,
    nome: str,
    pasta_dados: Path,
    limite_bytes: int = LIMITE_UPLOAD_BYTES,
) -> Path:
    nome_seguro = re.sub(r'[^\w. -]', "_", Path(nome).name, flags=re.UNICODE).strip(". ") or "arquivo"
    destino = pasta_dados / "transcricoes" / f"{uuid.uuid4().hex[:12]}_{nome_seguro}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    arquivo.seek(0)
    total = 0
    try:
        with destino.open("wb") as saida:
            while bloco := arquivo.read(TAMANHO_BLOCO):
                total += len(bloco)
                if total > limite_bytes:
                    raise ErroTranscricao(
                        f"o arquivo passa do limite de {limite_bytes // (1024 * 1024)} MB"
                    )
                saida.write(bloco)
    except (OSError, ErroTranscricao):
        destino.unlink(missing_ok=True)
        raise
    if destino.stat().st_size == 0:
        destino.unlink()
        raise ErroTranscricao("o arquivo está vazio")
    return destino


def transcrever(
    caminho: Path,
    idioma: str,
    config: Configuracao,
    transporte: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    try:
        with caminho.open("rb") as audio, httpx.Client(
            timeout=config.timeout_s, transport=transporte
        ) as cliente:
            resposta = cliente.post(
                f"{config.base_url}/transcribe",
                files={"audio": (caminho.name, audio)},
                # O transcritor da base so entende codigo valido ("pt", "en").
                # Com o codigo da tela ("pb") ele nao reconhecia o idioma.
                data={"language": para_motor(idioma)},
            )
    except httpx.HTTPError as erro:
        raise ErroTranscricao(str(erro)) from erro
    if resposta.is_error:
        try:
            detalhe = resposta.json().get("detail", resposta.text)
        except (json.JSONDecodeError, AttributeError):
            detalhe = resposta.text
        if not isinstance(detalhe, str):
            detalhe = json.dumps(detalhe, ensure_ascii=False)
        raise ErroTranscricao(detalhe or f"HTTP {resposta.status_code}")
    try:
        resultado = resposta.json()
        texto = resultado["text"]
        if not isinstance(texto, str):
            raise TypeError
    except (json.JSONDecodeError, KeyError, TypeError) as erro:
        raise ErroTranscricao("a base devolveu uma resposta inválida") from erro
    return {
        "texto": texto,
        "idioma_detectado": resultado.get("language"),
        "motor": resultado.get("engine", "desconhecido"),
    }
