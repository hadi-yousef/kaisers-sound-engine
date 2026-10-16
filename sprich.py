# Kaiser’s Sound-Engine – Text sprechen lassen (Kommandozeile).
# Einfacher: Doppelklick auf „Sound-Engine starten.command“ → Oberfläche im Browser.
#   ./sprich <stimme> "Text"                 → ausgabe/<stimme>-<zeit>.mp3   (Stimmen: doku, haupt)
#   ./sprich <stimme> text.txt               → eine Zeile = ein Satz (oder ein Absatz, der in Sätze geteilt wird)
#   ./sprich --stimmen                       → alle Stimmen anzeigen
# Optionen: -o <datei.mp3|.wav|.m4a>   Zieldatei
#           --klang grammophon|rein|saal|trocken   (Standard: der Klang der Stimme)
#           --woertlich   Text nicht in Sprechfassung umwandeln (sonst „230 V“ → „zweihundertdreißig Volt“; nur Deutsch)
#           --pause <s>   Pause zwischen Sätzen (Standard 0,8 s)   --lautheit <LUFS> (Standard −18)
#           --schnell     ohne Whisper-Prüfung, je Satz nur ein Versuch   --seed <n>  andere, ebenfalls wiederholbare Variante
#           --einzeln     zusätzlich jeden Satz als eigene Datei (ausgabe/<name>/satz-01.wav …)
import os, sys, datetime, argparse

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
from engine import stimmen as ST
from engine.klang import ffmpeg_da

def main():
    ap = argparse.ArgumentParser(prog='sprich', description='Text mit den Stimmen der Engine sprechen')
    ap.add_argument('stimme', nargs='?'); ap.add_argument('text', nargs='?')
    ap.add_argument('-o', '--aus'); ap.add_argument('--klang'); ap.add_argument('--woertlich', action='store_true')
    ap.add_argument('--pause', type=float, default=0.8); ap.add_argument('--lautheit', type=float, default=-18.0)
    ap.add_argument('--schnell', action='store_true'); ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--einzeln', action='store_true'); ap.add_argument('--stimmen', action='store_true')
    a = ap.parse_args()

    if a.stimmen or not a.stimme:
        print('Stimmen:')
        for s in ST.liste():
            S = s['steckbrief']; fa = '  ⚠ Vorlage verändert (Fingerabdruck passt nicht)' if s['fingerabdruck'] is False else ''
            print(f"  {s['id']:<11} {s['name']} – {S.get('kurz', '')} · Sprache {s['sprache']} · Klang {s['klang']}{fa}\n              {S.get('beschreibung', '')}")
        print('\nAufruf:  ./sprich <stimme> "Text"   (Hilfe: ./sprich -h)')
        return
    if not a.text: raise SystemExit('✗ Text fehlt:  ./sprich <stimme> "Text"  oder  ./sprich <stimme> datei.txt')
    if not ffmpeg_da(): raise SystemExit('✗ ffmpeg fehlt – einmal installieren:  brew install ffmpeg')
    st = ST.laden(a.stimme)
    if st['fingerabdruck'] is False: print(f"⚠ Die Vorlage der Stimme „{st['id']}“ wurde verändert (SHA256SUMS passt nicht).")
    text = open(a.text, encoding='utf-8').read() if os.path.isfile(a.text) else a.text
    jetzt = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    ziel = os.path.abspath(a.aus) if a.aus else os.path.join(HIER, 'ausgabe', f"{st['id']}-{jetzt}.mp3")
    print(f"→ {st['name']} · Klang {a.klang or st['klang']}\n  (beim ersten Satz wird das Sprachmodell geladen – einige Sekunden)")

    from engine.tts import Sprecher
    from engine.auftrag import sprechen
    def melde(i, n, t, info):
        herkunft = 'aus dem Lager' if info.get('aus_lager') else f"{info['rechenzeit']} s Rechenzeit, Versuch {info['versuch']}"
        warn = f"  ⚠ unsicher, gehört: „{info.get('gehoert')}“" if (info.get('quote') or 0) > 0.3 else ''
        print(f"  {i}/{n}  {info['dauer']} s  ({herkunft}){'' if info.get('quote') is None else '  Quote ' + str(info['quote'])}{warn}\n        {t}")
    sp = Sprecher(os.path.join(HIER, 'lager'), seed_basis=a.seed, pruefen=not a.schnell, melde=lambda *_: None)
    sprechen(st['id'], text, ziel, sp, klang=a.klang, pause=a.pause, lautheit=a.lautheit, woertlich=a.woertlich, einzeln=a.einzeln, fortschritt=melde)
    print(f'✓ {ziel}')

if __name__ == '__main__':
    main()
