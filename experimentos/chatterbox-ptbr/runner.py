"""JSON -> WAV runner for the official Chatterbox V3 pt-BR language pack."""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
MODEL_REPO = "ResembleAI/Chatterbox-Multilingual-pt-br"
BASE_REPO = "ResembleAI/chatterbox"
BASE_REVISION = "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"
PTBR_REVISION = "b3952f18bc2eaa72b9bd7c17d2c4653bcad4770d"


def read_request(path: str | None) -> dict:
    raw = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON invalido: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError("entrada deve ser um objeto JSON")
    return value


def validate_request(value: dict) -> dict:
    text = value.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text deve ser uma string nao vazia")
    if value.get("locale", "pt-BR") != "pt-BR":
        raise ValueError("locale deve ser pt-BR")

    reference = Path(str(value.get("reference_audio", ""))).resolve()
    if not reference.is_file():
        raise ValueError(f"reference_audio nao existe: {reference}")
    output = Path(str(value.get("output", ""))).resolve()
    if not output.name or output.suffix.lower() != ".wav":
        raise ValueError("output deve terminar em .wav")

    config = {
        "text": text.strip(),
        "locale": "pt-BR",
        "language_id": "pt",
        "reference_audio": str(reference),
        "output": str(output),
        "seed": int(value.get("seed", 20260927)),
        "cfg_weight": float(value.get("cfg_weight", 0.5)),
        "exaggeration": float(value.get("exaggeration", 0.5)),
        "temperature": float(value.get("temperature", 0.8)),
        "device": str(value.get("device", "auto")),
    }
    if not 0.0 <= config["cfg_weight"] <= 1.0:
        raise ValueError("cfg_weight deve ficar entre 0 e 1")
    if not 0.25 <= config["exaggeration"] <= 2.0:
        raise ValueError("exaggeration deve ficar entre 0.25 e 2")
    if config["temperature"] <= 0:
        raise ValueError("temperature deve ser maior que 0")
    if config["device"] not in {"auto", "cuda", "cpu"}:
        raise ValueError("device deve ser auto, cuda ou cpu")
    return config


def cuda_free_mib() -> int | None:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.free",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            capture_output=True,
            check=True,
            timeout=10,
        )
        return int(result.stdout.strip().splitlines()[0])
    except (FileNotFoundError, ValueError, subprocess.SubprocessError):
        return None


def select_device(requested: str, torch) -> tuple[str, int | None]:
    free = cuda_free_mib()
    if requested == "cpu":
        return "cpu", free
    if requested == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA solicitada, mas torch.cuda.is_available() e falso")
        return "cuda", free
    # ponytail: conservative 7 GiB gate; expose explicit device=cuda after measurement.
    if torch.cuda.is_available() and free is not None and free >= 7168:
        return "cuda", free
    return "cpu", free


def load_ptbr_model(device: str):
    """Mirror the official pt-BR Space loader while keeping PerTh intact."""
    import torch
    from huggingface_hub import hf_hub_download, snapshot_download
    from safetensors.torch import load_file as load_safetensors

    from chatterbox.models.s3gen import S3Gen
    from chatterbox.models.t3 import T3
    from chatterbox.models.t3.modules.t3_config import T3Config
    from chatterbox.models.tokenizers import MTLTokenizer
    from chatterbox.models.voice_encoder import VoiceEncoder
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS, Conditionals

    cache = EXPERIMENT_DIR / "model-cache"
    common = {"cache_dir": cache, "token": os.getenv("HF_TOKEN")}
    base_dir = Path(
        snapshot_download(
            repo_id=BASE_REPO,
            revision=BASE_REVISION,
            allow_patterns=["ve.pt", "conds.pt", "grapheme_mtl_merged_expanded_v1.json"],
            **common,
        )
    )
    t3_path = Path(
        hf_hub_download(repo_id=MODEL_REPO, revision=PTBR_REVISION, filename="t3_pt_br.safetensors", **common)
    )
    s3_path = Path(
        hf_hub_download(repo_id=MODEL_REPO, revision=PTBR_REVISION, filename="s3gen_v3.pt", **common)
    )

    ve = VoiceEncoder()
    ve.load_state_dict(torch.load(base_dir / "ve.pt", map_location="cpu", weights_only=True))
    ve.to(device).eval()

    t3 = T3(T3Config.multilingual())
    t3.load_state_dict(load_safetensors(t3_path))
    t3.to(device).eval()

    s3gen = S3Gen()
    s3gen.load_state_dict(
        torch.load(s3_path, map_location="cpu", weights_only=True), strict=False
    )
    s3gen.to(device).eval()

    tokenizer = MTLTokenizer(str(base_dir / "grapheme_mtl_merged_expanded_v1.json"))
    conds_path = base_dir / "conds.pt"
    conds = Conditionals.load(conds_path, map_location="cpu").to(device)
    model = ChatterboxMultilingualTTS(t3, s3gen, ve, tokenizer, device, conds=conds)
    revisions = {
        "base": base_dir.name,
        "ptbr": t3_path.parent.name,
    }
    return model, revisions


def generate(config: dict) -> dict:
    import torch
    import torchaudio

    torch.set_num_threads(min(8, os.cpu_count() or 1))
    device, free_before = select_device(config["device"], torch)
    random.seed(config["seed"])
    torch.manual_seed(config["seed"])
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(config["seed"])

    started = time.perf_counter()
    model, revisions = load_ptbr_model(device)
    loaded = time.perf_counter()
    wav = model.generate(
        config["text"],
        language_id="pt",
        audio_prompt_path=config["reference_audio"],
        cfg_weight=config["cfg_weight"],
        exaggeration=config["exaggeration"],
        temperature=config["temperature"],
    )
    generated = time.perf_counter()
    output = Path(config["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    torchaudio.save(str(output), wav.detach().cpu(), model.sr, encoding="PCM_S", bits_per_sample=16)
    return {
        **config,
        "status": "ok",
        "device_used": device,
        "gpu_free_mib_before": free_before,
        "sample_rate": model.sr,
        "duration_seconds": wav.shape[-1] / model.sr,
        "load_seconds": loaded - started,
        "generation_seconds": generated - loaded,
        "total_seconds": time.perf_counter() - started,
        "model_revisions": revisions,
        "watermark": "PerTh official model path unchanged",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="JSON file; stdin when omitted")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        config = validate_request(read_request(args.input))
        result = config if args.validate_only else generate(config)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
