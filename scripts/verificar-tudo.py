from __future__ import annotations

import json
import sys
import time
import wave
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_PROJETO))

from app.config import carregar_config
from app.motor import sintetizar


def _get_json(url: str) -> Any:
    with urlopen(url, timeout=10) as resposta:
        return json.load(resposta)


def _nomes_motores(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        for chave in ("backends", "engines", "motores", "items", "data", "tts"):
            if isinstance(payload.get(chave), list):
                payload = payload[chave]
                break
    if not isinstance(payload, list):
        return []
    nomes = []
    for item in payload:
        if isinstance(item, str):
            nomes.append(item)
        elif isinstance(item, dict):
            nome = item.get("id") or item.get("name") or item.get("nome")
            if nome:
                nomes.append(str(nome))
    return nomes


def _duracao_wav(arquivo: Path) -> float:
    with wave.open(str(arquivo), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def main() -> int:
    config = carregar_config()
    falhas: list[str] = []
    print("VERIFICACAO DO ESTUDIO DE VOZ LOCAL")

    try:
        saude_base = _get_json(f"{config.base_url}/health")
        print(f"OK base: {saude_base}")
    except (HTTPError, URLError, OSError, ValueError) as erro:
        falhas.append(f"base indisponivel: {erro}")
        print(f"ERRO base: {erro}")

    try:
        saude_app = _get_json(f"http://127.0.0.1:{config.porta}/api/saude")
        print(f"OK app: {saude_app}")
    except (HTTPError, URLError, OSError, ValueError) as erro:
        falhas.append(f"app indisponivel: {erro}")
        print(f"ERRO app: {erro}")

    try:
        nomes = _nomes_motores(_get_json(f"{config.base_url}/engines/tts"))
        if not nomes:
            raise ValueError("a base respondeu sem nomes de motores")
        print(f"OK motores: {', '.join(nomes)}")
    except (HTTPError, URLError, OSError, ValueError) as erro:
        falhas.append(f"motores indisponiveis: {erro}")
        print(f"ERRO motores: {erro}")

    try:
        inicio = time.perf_counter()
        resultado = sintetizar(
            "Verificacao local completa com o motor de teste.",
            motor="mock",
            pasta_saida=config.saidas,
        )
        tempo_parede = time.perf_counter() - inicio
        arquivo = Path(resultado["arquivo"])
        duracao = _duracao_wav(arquivo)
        print(
            f"OK wav: {arquivo} | audio {duracao:.3f} s | "
            f"parede {tempo_parede:.3f} s"
        )
    except (OSError, ValueError, KeyError, wave.Error) as erro:
        falhas.append(f"wav mock falhou: {erro}")
        print(f"ERRO wav: {erro}")

    if falhas:
        print(f"RESULTADO: FALHOU ({len(falhas)} item(ns))")
        return 1
    print("RESULTADO: TUDO CERTO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
