# Nachbearbeitung mit ffmpeg: De-Esser (Standard 0,6 wie in den Filmen), Klang der Stimme, Lautheit, Ausgabeformat.
# Klang-Ketten (ffmpeg):
#   grammophon – Kinoerzähler: Hochpass 210 Hz, Präsenz +5 dB bei 1,6 kHz, Röhrensättigung (tanh), Tiefpass 3,7 kHz, etwas Saal
#   rein       – Doku-Stimme: nur ein sanfter Hochpass (60 Hz) gegen Brummen
#   saal       – eigene Stimme: Hochpass 90 Hz, Kanten bei 3,2 kHz −2,5 dB, sanfter Kompressor, Hall wie im Saal
#   trocken    – keine Färbung (nur De-Esser und Lautheit)
import subprocess, shutil

KETTEN = {
    'grammophon': ['highpass=f=210:width_type=q:width=0.8', 'equalizer=f=1600:width_type=q:width=1:g=5', 'volume=1.8',
                   'asoftclip=type=tanh', 'volume=1.05', 'lowpass=f=3700:width_type=q:width=0.7', 'aecho=0.85:0.55:38|67:0.16|0.09'],
    'rein': ['highpass=f=60:width_type=q:width=0.7'],
    'saal': ['highpass=f=90:width_type=q:width=0.7', 'equalizer=f=3200:width_type=q:width=1:g=-2.5',
             'acompressor=threshold=0.125:ratio=2.5:attack=10:release=200', 'aecho=0.85:0.55:41|73:0.14|0.08'],
    'trocken': [],
}

def ffmpeg_da(): return shutil.which('ffmpeg') is not None

def fertig_machen(wav_in, ziel, klang='trocken', deesser=0.6, lautheit=-18.0):
    """wav_in (24 kHz mono) → ziel (.mp3/.wav/.m4a…) mit De-Esser, Klang-Kette und Lautheit (LUFS)"""
    if klang not in KETTEN: raise SystemExit(f"✗ Klang „{klang}“ gibt es nicht ({', '.join(KETTEN)})")
    af = ([f'deesser=i={deesser}:m=0.5:f=0.5'] if deesser > 0 else []) + KETTEN[klang] + [f'loudnorm=I={lautheit}:TP=-1.5:LRA=11', 'aresample=48000']
    format_ = ['-b:a', '160k'] if ziel.lower().endswith(('.mp3', '.m4a', '.aac')) else []
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav_in, '-af', ','.join(af), *format_, ziel], capture_output=True, text=True)
    if r.returncode: raise SystemExit('✗ ffmpeg: ' + r.stderr.strip()[-400:])
