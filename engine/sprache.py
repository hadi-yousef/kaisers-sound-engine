# Sprechfassung (Deutsch): Ziffern, Einheiten und Formelzeichen für die Stimme ausschreiben – „230 V“ → „zweihundertdreißig Volt“,
# „0,5 A“ → „null Komma fünf Ampere“, „U = R · I“ → „U gleich R mal I“, Jahreszahlen „1912“ → „neunzehnhundertzwölf“.
# Regeln erprobt in Lehrfilmen (Elektrotechnik, Physik, Geschichte).
import re
from ._abk import ABK

EINS = ['null', 'eins', 'zwei', 'drei', 'vier', 'fünf', 'sechs', 'sieben', 'acht', 'neun', 'zehn', 'elf', 'zwölf',
        'dreizehn', 'vierzehn', 'fünfzehn', 'sechzehn', 'siebzehn', 'achtzehn', 'neunzehn']
ZEHNER = ['', '', 'zwanzig', 'dreißig', 'vierzig', 'fünfzig', 'sechzig', 'siebzig', 'achtzig', 'neunzig']

def unter100(n):
    if n < 20: return EINS[n]
    e, z = n % 10, n // 10
    return (('ein' if e == 1 else EINS[e]) + 'und' + ZEHNER[z]) if e else ZEHNER[z]

def unter1000(n):
    h, r = n // 100, n % 100
    return ((('ein' if h == 1 else EINS[h]) + 'hundert') if h else '') + (unter100(r) if r else '')

def zahlwort(n):
    """ganze Zahl → Wort (bis Milliarden)"""
    if n == 0: return 'null'
    if n < 0: return 'minus ' + zahlwort(-n)
    teile = []
    mrd, mio, tsd, rest = n // 10**9, (n % 10**9) // 10**6, (n % 10**6) // 1000, n % 1000
    if mrd: teile.append('eine Milliarde' if mrd == 1 else zahlwort(mrd) + ' Milliarden')
    if mio: teile.append('eine Million' if mio == 1 else zahlwort(mio) + ' Millionen')
    if tsd: teile.append(('ein' if tsd == 1 else unter1000(tsd)) + 'tausend')
    if rest: teile.append(unter1000(rest))
    return ' '.join(teile).replace('tausend ', 'tausend', 1)

def jahr(n): return unter100(n // 100) + 'hundert' + (unter100(n % 100) if n % 100 else '')

# Einheiten: Kürzel → [Mehrzahl, Einzahl (bei genau 1), weiblich?]
EINHEIT = {
    'V': ['Volt'], 'kV': ['Kilovolt'], 'mV': ['Millivolt'], 'µV': ['Mikrovolt'],
    'A': ['Ampere'], 'mA': ['Milliampere'], 'µA': ['Mikroampere'], 'kA': ['Kiloampere'],
    'Ω': ['Ohm'], 'kΩ': ['Kiloohm'], 'MΩ': ['Megaohm'], 'mΩ': ['Milliohm'],
    'W': ['Watt'], 'mW': ['Milliwatt'], 'kW': ['Kilowatt'], 'MW': ['Megawatt'], 'GW': ['Gigawatt'],
    'Wh': ['Wattstunden', 'Wattstunde', 1], 'kWh': ['Kilowattstunden', 'Kilowattstunde', 1], 'MWh': ['Megawattstunden', 'Megawattstunde', 1],
    'mAh': ['Milliamperestunden', 'Milliamperestunde', 1], 'Ah': ['Amperestunden', 'Amperestunde', 1],
    'VA': ['Voltampere'], 'kVA': ['Kilovoltampere'], 'var': ['Var'], 'kvar': ['Kilovar'],
    'Hz': ['Hertz'], 'kHz': ['Kilohertz'], 'MHz': ['Megahertz'], 'GHz': ['Gigahertz'],
    'F': ['Farad'], 'mF': ['Millifarad'], 'µF': ['Mikrofarad'], 'nF': ['Nanofarad'], 'pF': ['Pikofarad'],
    'H': ['Henry'], 'mH': ['Millihenry'], 'µH': ['Mikrohenry'],
    's': ['Sekunden', 'Sekunde', 1], 'ms': ['Millisekunden', 'Millisekunde', 1], 'µs': ['Mikrosekunden', 'Mikrosekunde', 1], 'ns': ['Nanosekunden', 'Nanosekunde', 1],
    'min': ['Minuten', 'Minute', 1], 'h': ['Stunden', 'Stunde', 1],
    'mm': ['Millimeter'], 'cm': ['Zentimeter'], 'm': ['Meter'], 'km': ['Kilometer'], 'mm²': ['Quadratmillimeter'], 'm²': ['Quadratmeter'],
    '°C': ['Grad Celsius'], 'K': ['Kelvin'], 'lm': ['Lumen'], 'lx': ['Lux'], '%': ['Prozent'], '€': ['Euro'], 'ct': ['Cent'],
    'J': ['Joule'], 'kJ': ['Kilojoule'], 'mJ': ['Millijoule'], 'C': ['Coulomb'], 'T': ['Tesla'], 'mT': ['Millitesla'], 'N': ['Newton'], 'Nm': ['Newtonmeter'],
    'km/h': ['Kilometer pro Stunde'], 'U/min': ['Umdrehungen pro Minute'], 'kg': ['Kilogramm'], 'g': ['Gramm'], 'l': ['Liter'],
}
UNITS = '|'.join(re.escape(u) for u in sorted(EINHEIT, key=len, reverse=True))
NUM = r'\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?'
# \w wie in JavaScript nur ASCII – Umlaute stehen ausdrücklich in den Klassen
RE_UNIT = re.compile(r'(^|[^\wÄÖÜäöü,.])(−|-)?(' + NUM + r')\s?(' + UNITS + r')(?![\wÄÖÜäöü²])', re.ASCII)
RE_NUM = re.compile(r'(^|[^\wÄÖÜäöü,])(−|-)?(' + NUM + r')(?![\wÄÖÜäöü])', re.ASCII)
RE_PRO = re.compile(r'\b(pro|je|in|In|Einheit) (' + UNITS + r')(?![\wÄÖÜäöü²])', re.ASCII)

def zahl(s, mit_einheit=False, weiblich=False):
    ganz, _, nach = s.replace('.', '').partition(',')
    n = int(ganz)
    if _:
        nk = zahlwort(int(nach)) if len(nach) <= 2 and nach[0] != '0' else ' '.join(EINS[int(d)] for d in nach)
        return zahlwort(n) + ' Komma ' + nk
    if n == 1 and mit_einheit: return 'eine' if weiblich else 'ein'
    if not mit_einheit and 1100 <= n <= 1999: return jahr(n)                 # Jahreszahl
    w = zahlwort(n)
    if mit_einheit and w.endswith('eins'): w = w[:-1]                         # „hunderteins“ → „hundertein Volt“
    return w

def sprich(text):
    """Text → Sprechfassung (wie sprich() in der Engine)"""
    s = text
    for muster, ersatz in ABK: s = re.sub(muster, ersatz, s)
    s = re.sub(r'(\d)\s?–\s?(\d)', r'\1 bis \2', s)
    s = re.sub(r'\b([A-Z])(\d{1,2})\b', lambda m: m.group(1) + ' ' + zahlwort(int(m.group(2))), s, flags=re.ASCII)
    def einheit(m):
        vor, minus, n, u = m.groups()
        mehr, eins, weibl = (EINHEIT[u] + [None, None])[:3]
        return vor + ('minus ' if minus else '') + zahl(n, True, bool(weibl)) + ' ' + (eins if n == '1' and eins else mehr)
    s = RE_UNIT.sub(einheit, s)
    s = RE_NUM.sub(lambda m: m.group(1) + ('minus ' if m.group(2) else '') + zahl(m.group(3)), s)
    s = RE_PRO.sub(lambda m: m.group(1) + ' ' + (EINHEIT[m.group(2)][1] if len(EINHEIT[m.group(2)]) > 1 else EINHEIT[m.group(2)][0]), s)
    s = re.sub(r'\s?·\s?|\s×\s', ' mal ', s)
    s = re.sub(r'\s=\s', ' gleich ', s); s = re.sub(r'\s/\s', ' durch ', s); s = s.replace('≈', 'ungefähr')
    s = re.sub(r'\s\+\s', ' plus ', s); s = re.sub(r'\s[−-]\s(?=[A-ZÄÖÜa-z0-9])', ' minus ', s); s = s.replace('Ω', 'Ohm').replace('%', ' Prozent')
    s = s.replace('√', 'Wurzel aus ').replace('π', 'Pi').replace('φ', 'Phi').replace('²', ' Quadrat').replace('→', ', also').replace('…', ' ')
    return re.sub(r'\s{2,}', ' ', s).strip()
