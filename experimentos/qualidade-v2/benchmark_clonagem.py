"""Compara motores com o MESMO texto, a MESMA voz e a MESMA semente.

Diferente do benchmark anterior, aqui nada muda entre as rodadas alem do motor.
E o unico jeito de dizer qual clona melhor sem enganar a si mesmo.

    <python-do-app> experimentos/qualidade-v2/benchmark_clonagem.py PERFIL_ID "texto"
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

APP = "http://127.0.0.1:7800"
RAIZ = Path(__file__).resolve().parents[2]
MOTORES = ("omnivoice", "voxcpm2", "chatterbox-ptbr")
SEMENTE = 2026


def relativo(caminho: str) -> str:
    """Guarda caminho relativo ao projeto, para o relatorio nao vazar a maquina."""
    try:
        return Path(caminho).resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        return Path(caminho).name


def gerar(motor: str, perfil: str, texto: str) -> dict:
    corpo = {
        "texto": texto,
        "perfil_id": perfil,
        "motor": motor,
        "idioma": "pt",
        "velocidade": 1,
        "semente": SEMENTE,
    }
    pedido = urllib.request.Request(
        f"{APP}/api/gerar",
        data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(pedido, timeout=900) as resposta:
            return json.loads(resposta.read().decode("utf-8"))
    except urllib.error.HTTPError as erro:
        return {"erro": f"HTTP {erro.code}: {erro.read().decode('utf-8')[:200]}"}
    except Exception as erro:  # noqa: BLE001
        return {"erro": str(erro)[:200]}


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    perfil, texto = sys.argv[1], sys.argv[2]
    print(f"voz    : {perfil}")
    print(f"texto  : {texto}")
    print(f"semente: {SEMENTE} (igual para todos)")
    print()
    resultados = []
    for motor in MOTORES:
        print(f"--- {motor} ---", flush=True)
        r = gerar(motor, perfil, texto)
        if r.get("erro"):
            print(f"    falhou: {r['erro']}\n")
            resultados.append({"motor": motor, "erro": r["erro"]})
            continue
        print(f"    arquivo  : {Path(r['arquivo']).name}")
        print(f"    audio    : {r['duracao_audio_s']} s em {r['duracao_geracao_s']} s")
        print(f"    dispositivo: {r.get('dispositivo')}")
        if r.get("resumo_ajustes"):
            print(f"    ajustes  : {r['resumo_ajustes']}")
        print()
        resultados.append({"motor": motor, "arquivo": relativo(r["arquivo"]),
                           "duracao_audio_s": r["duracao_audio_s"],
                           "duracao_geracao_s": r["duracao_geracao_s"],
                           "dispositivo": r.get("dispositivo")})
    saida = Path("experimentos/qualidade-v2/benchmark-clonagem.json")
    saida.write_text(json.dumps({"perfil": perfil, "texto": texto, "semente": SEMENTE,
                                 "resultados": resultados}, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"gravado: {saida}")
    print()
    print("Para medir a similaridade de locutor:")
    arquivos = " ".join(f'"{r["arquivo"]}"' for r in resultados if r.get("arquivo"))
    print(f"  <python-da-base> experimentos/qualidade-v2/medir_locutor.py "
          f'"dados/referencias/<sua-referencia>.wav" {arquivos}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
