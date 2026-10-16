# Kaiser’s Sound-Engine – Oberfläche im Browser: Text eingeben, Stimme wählen, sprechen lassen, anhören, herunterladen.
#   Doppelklick auf „Sound-Engine starten.command“ – oder:  python server.py [--port 47811] [--netz] [--ohne-browser]
#   Ist der Port belegt, nimmt sie den nächsten freien; die Adresse steht dann in .adresse (der Starter liest sie).
#   --netz: auch für andere Geräte im Heimnetz erreichbar (Standard: nur dieser Mac)
# Ohne zusätzliche Pakete (nur Python-Standardbibliothek + die Sound-Engine). Aufträge laufen nacheinander (eine GPU); das Sprachmodell
# bleibt zwischen den Aufträgen geladen – ab dem zweiten Text geht es schneller.
import os, sys, json, threading, queue, time, uuid, datetime, re, argparse, webbrowser, atexit, signal
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote, quote, parse_qs

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
from engine import stimmen as ST
from engine.klang import ffmpeg_da, KETTEN
from engine.auftrag import saetze_aus

AUSGABE = os.path.join(HIER, 'ausgabe'); WEB = os.path.join(HIER, 'web')
AUFTRAEGE, Q, SPERRE = {}, queue.Queue(), threading.Lock()
MAX_ZEICHEN = 30000

def dateiname(A):
    worte = re.sub(r'[^\wäöüÄÖÜß ]+', ' ', A['text']).split()[:5]
    kurz = '-'.join(worte)[:48] or 'text'
    return f"{A['stimme']}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}-{kurz}.{A['format']}"

def arbeiter():
    from engine.tts import Sprecher
    from engine.auftrag import sprechen
    sp = Sprecher(os.path.join(HIER, 'lager'), melde=lambda *_: None)
    while True:
        jid = Q.get(); A = AUFTRAEGE[jid]
        A.update(status='laeuft', gestartet=time.time())
        try:
            sp.pruefen = not A['schnell']; sp.basis = A['seed']
            def fs(i, n, t, info):
                A.update(i=i, satz=t)
                if (info.get('quote') or 0) > 0.3: A['unsicher'].append({'satz': t, 'gehoert': info.get('gehoert')})
            name = dateiname(A)
            r = sprechen(A['stimme'], A['text'], os.path.join(AUSGABE, name), sp, klang=A['klang'] or None, pause=A['pause'],
                         woertlich=A['woertlich'], fortschritt=fs)
            A.update(status='fertig', datei=name, sekunden=round(time.time() - A['gestartet'], 1), klang=r['klang'])
        except BaseException as e:   # auch SystemExit aus Hilfsfunktionen
            A.update(status='fehler', fehler=str(e) or type(e).__name__)
        finally:
            Q.task_done()

def stimmen_json():
    out = []
    for s in ST.liste():
        S = s['steckbrief']
        out.append({'id': s['id'], 'name': s['name'], 'kurz': S.get('kurz', ''), 'beschreibung': S.get('beschreibung', ''), 'sprache': s['sprache'],
                    'klang': s['klang'], 'passt_fuer': S.get('passt_fuer', []), 'probe': f"/probe/{s['id']}.mp3" if os.path.exists(os.path.join(s['ordner'], 'probe.mp3')) else None,
                    'fingerabdruck_ok': s['fingerabdruck'] is not False})
    return out

def verlauf():
    if not os.path.isdir(AUSGABE): return []
    dateien = [f for f in os.listdir(AUSGABE) if f.lower().endswith(('.mp3', '.wav')) and os.path.isfile(os.path.join(AUSGABE, f))]
    dateien.sort(key=lambda f: os.path.getmtime(os.path.join(AUSGABE, f)), reverse=True)
    return [{'datei': f, 'zeit': datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(AUSGABE, f))).strftime('%d.%m. %H:%M')} for f in dateien[:20]]

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header('Content-Type', 'application/json; charset=utf-8'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def _datei(self, p, typ, download=None):
        if not os.path.isfile(p): return self._json({'fehler': 'nicht gefunden'}, 404)
        size = os.path.getsize(p)
        self.send_response(200); self.send_header('Content-Type', typ); self.send_header('Content-Length', str(size))
        if download: self.send_header('Content-Disposition', f"attachment; filename*=UTF-8''{quote(download)}")
        self.end_headers()
        with open(p, 'rb') as f:
            while True:
                b = f.read(1 << 16)
                if not b: break
                self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path); pfad = unquote(u.path)
        if pfad in ('/', '/index.html'): return self._datei(os.path.join(WEB, 'index.html'), 'text/html; charset=utf-8')
        if pfad == '/api/stimmen': return self._json({'engine': 'kaisers-sound-engine', 'stimmen': stimmen_json(), 'klaenge': list(KETTEN), 'ffmpeg': ffmpeg_da(), 'max_zeichen': MAX_ZEICHEN})
        if pfad == '/api/verlauf': return self._json(verlauf())
        m = re.match(r'^/api/auftrag/([0-9a-f]+)$', pfad)
        if m:
            A = AUFTRAEGE.get(m.group(1))
            if not A: return self._json({'fehler': 'unbekannter Auftrag'}, 404)
            vor = sum(1 for B in AUFTRAEGE.values() if B['status'] == 'wartet' and B['nr'] < A['nr'])
            sicht = {k: A[k] for k in ('status', 'i', 'n', 'satz', 'datei', 'fehler', 'sekunden', 'unsicher', 'stimme', 'klang')}
            return self._json({**sicht, 'vor_dir': vor + (1 if A['status'] == 'wartet' and any(B['status'] == 'laeuft' for B in AUFTRAEGE.values()) else 0)})
        m = re.match(r'^/probe/([\w-]+)\.mp3$', pfad)
        if m: return self._datei(os.path.join(ST.STIMMEN, m.group(1), 'probe.mp3'), 'audio/mpeg')
        m = re.match(r'^/ausgabe/([^/]+)$', pfad)
        if m:
            name = os.path.basename(m.group(1)); typ = 'audio/mpeg' if name.lower().endswith('.mp3') else 'audio/wav'
            return self._datei(os.path.join(AUSGABE, name), typ, name if 'download' in parse_qs(u.query) else None)
        self._json({'fehler': 'nicht gefunden'}, 404)
    def do_POST(self):
        if urlparse(self.path).path != '/api/sprechen': return self._json({'fehler': 'nicht gefunden'}, 404)
        try: d = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
        except Exception: return self._json({'fehler': 'ungültige Anfrage'}, 400)
        text = (d.get('text') or '').strip(); sid = d.get('stimme') or ''
        if not text: return self._json({'fehler': 'Bitte einen Text eingeben.'}, 400)
        if len(text) > MAX_ZEICHEN: return self._json({'fehler': f'Text zu lang (höchstens {MAX_ZEICHEN} Zeichen).'}, 400)
        if sid not in {s['id'] for s in ST.liste()}: return self._json({'fehler': 'Bitte eine Stimme wählen.'}, 400)
        klang = d.get('klang') or ''
        if klang and klang not in KETTEN: return self._json({'fehler': 'Unbekannter Klang.'}, 400)
        with SPERRE:
            jid = uuid.uuid4().hex[:12]
            AUFTRAEGE[jid] = {'nr': len(AUFTRAEGE), 'status': 'wartet', 'i': 0, 'n': len(saetze_aus(text)), 'satz': '', 'datei': None, 'fehler': None,
                              'sekunden': None, 'unsicher': [], 'text': text, 'stimme': sid, 'klang': klang, 'pause': float(d.get('pause') or 0.8),
                              'woertlich': bool(d.get('woertlich')), 'schnell': bool(d.get('schnell')), 'seed': int(d.get('seed') or 0),
                              'format': 'wav' if d.get('format') == 'wav' else 'mp3'}
        Q.put(jid)
        self._json({'id': jid})

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--port', type=int, default=47811); ap.add_argument('--netz', action='store_true'); ap.add_argument('--ohne-browser', action='store_true')
    a = ap.parse_args()
    if not ffmpeg_da(): print('⚠ ffmpeg fehlt – einmal installieren:  brew install ffmpeg')
    os.makedirs(AUSGABE, exist_ok=True)
    threading.Thread(target=arbeiter, daemon=True).start()
    host = '0.0.0.0' if a.netz else '127.0.0.1'
    srv = None
    for port in range(a.port, a.port + 40):                       # belegter Port (andere App) → nächsten freien nehmen
        try: srv = ThreadingHTTPServer((host, port), Handler); break
        except OSError: continue
    if srv is None: raise SystemExit(f'✗ Kein freier Port zwischen {a.port} und {a.port + 39}.')
    url = f'http://127.0.0.1:{port}/'
    adresse = os.path.join(HIER, '.adresse'); open(adresse, 'w').write(url)
    atexit.register(lambda: os.path.exists(adresse) and os.remove(adresse))
    for sig in (signal.SIGTERM, signal.SIGHUP): signal.signal(sig, lambda *_: sys.exit(0))   # Terminal-Fenster geschlossen → sauber beenden
    print(f"Kaiser’s Sound-Engine läuft: {url}" + ('  (auch im Heimnetz erreichbar)' if a.netz else ''))
    print('Dieses Fenster offen lassen. Beenden: Fenster schließen oder Ctrl+C.')
    if not a.ohne_browser: threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try: srv.serve_forever()
    except KeyboardInterrupt: print('\nBeendet.')

if __name__ == '__main__':
    main()
