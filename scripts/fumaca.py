from __future__ import annotations

import json
import sys
import wave
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_PROJETO))

from app.config import carregar_config
from app.motor import sintetizar


def _get_json(url: str) -> dict[str, object]:
    with urlopen(url, timeout=3) as resposta:
        return json.load(resposta)


def main() -> int:
    config = carregar_config()
    falhas: list[str] = []

    try:
        saude_base = _get_json(f"{config.base_url}/health")
        print(f"base: ok {saude_base}")
    except (OSError, URLError, ValueError) as erro:
        falhas.append(f"base indisponivel: {erro}")
        print(f"base: erro {erro}")

    try:
        saude_app = _get_json(f"http://127.0.0.1:{config.porta}/api/saude")
        print(f"app: ok {saude_app}")
    except (OSError, URLError, ValueError) as erro:
        falhas.append(f"app indisponivel: {erro}")
        print(f"app: erro {erro}")

    resultado = sintetizar(
        "Teste de fumaca da fatia zero.",
        motor="mock",
        pasta_saida=config.saidas,
    )
    arquivo = Path(resultado["arquivo"])
    with wave.open(str(arquivo), "rb") as wav:
        duracao_lida = wav.getnframes() / wav.getframerate()
    print(
        "mock: ok "
        f"arquivo={arquivo} duracao_audio_s={duracao_lida:.3f} "
        f"duracao_geracao_s={resultado['duracao_geracao_s']:.6f}"
    )

    for falha in falhas:
        print(f"FALHA: {falha}", file=sys.stderr)
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
