"""Procedural sound design for the MEZA teaser (15 s, 48 kHz stereo).

Structure: silence -> pulse -> tension -> drop -> overload -> silence -> final impact.
Cue times mirror src/timeline.ts. Usage: python3 scripts/make_sfx.py
"""
import wave
import numpy as np

SR = 48000
DUR = 15.0
N = int(SR * DUR)
rng = np.random.default_rng(42)
L = np.zeros(N)
R = np.zeros(N)


def t_arr(d):
    return np.arange(int(d * SR)) / SR


def add(sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    L[i : i + len(sig)] += sig * gain * np.sqrt((1 - pan) / 2) * 1.414
    R[i : i + len(sig)] += sig * gain * np.sqrt((1 + pan) / 2) * 1.414


def env(d, a=0.002, decay=0.3):
    t = t_arr(d)
    e = np.exp(-t / decay)
    na = max(1, int(a * SR))
    e[:na] *= np.linspace(0, 1, na)
    return e


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):  # small buffers only
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def fft_filter(x, lo=None, hi=None):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if lo:
        m *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi:
        m *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * m, len(x))


def sub_hit(d=2.5, f0=62, f1=28, decay=0.9, click=0.6):
    t = t_arr(d)
    freq = f1 + (f0 - f1) * np.exp(-t / 0.12)
    ph = 2 * np.pi * np.cumsum(freq) / SR
    s = np.sin(ph) * env(d, 0.001, decay)
    s = np.tanh(s * 1.8)
    n = rng.standard_normal(len(t)) * env(d, 0.0005, 0.012) * click
    return s + fft_filter(n, lo=800)


def cinematic_hit(d=4.5):
    s = sub_hit(d, 70, 26, 1.6, 0.8)
    t = t_arr(d)
    boom = fft_filter(rng.standard_normal(len(t)), hi=180) * env(d, 0.002, 0.9) * 0.9
    metal = sum(np.sin(2 * np.pi * f * t) * env(d, 0.001, 0.6 + k * 0.2) for k, f in enumerate([110, 164.8, 220.5, 329.6])) * 0.12
    return s + boom + metal


def kick(d=0.45):
    return sub_hit(d, 120, 45, 0.16, 0.5)


def hat(d=0.06, g=1.0):
    return fft_filter(rng.standard_normal(int(d * SR)), lo=7000) * env(d, 0.0005, 0.015) * g


def click(f=None):
    d = 0.025
    t = t_arr(d)
    f = f or rng.uniform(2500, 6000)
    return np.sin(2 * np.pi * f * t) * env(d, 0.0003, 0.004)


def whoosh(d=0.6, rising=True, lo=200, hi=6000):
    t = t_arr(d)
    n = rng.standard_normal(len(t))
    out = np.zeros_like(n)
    seg = 1024
    for s in range(0, len(n), seg):
        p = s / len(n)
        p = p if rising else 1 - p
        c = lo * (hi / lo) ** p
        out[s : s + seg] = fft_filter(n[s : s + seg], lo=c * 0.5, hi=c * 1.5)
    shape = np.sin(np.pi * np.clip(t / d, 0, 1)) ** (1.5 if rising else 0.7)
    if rising:
        shape = (t / d) ** 2.2
    return out * shape


def reverse_impact(d=0.7):
    return sub_hit(d, 80, 40, 0.25, 0.9)[::-1] * 0.8


def glitch(d=0.18):
    t = t_arr(d)
    sq = np.sign(np.sin(2 * np.pi * rng.uniform(300, 1400) * t))
    gate = (np.sin(2 * np.pi * rng.uniform(30, 70) * t) > 0).astype(float)
    bc = np.round(rng.standard_normal(len(t)) * 3) / 3
    return (sq * 0.5 + bc * 0.3) * gate * env(d, 0.001, d / 2) * 0.5


def boot_up(d=1.1):
    t = t_arr(d)
    f = 180 * (1300 / 180) ** (np.clip(t / 0.8, 0, 1) ** 1.4)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3.01 * ph))
    e = np.minimum(t / 0.05, 1) * np.exp(-np.maximum(t - 0.6, 0) / 0.25)
    return s * e * 0.35


def heartbeat(d=0.5):
    return sub_hit(d, 55, 38, 0.13, 0.05) * 0.9


def shimmer(d=1.2):
    t = t_arr(d)
    s = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in [1760, 2217, 2637, 3520])
    return s * env(d, 0.01, 0.35) * 0.06


def drone(start, end, base=55.0):
    d = end - start
    t = t_arr(d)
    s = np.zeros_like(t)
    for k, (f, g) in enumerate([(base, 1), (base * 1.005, 0.8), (base * 1.5, 0.45), (base * 2, 0.35), (base * 3.02, 0.12)]):
        s += g * np.sin(2 * np.pi * f * t + k)
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.35 * t)
    tex = fft_filter(rng.standard_normal(len(t)), lo=300, hi=1200) * 0.08
    grow = np.clip(t / d, 0, 1) ** 1.3
    return (s * 0.12 * lfo + tex * (0.3 + grow)) * (0.25 + 0.75 * grow)


def reverb(x, secs=2.2, mix=0.25):
    ir_t = t_arr(secs)
    ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t / (secs / 5))
    ir = fft_filter(ir, hi=5000)
    ir /= np.abs(ir).sum() / 8
    n = len(x) + len(ir)
    y = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[: len(x)]
    return x * (1 - mix) + y * mix


# --- 0:00 HOOK ---------------------------------------------------------------
add(sub_hit(2.6, 70, 26, 1.1, 1.0), 0.10, 1.0)
add(glitch(0.22), 0.14, 0.7, -0.3)
add(glitch(0.12), 0.30, 0.5, 0.4)
add(whoosh(0.5, True, 300, 9000), 0.45, 0.35)
add(reverse_impact(0.5), 0.5, 0.6)

# --- 0:01 AI wakes -------------------------------------------------------------
add(boot_up(), 0.98, 0.9)
add(drone(1.0, 12.0, 55.0), 1.0, 0.9)
for i in range(4):
    b = 1.15 + i * 0.85
    add(heartbeat(), b, 0.75)
    add(heartbeat(), b + 0.2, 0.45)
for _ in range(26):
    add(click(), rng.uniform(1.1, 6.4), rng.uniform(0.08, 0.2), rng.uniform(-0.8, 0.8))
add(shimmer(), 1.95, 1.0)  # pulse on "шеф"

# --- 0:04 human -----------------------------------------------------------------
add(whoosh(0.45, True, 400, 8000), 3.6, 0.3)
add(sub_hit(1.4, 60, 34, 0.45, 0.3), 4.05, 0.45)
add(shimmer(1.6), 4.1, 0.7)

# --- riser & drop 0:07 ---------------------------------------------------------------
add(whoosh(0.9, True, 150, 12000), 6.1, 0.55)
add(reverse_impact(0.9), 6.1, 0.7)
add(cinematic_hit(3.0), 7.0, 1.0)

# --- 0:07-0:12 overload ------------------------------------------------------------
beat = 60 / 150
t = 7.0
while t < 11.95:
    add(kick(), t, 0.85)
    add(hat(g=0.9), t + beat / 2, 0.22, rng.uniform(-0.5, 0.5))
    add(hat(g=0.6), t + beat / 4 * 3, 0.12, rng.uniform(-0.5, 0.5))
    t += beat
for wt in [8.25, 9.5, 10.75]:
    add(whoosh(0.28, True, 600, 10000), wt - 0.28, 0.45, rng.uniform(-0.6, 0.6))
    add(sub_hit(1.2, 85, 36, 0.35, 0.7), wt, 0.8)
    add(glitch(0.1), wt + 0.02, 0.35, rng.uniform(-0.6, 0.6))
for _ in range(18):
    add(click(rng.uniform(1500, 7000)), rng.uniform(7.0, 11.9), 0.18, rng.uniform(-0.9, 0.9))
for _ in range(5):
    add(glitch(rng.uniform(0.05, 0.12)), rng.uniform(7.2, 11.8), 0.25, rng.uniform(-0.7, 0.7))
add(whoosh(0.5, True, 300, 14000), 11.5, 0.5)

# reverb the first act, then hard-cut it at 12.0 so no tail leaks into the silence
part_a = np.stack([reverb(L, 2.4, 0.22), reverb(R, 2.6, 0.22)])
cut = int(12.0 * SR)
fade = int(0.012 * SR)
part_a[:, cut : cut + fade] *= np.linspace(1, 0, fade)
part_a[:, cut + fade :] = 0
L[:] = 0
R[:] = 0

# --- 0:12 silence ---------------------------------------------------------------------
hiss = fft_filter(rng.standard_normal(int(1.6 * SR)), lo=3000) * 0.006
add(hiss, 12.0, 1.0)
for bt in [12.45, 12.9, 13.2]:
    add(click(5200), bt, 0.05)

# --- 0:13.5 final -------------------------------------------------------------------------
swell = np.sin(2 * np.pi * 41 * t_arr(1.2)) * np.sin(np.pi * np.clip(t_arr(1.2) / 1.2, 0, 1)) * 0.35
add(swell, 13.35, 1.0)
add(shimmer(1.4), 13.5, 1.2)
add(cinematic_hit(1.3), 13.75, 1.1)

mix = part_a + np.stack([reverb(L, 3.0, 0.3), reverb(R, 3.2, 0.3)])
# tail to black at 15 s
tail = int(0.35 * SR)
mix[:, -tail:] *= np.linspace(1, 0, tail)
mix = np.tanh(mix * 1.1)
mix /= np.max(np.abs(mix)) / 0.89

pcm = (mix.T * 32767).astype(np.int16)
with wave.open("public/sfx.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("ok")
