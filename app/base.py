from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import Configuracao


def saudavel(config: Configuracao) -> bool:
    requisicao = Request(f"{config.base_url}/health", method="GET")
    try:
        with urlopen(requisicao, timeout=min(config.timeout_s, 3.0)) as resposta:
            return 200 <= resposta.status < 300
    except (HTTPError, URLError, TimeoutError, OSError):
        return False
