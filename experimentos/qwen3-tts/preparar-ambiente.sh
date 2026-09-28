#!/usr/bin/env bash
# Monta o ambiente isolado do Qwen3-TTS. Nao toca na base nem no venv do app.
#
#   bash experimentos/qwen3-tts/preparar-ambiente.sh
#
# Precisa de uv (recomendado) ou de um python 3.11 ou mais novo no PATH.
# Os caminhos saem da posicao deste arquivo, entao funciona em qualquer maquina.
set -u

DESTINO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DESTINO" || exit 1
echo "=== pasta: $(pwd) ==="

PY_PROJETO=".venv/Scripts/python.exe"
[ -f "$PY_PROJETO" ] || PY_PROJETO=".venv/bin/python"

# O indice padrao do PyPI entrega torch de CPU. Pedir o mesmo numero de versao
# vindo do indice CUDA nao basta: o uv responde "Checked" e nao reinstala, e voce
# fica com torch +cpu sem perceber. Por isso --reinstall, e por isso cu130:
# a versao 2.14 existe em cu130, enquanto cu128 para em 2.11.
INDICE_CUDA="https://download.pytorch.org/whl/cu130"

if command -v uv >/dev/null 2>&1; then
  UV="$(command -v uv)"
  echo "=== uv: $UV ==="
  "$UV" venv .venv --python 3.11 || exit 1
  "$UV" pip install --python "$PY_PROJETO" "qwen-tts" || exit 1
  "$UV" pip install --python "$PY_PROJETO" --reinstall torch torchaudio \
    --index-url "$INDICE_CUDA" || exit 1
else
  echo "=== uv nao encontrado; usando python -m venv + pip ==="
  PY="$(command -v python3 || command -v python || true)"
  if [ -z "$PY" ]; then
    echo "python nao encontrado no PATH" >&2
    exit 1
  fi
  # O qwen-tts pede ambiente limpo, e o ecossistema do torch costuma demorar a
  # publicar pacote para as versoes mais novas de python. Fora desta faixa o
  # risco de nao achar pacote pronto e alto, entao avisa antes de tentar.
  VERSAO="$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "?")"
  case "$VERSAO" in
    3.10|3.11|3.12) ;;
    *)
      echo "AVISO: o python encontrado e $VERSAO. O qwen-tts recomenda 3.12 e o torch"
      echo "       pode nao ter pacote pronto para essa versao."
      echo "       Se a instalacao falhar, instale o uv e rode este script de novo:"
      echo "       com uv a versao certa e baixada automaticamente."
      ;;
  esac
  "$PY" -m venv .venv || exit 1
  "$PY_PROJETO" -m pip install --upgrade pip "qwen-tts" || exit 1
  "$PY_PROJETO" -m pip install --force-reinstall torch torchaudio \
    --index-url "$INDICE_CUDA" || exit 1
fi

echo
echo "=== confirmando ==="
"$PY_PROJETO" -c "import importlib.metadata as m; print('qwen-tts', m.version('qwen-tts')); import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
echo
echo "Se cuda vier False, o torch instalado e build de CPU: rode de novo com uv."
