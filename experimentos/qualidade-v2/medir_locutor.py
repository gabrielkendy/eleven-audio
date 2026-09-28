"""Mede similaridade de locutor entre uma referencia e um audio gerado.

Usa o embeddings de locutor do SpeechBrain (ECAPA-TDNN), que e o mesmo tipo de
metrica que os benchmarks de clonagem usam (similaridade de cosseno entre o
embedding da referencia e o do audio sintetizado).

Roda com o interpretador do venv da BASE, porque e la que vive o speechbrain.
Nao altera nenhum arquivo da base: so importa e executa.

    <python-da-base> experimentos/qualidade-v2/medir_locutor.py REF.wav AUDIO.wav [AUDIO2.wav ...]
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")


def carregar():
    import torch
    from speechbrain.inference.speaker import EncoderClassifier

    fonte = "speechbrain/spkrec-ecapa-voxceleb"
    try:
        modelo = EncoderClassifier.from_hparams(source=fonte, savedir=None, run_opts={"device": "cpu"})
    except Exception:
        modelo = EncoderClassifier.from_hparams(source=fonte, run_opts={"device": "cpu"})
    return modelo, torch


def embedding(modelo, torch, caminho: Path):
    import torchaudio

    onda, taxa = torchaudio.load(str(caminho))
    if onda.shape[0] > 1:
        onda = onda.mean(dim=0, keepdim=True)
    if taxa != 16000:
        onda = torchaudio.functional.resample(onda, taxa, 16000)
    with torch.no_grad():
        vetor = modelo.encode_batch(onda).squeeze()
    return vetor


def cosseno(a, b) -> float:
    import torch

    return float(torch.nn.functional.cosine_similarity(a.unsqueeze(0), b.unsqueeze(0)))


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    referencia = Path(sys.argv[1])
    gerados = [Path(p) for p in sys.argv[2:]]
    for caminho in [referencia, *gerados]:
        if not caminho.is_file():
            print(f"nao existe: {caminho}", file=sys.stderr)
            return 2

    modelo, torch = carregar()
    print(f"modelo  : {modelo.hparams.__class__.__name__ if hasattr(modelo, 'hparams') else 'ecapa'}")
    emb_ref = embedding(modelo, torch, referencia)
    print(f"referencia: {referencia.name} ({referencia.stat().st_size / 1e3:.0f} kB)")
    print()
    print(f"{'audio gerado':52} {'similaridade':>12}")
    print("-" * 66)
    saida = []
    for caminho in gerados:
        valor = cosseno(emb_ref, embedding(modelo, torch, caminho))
        saida.append({"arquivo": caminho.name, "similaridade_locutor": round(valor, 4)})
        print(f"{caminho.name[:51]:52} {valor:>12.4f}")
    print()
    print("Leitura: 1,0 seria identico. Abaixo de 0,70 costuma soar como outra")
    print("pessoa. Isto mede identidade de locutor, nao naturalidade nem pronuncia.")
    print(json.dumps({"referencia": referencia.name, "resultados": saida}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
