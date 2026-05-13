import math
import random

try:
    import numpy as np
    _HAS_NP = True
except ImportError:
    _HAS_NP = False

try:
    import pygame
    _HAS_PG = True
except ImportError:
    _HAS_PG = False

#  Runtime state 
_SR           = 44100
_READY        = False
_music_vol    = 0.40
_sfx_vol      = 0.55
_sfx_cache    = {}          # name  → pygame.Sound
_music_cache  = {}          # state → pygame.Sound  (pre-generated loops)
_music_ch     = None        # dedicated pygame.Channel for background music
_current_state = 'none'     # last state passed to music_set_state()

#  Waveform helpers 

def _t(n):
    return np.linspace(0, n / _SR, n, endpoint=False)

def _sine(freq, n):
    return np.sin(2 * math.pi * freq * _t(n))

def _square(freq, n):
    return np.sign(np.sin(2 * math.pi * freq * _t(n)) + 1e-9)

def _noise(n):
    return np.random.uniform(-1, 1, n)

def _env_adsr(n, a=0.01, d=0.05, s=0.7, r=0.2):
    env = np.zeros(n)
    na, nd, nr = int(n*a), int(n*d), int(n*r)
    ns = max(0, n - na - nd - nr)
    if na: env[:na]            = np.linspace(0, 1, na)
    if nd: env[na:na+nd]       = np.linspace(1, s, nd)
    if ns: env[na+nd:na+nd+ns] = s
    if nr: env[na+nd+ns:]      = np.linspace(s, 0, nr)
    return env

def _to_sound(sig, vol=1.0):
    """Convert float32 [-1,1] mono array → stereo pygame.Sound."""
    if not (_HAS_NP and _HAS_PG):
        return None
    try:
        sig  = np.clip(sig * vol, -1, 1)
        s16  = (sig * 32767).astype(np.int16)
        st   = np.ascontiguousarray(np.column_stack([s16, s16]))
        snd  = pygame.sndarray.make_sound(st)
        return snd
    except Exception:
        return None

# Music generators (each returns a ~8s loopable float32 array) 

_NOTES = {
    'Am':  [220.00, 261.63, 329.63, 440.00, 523.25],
    'dim': [233.08, 277.18, 329.63, 415.30],
    'maj': [261.63, 329.63, 392.00, 523.25, 659.25],
}

def _music_menu():
    """Dark ambient arpeggio, slow A-minor. ~8 s."""
    n   = int(_SR * 8.0)
    sig = np.zeros(n)
    # Sustain pad
    for f, v in [(110, 0.10), (165, 0.07), (220, 0.06)]:
        sig += _sine(f, n) * v
    # Slow tremolo on pad
    sig *= (0.75 + 0.25 * np.sin(2*math.pi*0.4 * _t(n)))
    # Arp notes
    beat = int(_SR * 0.75)
    notes = _NOTES['Am']
    for step, f in enumerate(notes * 4):
        onset = step * beat
        if onset >= n: break
        dur   = min(int(_SR * 0.55), n - onset)
        s     = _sine(f, dur) * 0.22 + _sine(f*2, dur) * 0.08
        env   = _env_adsr(dur, a=0.04, d=0.12, s=0.35, r=0.40)
        sig[onset:onset+dur] += s * env
    # Subtle reverb echoes
    for delay in [3300, 6600, 13200]:
        if delay < n:
            tail = np.zeros(n)
            tail[delay:] = sig[:-delay] * 0.20
            sig += tail
    return np.clip(sig, -1, 1)


def _music_play():
    """Tense drone + sparse high notes. ~8 s."""
    n   = int(_SR * 8.0)
    sig = np.zeros(n)
    # Drone
    for f, v in [(55, 0.16), (82.4, 0.10), (110, 0.07)]:
        sig += _sine(f, n) * v
    sig *= (0.7 + 0.3 * np.sin(2*math.pi*3.0 * _t(n)))
    # Sparse arp
    beat = int(_SR * 0.75)
    notes = _NOTES['Am']
    for step in range(0, n // beat, 2):        # every 2 beats
        onset = step * beat + random.randint(0, beat // 4)
        if onset >= n: break
        f   = random.choice(notes)
        dur = min(int(_SR * 0.18), n - onset)
        s   = _sine(f, dur) * _env_adsr(dur, a=0.01, d=0.05, s=0.30, r=0.55)
        sig[onset:onset+dur] += s * 0.24
    return np.clip(sig, -1, 1)


def _music_alert():
    """Fast dissonant rhythm. ~4 s (will loop every 4 s)."""
    n    = int(_SR * 4.0)
    sig  = np.zeros(n)
    beat = int(_SR * 60 / 140)
    notes = _NOTES['dim']
    for step in range(n // (beat // 2)):
        onset = step * (beat // 2)
        if onset >= n: break
        f   = notes[step % len(notes)]
        dur = min(int(_SR * 0.08), n - onset)
        s   = _square(f, dur) * _env_adsr(dur, a=0.005, d=0.03, s=0.35, r=0.45)
        sig[onset:onset+dur] += s * 0.22
    # Tension sweep
    ph = 2*math.pi*300/_SR * np.arange(n) * np.linspace(1.0, 1.06, n)
    sig += np.sin(ph) * 0.10 * (0.6 + 0.4*np.sin(2*math.pi*7 * _t(n)))
    return np.clip(sig, -1, 1)


def _music_win():
    """Bright ascending chord stab, loops as celebration. ~4 s."""
    n   = int(_SR * 4.0)
    sig = np.zeros(n)
    for i, f in enumerate(_NOTES['maj']):
        onset = int(i * _SR * 0.07)
        dur   = min(int(_SR * 1.5), n - onset)
        if dur <= 0: break
        s   = _sine(f, dur)*0.35 + _sine(f*2, dur)*0.12
        sig[onset:onset+dur] += s * _env_adsr(dur, a=0.01, d=0.15, s=0.55, r=0.25)
    return np.clip(sig, -1, 1)


def _music_lose():
    """Low rumble + descending drone. ~4 s."""
    n   = int(_SR * 4.0)
    sig = _noise(n) * 0.20 * np.exp(-np.linspace(0, 2, n))
    for f in [55, 41.2, 36.7]:
        sig += _sine(f, n) * 0.15 * np.linspace(1, 0.1, n)
    return np.clip(sig, -1, 1)


#  SFX synthesis 

def _build_sfx():
    if not (_HAS_NP and _HAS_PG):
        return {}
    c = {}

    def mk(gen, vol): return _to_sound(gen, vol)

    # SONAR PING
    def _sonar():
        n  = int(_SR * 0.14)
        ph = 2*math.pi*440/_SR * np.cumsum(np.linspace(1.0, 1.4, n))
        return np.sin(ph) * np.exp(-np.linspace(0, 6, n))
    c['sonar'] = mk(_sonar(), 0.28)

    # MIRROR REFLECTION
    def _mirror():
        n  = int(_SR * 0.09)
        ph = 2*math.pi*1200/_SR * np.arange(n)
        return np.sin(ph) * np.exp(-np.linspace(0, 10, n))
    c['mirror'] = mk(_mirror(), 0.20)

    # TRAP TRIGGER
    def _trap():
        n = int(_SR * 0.22)
        return _square(55, n)*np.exp(-np.linspace(0,4,n)) + \
               _noise(n)*np.exp(-np.linspace(0,12,n))*0.3
    c['trap'] = mk(_trap(), 0.32)

    # LOSE
    def _lose():
        n = int(_SR * 0.5)
        seg = n // 4
        sig = np.zeros(n)
        for i, f in enumerate([440, 370, 311, 262]):
            s = _sine(f, seg) * np.linspace(1,0,seg)**1.5
            sig[i*seg:(i+1)*seg] = s
        return sig
    c['lose'] = mk(_lose(), 0.35)

    # WIN
    def _win():
        n = int(_SR * 0.55)
        seg = n // 4
        sig = np.zeros(n)
        for i, f in enumerate([523, 659, 784, 1047]):
            s = (_sine(f, seg)*0.6 + _sine(f*2, seg)*0.2) * \
                _env_adsr(seg, a=0.02, d=0.1, s=0.5, r=0.35)
            sig[i*seg:(i+1)*seg] = s
        return sig
    c['win'] = mk(_win(), 0.32)

    # ALERT SFX (one-shot)
    def _alert():
        n  = int(_SR * 0.18)
        ph = 2*math.pi*180/_SR * np.arange(n) * np.linspace(1,3,n)
        return np.sign(np.sin(ph)) * np.linspace(1, 0, n)
    c['alert'] = mk(_alert(), 0.28)

    # STEP
    c['step'] = mk(
        _noise(int(_SR*0.04))*np.exp(-np.linspace(0,15,int(_SR*0.04)))*0.5 +
        _sine(80, int(_SR*0.04))*np.exp(-np.linspace(0,20,int(_SR*0.04)))*0.3,
        0.12)

    # DECOY
    def _decoy():
        n  = int(_SR * 0.12)
        ph = 2*math.pi*300/_SR * np.arange(n)
        return np.sin(ph) * np.exp(-np.linspace(0, 8, n))
    c['decoy'] = mk(_decoy(), 0.22)

    # START WHOOSH
    def _start():
        n   = int(_SR * 0.4)
        sig = _noise(n) * 0.3
        for _ in range(3):
            sig = np.convolve(sig, np.ones(8)/8, mode='same')
        env = np.concatenate([np.linspace(0,1,n//3), np.linspace(1,0,n-n//3)])
        sig = (sig + _sine(120,n)*0.4) * env
        return sig
    c['start'] = mk(_start(), 0.25)

    # BLACKOUT
    def _blackout():
        n = int(_SR * 0.35)
        return _noise(n)*np.exp(-np.linspace(0,3,n)) + \
               _sine(40,n)*0.5*np.exp(-np.linspace(0,5,n))
    c['blackout'] = mk(_blackout(), 0.40)

    # CLICK
    def _click():
        n  = int(_SR * 0.05)
        return _sine(600,n)*np.exp(-np.linspace(0,20,n))
    c['click'] = mk(_click(), 0.18)

    # SNEAK
    c['sneak'] = mk(
        _noise(int(_SR*0.06))*np.exp(-np.linspace(0,8,int(_SR*0.06)))*0.4,
        0.10)

    return c


#  Public API 

def audio_init():
    """
    Initialize pygame mixer, pre-generate ALL SFX and music loops.
    Call once after pygame.init(). Safe to call even if numpy is missing.
    """
    global _READY, _sfx_cache, _music_cache, _music_ch
    if not (_HAS_NP and _HAS_PG):
        return
    try:
        pygame.mixer.pre_init(frequency=_SR, size=-16, channels=2, buffer=2048)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)
    except Exception:
        return

    try:
        _sfx_cache   = _build_sfx()
    except Exception:
        _sfx_cache = {}

    # Pre-generate looping music buffers
    generators = {
        'menu':  _music_menu,
        'play':  _music_play,
        'alert': _music_alert,
        'win':   _music_win,
        'lose':  _music_lose,
    }
    for state, gen in generators.items():
        try:
            raw = gen()
            snd = _to_sound(raw, _music_vol)
            if snd:
                _music_cache[state] = snd
        except Exception:
            pass

    try:
        _music_ch = pygame.mixer.Channel(15)
    except Exception:
        pass

    _READY = True


def play_sfx(name):
    """Play a one-shot sound effect. Safe to call even if audio not ready."""
    if not _READY:
        return
    snd = _sfx_cache.get(name)
    if snd is None:
        return
    try:
        snd.set_volume(_sfx_vol)
        snd.play()
    except Exception:
        pass


def music_set_state(state):
    global _current_state
    if not _READY or state == _current_state:
        return
    _current_state = state
    if _music_ch is None:
        return
    try:
        if state == 'none':
            _music_ch.stop()
            return
        snd = _music_cache.get(state)
        if snd is not None:
            snd.set_volume(_music_vol)
            _music_ch.play(snd, loops=-1)   # ← infinite loop, no threads needed
    except Exception:
        pass


def music_tick():
    """No-op kept for API compatibility. Music loops automatically."""
    pass


def music_set_volume(v):
    """Set music master volume (0.0–1.0)."""
    global _music_vol
    _music_vol = max(0.0, min(1.0, v))
    if not _READY or _music_ch is None:
        return
    try:
        _music_ch.set_volume(_music_vol)
        # Also update cached sounds' volume so it's correct on next play()
        for snd in _music_cache.values():
            snd.set_volume(_music_vol)
    except Exception:
        pass


def sfx_set_volume(v):
    """Set SFX master volume (0.0–1.0)."""
    global _sfx_vol
    _sfx_vol = max(0.0, min(1.0, v))
