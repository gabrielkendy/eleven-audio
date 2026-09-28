#!/usr/bin/env bash
# Monta o ambiente isolado do Qwen3-TTS. Nao toca na base nem no venv do app.
set -u

RAIZ="C:/Users/Gabriel/Documents/eleven-audio"
DESTINO="$RAIZ/experimentos/qwen3-tts"
cd "$DESTINO" || exit 1

echo "=== pasta: $(pwd) ==="

UV="C:/Users/Gabriel/.venvs/comfy-agent/Scripts/uv.exe"
if [ ! -f "$UV" ]; then
  UV="$(command -v uv 2>/dev/null || true)"
fi
if [ -z "${UV:-}" ] || [ ! -x "$UV" ]; then
  echo "uv nao encontrado; usando venv + pip do python do sistema"
  PY="C:/Users/Gabriel/AppData/Local/Programs/Python/Python313/python.exe"
  "$PY" -m venv .venv || exit 1
  exec ".venv/Scripts/python.exe" -m pip install --upgrade pip "qwen-tts"
fi

echo "=== uv: $UV ==="
"$UV" venv .venv --python 3.11 || exit 1
"$UV" pip install --python .venv/Scripts/python.exe "qwen-tts" || exit 1

echo
echo "=== confirmando ==="
".venv/Scripts/python.exe" -c "import importlib.metadata as m; print('qwen-tts', m.version('qwen-tts')); import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
