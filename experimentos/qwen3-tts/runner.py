"""Runner de clonagem de voz com Qwen3-TTS. JSON entra, WAV sai.

Mesmo contrato do runner do Chatterbox: le um pedido em JSON pelo stdin, escreve
o WAV e devolve os metadados em JSON no stdout. Assim o adaptador do estudio
trata os dois motores do mesmo jeito.

    <python-do-venv> runner.py < pedido.json
    <python-do-venv> runner.py pedido.json --validate-only
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

MODELO = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
# Revisao fixada: o mesmo peso sempre, sem surpresa de atualizacao silenciosa.
REVISAO = "fd4b254389122332181a7c3db7f27e918eec64e3"
IDIOMA = "Portuguese"


def ler_pedido(caminho: str | None) -> dict:
    bruto = Path(caminho).read_text(encoding="utf-8") if caminho else sys.stdin.read()
    try:
        valor = json.loads(bruto)
    except json.JSONDecodeError as erro:
        raise ValueError(f"JSON invalido: {erro.msg}") from erro
    if not isinstance(valor, dict):
        raise ValueError("a entrada precisa ser um objeto JSON")
    return valor


def validar(valor: dict) -> dict:
    texto = valor.get("text")
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("text precisa ser uma string nao vazia")

    referencia = Path(str(valor.get("reference_audio", ""))).resolve()
    if not referencia.is_file():
        raise ValueError(f"reference_audio nao existe: {referencia}")

    saida = Path(str(valor.get("output", ""))).resolve()
    if not saida.name or saida.suffix.lower() != ".wav":
        raise ValueError("output precisa terminar em .wav")

    dispositivo = str(valor.get("device", "auto"))
    if dispositivo not in {"auto", "cuda", "cpu"}:
        raise ValueError("device precisa ser auto, cuda ou cpu")

    texto_referencia = valor.get("reference_text")
    if texto_referencia is not None and not isinstance(texto_referencia, str):
        raise ValueError("reference_text precisa ser texto ou nulo")

    return {
        "text": texto.strip(),
        "language": str(valor.get("language", IDIOMA)),
        "reference_audio": str(referencia),
        # Sem a transcricao da referencia, cai no modo que usa so o embedding de
        # locutor. E melhor que chutar um texto que nao corresponde ao audio.
        "reference_text": (texto_referencia or "").strip(),
        "output": str(saida),
        "device": dispositivo,
        "seed": int(valor.get("seed", 2026)),
        "model_id": str(valor.get("model_id", MODELO)),
        "model_revision": str(valor.get("model_revision", REVISAO)),
    }


def escolher_dispositivo(pedido: str, torch) -> str:
    if pedido == "cpu":
        return "cpu"
    if not torch.cuda.is_available():
        if pedido == "cuda":
            raise RuntimeError("CUDA foi pedida, mas torch.cuda.is_available() e falso")
        return "cpu"
    if pedido == "cuda":
        return "cuda:0"
    return "cuda:0" if torch.cuda.is_available() else "cpu"


def gerar(config: dict) -> dict:
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    torch.manual_seed(config["seed"])
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(config["seed"])

    inicio = time.perf_counter()
    destino = escolher_dispositivo(config["device"], torch)
    # Sem flash-attn instalado o pacote usa o caminho manual do PyTorch. E honesto
    # declarar isso no metadado em vez de deixar parecer que a via rapida rodou.
    atencao = "flash_attention_2" if _tem_flash_attn() else "eager"

    modelo = Qwen3TTSModel.from_pretrained(
        config["model_id"],
        revision=config["model_revision"],
        device_map=destino,
        dtype=torch.bfloat16 if destino != "cpu" else torch.float32,
        attn_implementation=atencao,
    )
    carregado = time.perf_counter()

    usar_so_locutor = not config["reference_text"]
    ondas, taxa = modelo.generate_voice_clone(
        text=config["text"],
        language=config["language"],
        ref_audio=config["reference_audio"],
        ref_text=config["reference_text"] or None,
        x_vector_only_mode=usar_so_locutor,
    )
    gerado = time.perf_counter()

    saida = Path(config["output"])
    saida.parent.mkdir(parents=True, exist_ok=True)
    onda = ondas[0] if isinstance(ondas, list) else ondas
    sf.write(str(saida), np.asarray(onda), int(taxa), subtype="PCM_16")

    return {
        **config,
        "status": "ok",
        "device_used": destino,
        "attention": atencao,
        "clonagem_modo": "so_locutor" if usar_so_locutor else "texto_e_locutor",
        "sample_rate": int(taxa),
        "duration_seconds": float(len(onda)) / float(taxa),
        "load_seconds": round(carregado - inicio, 3),
        "generation_seconds": round(gerado - carregado, 3),
        "total_seconds": round(time.perf_counter() - inicio, 3),
    }


def _tem_flash_attn() -> bool:
    try:
        import flash_attn  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", nargs="?", help="arquivo JSON; stdin quando omitido")
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()
    try:
        config = validar(ler_pedido(args.input))
        resultado = config if args.validate_only else gerar(config)
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(resultado, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    raise SystemExit(main())
