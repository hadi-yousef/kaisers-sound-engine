# Sprachkern: Qwen3-TTS (lokal über MLX, Mac mit Apple Silicon) klont eine Stimme aus ihrer Vorlage (stimmen/<id>/referenz.wav +
# referenz.txt) und spricht Satz für Satz :
#   je Satz bis zu N Versuche (Temperatur je Stimme), vor jedem Versuch ein fester Seed (aus Satz-Kennung + Versuch) → wiederholbar,
#   Satz unverändert ans Modell, 40 ms Rand, kurze Blende, Whisper hört nach und entscheidet (Wortfehler-Quote, 0 = perfekt).
# Satz-Lager: gleicher Text + gleiche Stimme → die vorhandene Aufnahme wird wiederverwendet (lager/<stimme>/).
import os, json, hashlib, time
import numpy as np, soundfile as sf

CLONE = 'mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16'
SR = 24000

def fnv(t):
    # Satz-Kennung (FNV-1a, 32 Bit, Basis 36) → fester Seed je Satz, gleiche Aufnahmen bei jedem Lauf
    h = 2166136261
    for ch in t:
        h ^= ord(ch); h = (h * 16777619) & 0xFFFFFFFF
    z, s = '0123456789abcdefghijklmnopqrstuvwxyz', ''
    while True:
        h, r = divmod(h, 36); s = z[r] + s
        if not h: return s

def seed_fuer(*teile, basis=0):
    return int(hashlib.sha256('/'.join(map(str, (*teile, basis))).encode()).hexdigest()[:8], 16)

def to_np(rs): return np.concatenate([np.array(r.audio, dtype=np.float32).reshape(-1) for r in rs])
def trim(a, thr=0.008, keep=0.04, sr=SR):
    i = np.where(np.abs(a) > thr)[0]
    return a if not len(i) else a[max(0, i[0] - int(keep * sr)): i[-1] + int(keep * sr)]
def fade(a, sr, ms=10):
    n = min(len(a) // 2, int(sr * ms / 1000)); a = a.copy()
    if n: a[:n] *= np.linspace(0, 1, n); a[-n:] *= np.linspace(1, 0, n)
    return a

class Sprecher:
    def __init__(self, lager_dir, seed_basis=0, pruefen=True, melde=print):
        self.m = None; self.lager_dir = lager_dir; self.basis = seed_basis; self.pruefen = pruefen; self.melde = melde

    def _modell(self):
        if self.m is None:
            from mlx_audio.tts.utils import load_model
            self.melde('  … lade das Sprachmodell (beim ersten Mal lädt es mehrere GB herunter)')
            self.m = load_model(CLONE)
        return self.m

    def satz(self, text, st):
        """Einen Satz mit Stimme st (dict aus stimmen.laden) sprechen → (Audio float32 24 kHz, Info)"""
        sid = 's-' + fnv(text)
        ldir = os.path.join(self.lager_dir, st['id']); os.makedirs(ldir, exist_ok=True)
        wav, meta = os.path.join(ldir, sid + '.wav'), os.path.join(ldir, sid + '.json')
        if os.path.exists(wav) and os.path.exists(meta):
            info = json.load(open(meta))
            if info.get('text') == text and info.get('seed_basis', 0) == self.basis and (info.get('geprueft') or not self.pruefen):
                a, _ = sf.read(wav, dtype='float32'); return a, {**info, 'aus_lager': True}
        import mlx.core as mx
        m = self._modell(); E = st['einstellungen']
        temp, versuche, schwelle, blende = E.get('temperatur', [0.65, 0.75]), E.get('versuche', 4), E.get('schwelle', 0.1), E.get('blende_ms', 10)
        sprache = E.get('sprache', 'de'); lang = {'de': 'German', 'en': 'English'}[sprache]
        best = None; t0 = time.time()
        for v in range(versuche if self.pruefen else 1):
            mx.random.seed(seed_fuer('satz', sid, v + 1, basis=self.basis))
            roh = to_np(m.generate(text=text, ref_audio=st['ref'], ref_text=st['ref_text'], lang_code=lang, temperature=temp[0] if v == 0 else temp[1]))
            a = fade(trim(roh), SR, blende); sf.write(wav, a, SR)
            if not self.pruefen: best = (0, a, None, None, v + 1); break
            from .pruefen import check
            c = check(wav, text, sprache)
            if best is None or c['quote'] < best[0]: best = (c['quote'], a, c['gehoert'], c['quote'], v + 1)
            if c['quote'] <= schwelle: break
        _, a, gehoert, quote, nr = best; sf.write(wav, a, SR)
        info = {'text': text, 'stimme': st['id'], 'dauer': round(len(a) / SR, 2), 'quote': quote, 'gehoert': gehoert, 'versuch': nr,
                'seed': seed_fuer('satz', sid, nr, basis=self.basis), 'seed_basis': self.basis, 'geprueft': self.pruefen, 'rechenzeit': round(time.time() - t0, 1)}
        json.dump(info, open(meta, 'w'), ensure_ascii=False, indent=1)
        return a, info

def zusammen(teile, vorlauf=0.3, pause=0.8, nachlauf=0.5):
    """Sätze zu einer Spur: Stille vorn, Pause zwischen den Sätzen (Standard 0,8 s wie in den Filmen), Stille hinten"""
    z = lambda s: np.zeros(int(s * SR), np.float32)
    out = [z(vorlauf)]
    for i, a in enumerate(teile): out += [a] + ([z(pause)] if i < len(teile) - 1 else [])
    return np.concatenate(out + [z(nachlauf)])
