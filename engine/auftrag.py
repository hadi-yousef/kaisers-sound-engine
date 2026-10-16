# Ein Sprech-Auftrag von Anfang bis Ende: Text → Sätze → Sprechfassung → Stimme → Prüfung → Spur → Klang → Datei.
# Gemeinsam für die Kommandozeile (sprich.py) und die Oberfläche im Browser (server.py).
import os, re, io, tempfile, contextlib
import soundfile as sf
from . import stimmen as ST
from .sprache import sprich as sprechfassung
from .klang import fertig_machen

os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1'); os.environ.setdefault('TRANSFORMERS_VERBOSITY', 'error')

def saetze_aus(text):
    out = []
    for zeile in text.replace('\r', '').split('\n'):
        out += [t.strip() for t in re.split(r'(?<=[.!?…])\s+', zeile) if t.strip()]
    return out

def sprechen(stimme_id, text, ziel, sprecher, klang=None, pause=0.8, lautheit=-18.0, woertlich=False, einzeln=False, fortschritt=None):
    """Text mit der Stimme sprechen und als ziel (.mp3/.wav/.m4a) speichern. fortschritt(i, n, satz, info) nach jedem Satz.
    sprecher = engine.tts.Sprecher (hält das Modell geladen – für mehrere Aufträge wiederverwenden)."""
    from .tts import zusammen, SR
    st = ST.laden(stimme_id)
    saetze = saetze_aus(text)
    if not saetze: raise ValueError('Kein Text')
    wort = woertlich or st['sprache'] != 'de'          # Sprechfassung (Zahlen → Wörter) nur auf Deutsch
    gesprochen = [t if wort else sprechfassung(t) for t in saetze]
    teile, infos = [], []
    for i, t in enumerate(gesprochen):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):   # Lade-Meldungen der Modelle ausblenden
            audio, info = sprecher.satz(t, st)
        teile.append(audio); infos.append(info)
        if fortschritt: fortschritt(i + 1, len(gesprochen), t, info)
    os.makedirs(os.path.dirname(os.path.abspath(ziel)), exist_ok=True)
    k = klang or st['klang']
    with tempfile.TemporaryDirectory() as tmp:
        roh = os.path.join(tmp, 'spur.wav'); sf.write(roh, zusammen(teile, pause=pause), SR)
        fertig_machen(roh, ziel, k, st['deesser'], lautheit)
        if einzeln:
            ordner = os.path.splitext(ziel)[0]; os.makedirs(ordner, exist_ok=True)
            for i, a in enumerate(teile):
                p = os.path.join(tmp, f'satz-{i + 1:02d}.wav'); sf.write(p, zusammen([a], vorlauf=0.05, nachlauf=0.1), SR)
                fertig_machen(p, os.path.join(ordner, f'satz-{i + 1:02d}.wav'), k, st['deesser'], lautheit)
    return {'datei': ziel, 'stimme': st, 'saetze': gesprochen, 'infos': infos, 'klang': k, 'sprechfassung': not wort}
