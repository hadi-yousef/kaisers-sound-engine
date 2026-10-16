# Verständlichkeit prüfen: Whisper (MLX) transkribiert eine Sprachprobe zurück,
# gezählt werden Wortfehler gegen den Solltext. quote = Fehler / Wörter (0 = perfekt).
# Seit 2026-10-15: Ziffern in Whispers Mitschrift werden vorher in Zahlwörter übersetzt („3000“ → „dreitausend“, „7,2“ → „sieben
# komma zwei“) – sonst zählte jede richtig gesprochene Zahl als Fehler (188 von 246 Verdachtsfällen der Natürlichkeitsprüfung).
import re, difflib
from mlx_audio.stt.utils import load_model

WHISPER = 'mlx-community/whisper-large-v3-turbo'
_model = None
_norm = lambda s: re.sub(r'[^a-zäöüß0-9 ]', ' ', s.lower()).split()

EINS = ['', 'eins', 'zwei', 'drei', 'vier', 'fünf', 'sechs', 'sieben', 'acht', 'neun', 'zehn', 'elf', 'zwölf', 'dreizehn', 'vierzehn',
        'fünfzehn', 'sechzehn', 'siebzehn', 'achtzehn', 'neunzehn']
ZEHN = ['', '', 'zwanzig', 'dreißig', 'vierzig', 'fünfzig', 'sechzig', 'siebzig', 'achtzig', 'neunzig']
def _u100(n):
    if n < 20: return EINS[n]
    e, z = n % 10, n // 10
    return (('ein' if e == 1 else EINS[e]) + 'und' if e else '') + ZEHN[z]
def _u1000(n):
    h, r = divmod(n, 100)
    return (('ein' if h == 1 else EINS[h]) + 'hundert' if h else '') + (_u100(r) if r else '')
def zahlwort(n):
    # wie zahlwort() in public/js/bausteine/lehrbuch/sprache.js
    if n == 0: return 'null'
    teile = []; mrd, n = divmod(n, 10**9); mio, n = divmod(n, 10**6); tsd, rest = divmod(n, 1000)
    if mrd: teile.append('eine milliarde' if mrd == 1 else zahlwort(mrd) + ' milliarden')
    if mio: teile.append('eine million' if mio == 1 else zahlwort(mio) + ' millionen')
    if tsd: teile.append(('ein' if tsd == 1 else _u1000(tsd)) + 'tausend')
    if rest: teile.append(_u1000(rest))
    return ' '.join(teile).replace('tausend ', 'tausend')
def _zahl(m):
    roh = m.group(1); ganz = int(roh.replace('.', ''))
    if m.group(2) is None and '.' not in roh and 1100 <= ganz <= 1999:      # Jahreszahl wie in sprache.js: neunzehnhundertvierundfünfzig
        w = _u100(ganz // 100) + 'hundert' + (_u100(ganz % 100) if ganz % 100 else '')
    else: w = zahlwort(ganz)
    if m.group(2):                                                          # wie gesprochen: „drei komma fünfundachtzig“
        d = m.group(2); w += ' komma ' + (zahlwort(int(d)) if not d.startswith('0') else ' '.join(zahlwort(int(c)) if c != '0' else 'null' for c in d))
    return ' ' + w + ' '
def zahlen_als_worte(s):
    # 1.000 / 10.000 (Tausenderpunkt), 7,2 (Komma), 50 % → fünfzig prozent
    s = s.replace('%', ' prozent ')
    return re.sub(r'(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?', _zahl, s)

# Englische Stimmen (einstellungen.json „sprache“: 'en'): Whisper schreibt Ziffern („230 volts“) – als englische Zahlwörter vergleichen.
# Zehner und Einer zusammen („fiftyfive“), weil norm() Bindestriche tilgt („fifty-five“); „and“ zählt nicht („two hundred and thirty“).
EN1 = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen',
       'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen']
EN10 = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
def _en(n):
    if n == 0: return 'zero'
    out = []
    for teil, wort in [(n // 1000000, ' million'), (n // 1000 % 1000, ' thousand'), (n % 1000, '')]:
        if not teil: continue
        h, r = divmod(teil, 100)
        w = (EN1[h] + ' hundred ' if h else '') + (EN1[r] if r < 20 else EN10[r // 10] + EN1[r % 10])
        out.append(w.strip() + wort)
    return ' '.join(out)
def zahlen_en(s):
    s = s.replace('%', ' percent ')
    s = re.sub(r'(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?', lambda m: ' ' + _en(int(m.group(1).replace(',', ''))) + (' point ' + ' '.join(_en(int(c)) for c in m.group(2)) if m.group(2) else '') + ' ', s)
    return re.sub(r'\band\b', ' ', s)

def norm(s, sprache='de'):
    # gemeinsame Schreibweise für Soll und Gehörtes: Zahlen als Wörter, buchstabierte Abkürzungen zusammen („L E D“ = „LED“),
    # Bindestrich-Wörter zusammen („Drei-Phasen-Wechselstrom“ = „Dreiphasenwechselstrom“) – Fehler sind nur anders gesprochene Wörter
    s = zahlen_en(s.lower()) if sprache == 'en' else zahlen_als_worte(s.lower())
    s = re.sub(r'\b(?:[a-zäöü] )+[a-zäöü](?:s\b|\b)', lambda m: m.group(0).replace(' ', ''), s)
    s = re.sub(r'(?<=\w)-(?=\w)', '', s)
    return _norm(s)

def check(wav, soll, sprache='de'):
    global _model
    _model = _model or load_model(WHISPER)
    gehoert = _model.generate(wav, language=sprache).text.strip()
    a, b = norm(soll, sprache), norm(gehoert, sprache)
    ops = difflib.SequenceMatcher(None, a, b).get_opcodes()
    fehler = sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in ops if tag != 'equal')
    return {'fehler': fehler, 'woerter': len(a), 'quote': round(fehler / max(1, len(a)), 3), 'gehoert': gehoert}
