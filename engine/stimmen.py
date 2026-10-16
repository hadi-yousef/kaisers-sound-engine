# Stimmen-Bibliothek: jeder Ordner in stimmen/ mit referenz.wav + referenz.txt ist eine Stimme (id = Ordnername).
# steckbrief.json (Name, Beschreibung), einstellungen.json (Sprech-Einstellungen, Sprache, Klang), SHA256SUMS (Fingerabdruck der Vorlage).
import os, json, hashlib

HIER = os.path.dirname(os.path.abspath(__file__))
STIMMEN = os.path.join(os.path.dirname(HIER), 'stimmen')

def _json(p, std=None):
    try: return json.load(open(p, encoding='utf-8'))
    except Exception: return std if std is not None else {}

def liste():
    out = []
    for d in sorted(os.listdir(STIMMEN)) if os.path.isdir(STIMMEN) else []:
        p = os.path.join(STIMMEN, d)
        if os.path.exists(os.path.join(p, 'referenz.wav')) and os.path.exists(os.path.join(p, 'referenz.txt')): out.append(laden(d))
    return out

def fingerabdruck_ok(p):
    sums = os.path.join(p, 'SHA256SUMS')
    if not os.path.exists(sums): return None
    for zeile in open(sums):
        teile = zeile.split()
        if len(teile) == 2:
            h, f = teile
            if hashlib.sha256(open(os.path.join(p, f), 'rb').read()).hexdigest() != h: return False
    return True

def laden(sid):
    p = os.path.join(STIMMEN, sid)
    if not os.path.exists(os.path.join(p, 'referenz.wav')): raise SystemExit(f"✗ Stimme „{sid}“ gibt es nicht. Vorhanden: {', '.join(s['id'] for s in liste())}")
    E = _json(os.path.join(p, 'einstellungen.json')); S = _json(os.path.join(p, 'steckbrief.json'))
    return {'id': sid, 'ordner': p, 'ref': os.path.join(p, 'referenz.wav'), 'ref_text': open(os.path.join(p, 'referenz.txt'), encoding='utf-8').read().strip(),
            'einstellungen': E, 'steckbrief': S, 'name': S.get('name', sid), 'sprache': E.get('sprache', 'de'), 'klang': E.get('klang', 'trocken'),
            'deesser': E.get('deesser', 0.6), 'fingerabdruck': fingerabdruck_ok(p)}
