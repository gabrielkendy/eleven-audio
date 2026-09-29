from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, BinaryIO

import httpx

from app.config import Configuracao


class ErroTranscricao(Exception):
    pass


def guardar_arquivo(arquivo: BinaryIO, nome: str, pasta_dados: Path) -> Path:
    nome_seguro = re.sub(r'[^\w. -]', "_", Path(nome).name, flags=re.UNICODE).strip(". ") or "arquivo"
    destino = pasta_dados / "transcricoes" / f"{uuid.uuid4().hex[:12]}_{nome_seguro}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    arquivo.seek(0)
    with destino.open("wb") as saida:
        shutil.copyfileobj(arquivo, saida)
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
                data={"language": idioma},
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
