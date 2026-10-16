#!/bin/bash
# Kaiser’s Sound-Engine einrichten (einmalig): eigene Python-Umgebung .venv mit mlx-audio (Qwen3-TTS + Whisper über MLX).
# Braucht einen Mac mit Apple Silicon (M1 oder neuer, ≥ 16 GB Arbeitsspeicher empfohlen), Python 3.10–3.13 und ffmpeg.
#   ./einrichten.sh            → Umgebung anlegen
#   ./einrichten.sh --modelle  → zusätzlich die Modelle vorab laden (sonst beim ersten Sprechen, mehrere GB)
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$DIR"
if [ "$(uname -s)" != "Darwin" ] || [ "$(uname -m)" != "arm64" ]; then echo "✗ Nur auf einem Mac mit Apple Silicon (MLX)."; exit 1; fi
PY=""
for c in python3.12 python3.11 python3.13 python3.10 python3; do
  if command -v $c >/dev/null 2>&1; then v=$($c -c 'import sys; print("%d.%d" % sys.version_info[:2])'); case "$v" in 3.10|3.11|3.12|3.13) PY=$c; break;; esac; fi
done
[ -z "$PY" ] && { echo "✗ Kein Python 3.10–3.13 gefunden. Installieren:  brew install python@3.12"; exit 1; }
echo "✓ $($PY --version)"
[ -x .venv/bin/python ] || { echo "→ lege .venv an …"; $PY -m venv .venv; }
echo "→ installiere mlx-audio 0.5.9 und soundfile (einige hundert MB) …"
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -r requirements.txt
.venv/bin/python -c "import mlx_audio, soundfile, numpy" && echo "✓ mlx-audio bereit"
command -v ffmpeg >/dev/null 2>&1 && echo "✓ ffmpeg gefunden" || echo "! ffmpeg fehlt – installieren:  brew install ffmpeg"
if [ "$1" = "--modelle" ]; then
  echo "→ lade Modelle (Qwen3-TTS 1.7B Base, Whisper large-v3-turbo) …"
  .venv/bin/python -c "from mlx_audio.tts.utils import load_model; load_model('mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16'); from mlx_audio.stt.utils import load_model as l2; l2('mlx-community/whisper-large-v3-turbo'); print('✓ Modelle geladen')"
fi
echo "Fertig.  ./sprich --stimmen   ·   ./sprich doku \"Hallo, so klinge ich.\""
