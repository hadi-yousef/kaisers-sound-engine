#!/bin/bash
# Doppelklick im Finder: startet die Sound-Engine und öffnet sie im Browser (http://127.0.0.1:47811 oder der nächste freie Port).
# Dieses Fenster offen lassen, solange du sprechen lässt – Schließen beendet die Sound-Engine.
DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$DIR"
# läuft sie schon? (.adresse schreibt der Server beim Start; die Kennung prüfen, damit kein fremder Dienst geöffnet wird)
if [ -f .adresse ] && curl -s -m 2 "$(cat .adresse)api/stimmen" 2>/dev/null | grep -q kaisers-sound-engine; then echo "Die Sound-Engine läuft schon – öffne den Browser."; open "$(cat .adresse)"; exit 0; fi
for P in "$SOUND_ENGINE_PYTHON" "$DIR/.venv/bin/python"; do
  if [ -n "$P" ] && [ -x "$P" ] && "$P" -c "import mlx_audio, soundfile" >/dev/null 2>&1; then
    exec env TOKENIZERS_PARALLELISM=false PYTHONWARNINGS=ignore "$P" "$DIR/server.py" "$@"
  fi
done
echo "Die Sound-Engine ist auf diesem Mac noch nicht eingerichtet."
read -r -p "Jetzt einrichten? (einige Minuten, lädt mehrere GB)  [j/n] " A
if [ "$A" = "j" ] || [ "$A" = "J" ]; then ./einrichten.sh --modelle && exec "$0"; fi
read -r -p "Enter zum Schließen."
