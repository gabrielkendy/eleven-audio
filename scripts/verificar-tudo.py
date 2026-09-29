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

    # O motor de voz valida o idioma em `_resolve_language` e, quando nao conhece o
    # valor, NAO erra: registra um WARNING no log e gera em "modo agnostico de
    # idioma". Medido em 29/09/2026: dos 51 codigos do catalogo, 46 passavam e
    # pb/ar/zt/tl eram descartados; o rotulo em portugues ("Ingles") falhava sempre.
    # Como o dub_base mandava o rotulo, TODA dublagem saia sem indicacao de idioma.
    try:
        from app import traducao

        # Codigos que o motor RECUSA. Se algum sair do app, a geracao volta a
        # rodar sem idioma, em silencio.
        recusados_pelo_motor = {"pb", "ar", "zt", "tl"}
        ruins = []
        for codigo in traducao.IDIOMAS:
            for entrada in (codigo, traducao.IDIOMAS[codigo]):
                saida = traducao.para_motor(entrada)
                if not saida or saida in recusados_pelo_motor:
                    ruins.append(f"{entrada!r} -> {saida!r}")
        if ruins:
            raise ValueError("idiomas que o motor recusaria: " + "; ".join(ruins[:5]))
        # "auto" tem significado proprio e nao pode virar vazio: campo vazio
        # corrompe o corpo multipart do /transcribe.
        if traducao.para_motor("auto") != "auto":
            raise ValueError("para_motor mexeu no 'auto'")
        print(f"OK idiomas: {len(traducao.IDIOMAS)} codigos convertidos para o motor")
    except (ImportError, ValueError, AttributeError) as erro:
        falhas.append(f"idiomas para o motor: {erro}")
        print(f"ERRO idiomas: {erro}")

    if falhas:
        print(f"RESULTADO: FALHOU ({len(falhas)} item(ns))")
        return 1
    print("RESULTADO: TUDO CERTO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
