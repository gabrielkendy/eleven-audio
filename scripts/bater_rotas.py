"""Bate em TODA rota com payload de verdade e reporta o que quebrar.

Nao e' teste de unidade: e' a varredura que responde "alguma coisa aqui devolve 500
ou falha calada?". Roda contra o app no ar (127.0.0.1:7800).

Uso:
    env -u PYTHONPATH .venv/Scripts/python.exe scripts/bater_rotas.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:7800"

# (metodo, caminho, corpo)  -- corpo None = sem corpo
ROTAS: list[tuple[str, str, dict | None]] = [
    ("GET", "/", None),
    ("GET", "/api/saude", None),
    ("GET", "/api/versao", None),
    ("GET", "/api/config", None),
    ("GET", "/api/estado", None),
    ("GET", "/api/motores", None),
    ("GET", "/api/configuracoes", None),
    ("GET", "/api/saidas", None),
    ("GET", "/api/historico", None),
    ("GET", "/api/perfis", None),
    ("GET", "/api/desenhos", None),
    ("GET", "/api/marcas", None),
    ("GET", "/api/transcricoes", None),
    ("GET", "/api/agente/status", None),
    ("GET", "/api/traduzir/idiomas", None),
    ("GET", "/api/traduzir/pacotes", None),
]


def chamar(metodo: str, caminho: str, corpo: dict | None) -> tuple[int, str, float]:
    import time

    dados = None if corpo is None else json.dumps(corpo).encode("utf-8")
    pedido = urllib.request.Request(BASE + caminho, data=dados, method=metodo)
    pedido.add_header("Accept", "application/json")
    if dados is not None:
        pedido.add_header("Content-Type", "application/json")
    inicio = time.perf_counter()
    try:
        with urllib.request.urlopen(pedido, timeout=120) as resposta:
            return resposta.status, resposta.read(400_000).decode("utf-8", "replace"), (
                time.perf_counter() - inicio
            )
    except urllib.error.HTTPError as erro:
        return erro.code, erro.read(400_000).decode("utf-8", "replace"), (
            time.perf_counter() - inicio
        )
    except Exception as erro:  # noqa: BLE001
        return 0, f"EXCECAO: {erro!r}", time.perf_counter() - inicio


def main() -> int:
    quebras: list[str] = []
    print(f"{'METODO':7} {'ROTA':34} {'HTTP':>5} {'s':>7}  OBS")
    for metodo, caminho, corpo in ROTAS:
        codigo, texto, segundos = chamar(metodo, caminho, corpo)
        obs = ""
        if codigo == 0:
            obs = "NAO RESPONDEU"
            quebras.append(f"{metodo} {caminho}: nao respondeu ({texto[:120]})")
        elif codigo >= 500:
            obs = "500!"
            quebras.append(f"{metodo} {caminho}: HTTP {codigo} -> {texto[:160]}")
        elif codigo == 404:
            obs = "404"
            quebras.append(f"{metodo} {caminho}: 404")
        elif texto.lstrip().startswith("<"):
            obs = "DEVOLVEU HTML"
            quebras.append(f"{metodo} {caminho}: devolveu HTML em vez de JSON")
        elif codigo >= 400:
            obs = "4xx (talvez ok)"
        print(f"{metodo:7} {caminho:34} {codigo:5} {segundos:7.2f}  {obs}")

    print()
    if quebras:
        print(f"{len(quebras)} QUEBRA(S):")
        for item in quebras:
            print("  -", item)
        return 1
    print("nenhuma quebra: todas as rotas GET respondem JSON, sem 5xx, sem 404.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
