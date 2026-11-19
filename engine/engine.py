"""Zorvane v2 engine: Kokoro TTS + skia vector scenes + synth music/SFX -> 1080x1920 Short."""
import sys, os, math, json, random, subprocess, wave, re
import numpy as np, skia, soundfile as sf

W, H, FPS = 1080, 1920, 30
FD = '/usr/share/fonts/truetype/google-fonts/ofl/'
TF = {'anton': skia.Typeface.MakeFromFile(FD + 'anton/Anton-Regular.ttf'),
      'black': skia.Typeface.MakeFromFile(FD + 'archivoblack/ArchivoBlack-Regular.ttf')}
SR = 24000

PALS = {
 'sunset': dict(sky=[(0x1a0b3d), (0x6a1b9a), (0xff4e8a), (0xffb347)], sun=(0xffe66d, 0xff4e8a), grid=0x35e0ff, a1=0xff4ea6, a2=0x35e0ff, bld=0x120822, stars=0),
 'night':  dict(sky=[(0x050818), (0x0d1b4a), (0x2a2a8a), (0x7a3cc4)], sun=(0xe9f1ff, 0x7ab8ff), grid=0xff4ea6, a1=0x35e0ff, a2=0xffd23f, bld=0x060914, stars=1),
 'dawn':   dict(sky=[(0x14304a), (0x2a6f97), (0xf4a261), (0xffd6a5)], sun=(0xfff1c1, 0xff9f1c), grid=0xffffff, a1=0xff7a00, a2=0x00e5c7, bld=0x0f2233, stars=0),
 'toxic':  dict(sky=[(0x04140f), (0x0b4a3a), (0x16a085), (0xb8f34a)], sun=(0xf6ffb0, 0x7dff6b), grid=0xb8f34a, a1=0xffee32, a2=0xff3d81, bld=0x03120d, stars=0),
 'ember':  dict(sky=[(0x1c0505), (0x7a1010), (0xe8431a), (0xffb000)], sun=(0xfff3b0, 0xff5a1f), grid=0xffb000, a1=0xffe14d, a2=0x35e0ff, bld=0x120303, stars=0),
}

def col(c, a=255):
    return skia.Color(c >> 16 & 255, c >> 8 & 255, c & 255, int(a))

def lerp(a, b, t): return a + (b - a) * t
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def pop(x):
    x = clamp(x); return 1 + 2.4 * (x - 1) ** 3 + 1.4 * (x - 1) ** 2

def font(name, size):
    f = skia.Font(TF[name], size); f.setSubpixel(True); return f

def text_w(s, f): return f.measureText(s)

def draw_text(c, s, x, y, f, color, stroke=None, shadow=True, align='c', alpha=255, scale=1.0, rot=0, maxw=None):
    alpha = int(clamp(alpha, 0, 255))
    w = text_w(s, f)
    if maxw and w * scale > maxw: scale = maxw / w
    ox = x - w / 2 if align == 'c' else x
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(scale, scale); c.translate(-x, -y)
    if shadow:
        p = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, int(alpha * 0.55)))
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6))
        c.drawString(s, ox + 4, y + 10, f, p)
    if stroke:
        p = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, alpha), Style=skia.Paint.kStroke_Style, StrokeWidth=stroke, StrokeJoin=skia.Paint.kRound_Join)
        c.drawString(s, ox, y, f, p)
    p = skia.Paint(AntiAlias=True, Color=color if isinstance(color, int) and color > 0xffffff else col(color, alpha))
    c.drawString(s, ox, y, f, p)
    c.restore()

# ---------------------------------------------------------------- background
class Scene:
    def __init__(self, pal, seed, variant):
        self.p = PALS[pal]; self.rng = random.Random(seed); self.variant = variant
        r = self.rng
        self.stars = [(r.random() * W, r.random() * 900, r.random() * 2 + 1, r.random() * 6) for _ in range(90)]
        self.layers = []
        for li, (base, hmin, hmax, speed, shade) in enumerate([(1010, 120, 330, 6, 0.55), (1010, 180, 520, 14, 0.8), (1010, 240, 700, 26, 1.0)]):
            bl = []; x = -200
            while x < W + 1400:
                bw = r.randint(70, 170); bh = r.randint(hmin, hmax)
                wins = [(r.random() < 0.35) for _ in range(40)]
                bl.append((x, bw, bh, wins)); x += bw + r.randint(0, 24)
            self.layers.append((bl, speed, shade, base))
        self.palms = [(r.choice([-1, 1]), r.uniform(0.8, 1.3), r.uniform(0, 6)) for _ in range(3)]
        self.shapes = []
        for _ in range(14):
            self.shapes.append((r.random() * W, r.random() * H, r.uniform(20, 70), r.uniform(0, 6.28), r.uniform(0.2, 0.8)))

    def draw(self, c, t, dur):
        P = self.p
        z = 1.0 + 0.07 * (t / max(dur, 1))
        c.save(); c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-W / 2, -H / 2 + 30 * math.sin(t * 0.6))
        # sky
        stops = [0, .45, .75, 1.0]
        sh = skia.GradientShader.MakeLinear([(0, -100), (0, 1060)], [col(x) for x in P['sky']], stops)
        c.drawRect(skia.Rect(-100, -200, W + 100, 1060), skia.Paint(Shader=sh))
        if P['stars']:
            for (x, y, s, ph) in self.stars:
                a = 140 + 110 * math.sin(t * 2 + ph)
                c.drawCircle(x, y, s, skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255, int(clamp(a, 0, 255)))))
        # sun
        sy = 760 + 14 * math.sin(t * 0.8); sr = 300
        sh = skia.GradientShader.MakeLinear([(0, sy - sr), (0, sy + sr)], [col(P['sun'][0]), col(P['sun'][1])])
        glow = skia.Paint(AntiAlias=True, Color=col(P['sun'][1], 120)); glow.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 80))
        c.drawCircle(W / 2, sy, sr + 40, glow)
        c.save(); c.clipRect(skia.Rect(0, 0, W, 1010))
        c.drawCircle(W / 2, sy, sr, skia.Paint(AntiAlias=True, Shader=sh))
        # stripes
        for i in range(9):
            yy = sy + 40 + i * 32 + (t * 14) % 32
            th = 4 + i * 2.6
            c.drawRect(skia.Rect(W / 2 - sr, yy, W / 2 + sr, yy + th), skia.Paint(Color=col(P['sky'][3] if i % 2 else P['sky'][2], 255)))
        c.restore()
        # skyline layers
        for li, (bl, speed, shade, base) in enumerate(self.layers):
            off = (t * speed) % 1400
            for (x, bw, bh, wins) in bl:
                xx = x - off
                if xx < -300 or xx > W + 10: continue
                cc = col(P['bld'])
                c.drawRect(skia.Rect(xx, base - bh, xx + bw, base + 4), skia.Paint(Color=cc))
                if li >= 1:
                    k = 0
                    for wy in range(int(base - bh + 24), int(base - 20), 34):
                        for wx in range(int(xx + 12), int(xx + bw - 14), 22):
                            if wins[k % 40] and ((int(t * 0.6) + k) % 11 != 0):
                                c.drawRect(skia.Rect(wx, wy, wx + 8, wy + 14), skia.Paint(Color=col(P['a2'] if k % 3 else P['a1'], 170 if li == 2 else 100)))
                            k += 1
                    c.drawRect(skia.Rect(xx, base - bh, xx + bw, base - bh + 4), skia.Paint(Color=col(P['a1'], 110 if li == 2 else 60)))
        # ground
        gs = skia.GradientShader.MakeLinear([(0, 1010), (0, H)], [col(P['bld']), col(P['sky'][0])])
        c.drawRect(skia.Rect(-100, 1010, W + 100, H + 100), skia.Paint(Shader=gs))
        gp = skia.Paint(AntiAlias=True, Color=col(P['grid'], 190), StrokeWidth=3, Style=skia.Paint.kStroke_Style)
        hz = 1010; cx = W / 2
        for i in range(-14, 15):
            c.drawLine(cx + i * 40, hz, cx + i * 360, H + 60, gp)
        sp = (t * 0.55) % 1
        for j in range(14):
            u = (j + sp) / 14; y = hz + (u ** 2.2) * (H - hz + 60)
            gp.setAlphaf(0.2 + 0.7 * u)
            c.drawLine(-100, y, W + 100, y, gp)
        # palms
        for i, (side, sc, ph) in enumerate(self.palms[:2]):
            self.palm(c, 70 if i == 0 else W - 70, 1010, -1 if i == 0 else 1, 1.15 + 0.1 * i, t, P, ph)
        # floating shapes (bokeh)
        for (x, y, s, ph, sp2) in self.shapes:
            yy = (y - t * 22 * sp2) % (H + 100) - 50
            a = 40 + 25 * math.sin(t + ph)
            c.drawCircle((x + 18 * math.sin(t * 0.5 + ph)) % W, yy, s, skia.Paint(AntiAlias=True, Color=col(P['a1'] if ph > 3 else P['a2'], a)))
        c.restore()

    def palm(self, c, x, base, dirn, sc, t, P, ph):
        c.save(); c.translate(x, base); c.scale(dirn * sc, sc)
        path = skia.Path(); path.moveTo(-14, 0); path.quadTo(30, -300, 70, -640); path.lineTo(88, -640); path.quadTo(44, -300, 16, 0); path.close()
        c.drawPath(path, skia.Paint(AntiAlias=True, Color=col(P['bld'])))
        c.translate(80, -640)
        for k in range(7):
            ang = -170 + k * 30 + 5 * math.sin(t * 1.3 + ph + k)
            c.save(); c.rotate(ang)
            fr = skia.Path(); fr.moveTo(0, 0); fr.quadTo(120, -60, 300, 30); fr.quadTo(130, -18, 0, 10); fr.close()
            c.drawPath(fr, skia.Paint(AntiAlias=True, Color=col(P['bld'])))
            c.restore()
        c.restore()

# ---------------------------------------------------------------- overlays
def chip(c, t, P, topic):
    f = font('anton', 54); w = text_w(topic, f) + 80
    x = 60; y = 128
    p = skia.Paint(AntiAlias=True, Color=col(P['a1']))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x, y - 66, x + w, y + 22), 22, 22), p)
    draw_text(c, topic, x + w / 2, y, f, 0xffffff, shadow=False)
    # channel handle
    draw_text(c, 'ZORVANE DAILY', W - 60 - text_w('ZORVANE DAILY', font('black', 34)) / 2, y - 6, font('black', 34), 0xffffff, stroke=4)

def widget_bignum(c, p, P, d, t):
    v = d['value']; lab = d['label']; sub = d.get('sub', '')
    k = ease_out(p * 1.6)
    shown = int(round(v * k)) if isinstance(v, (int, float)) else v
    f = font('anton', 520); s = str(shown)
    sc = pop(p * 4)
    gl = skia.Paint(AntiAlias=True, Color=col(P['a1'], 110)); gl.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 60))
    c.drawCircle(W / 2, 640, 300, gl)
    draw_text(c, s, W / 2, 760, f, 0xffffff, stroke=14, scale=sc, maxw=W - 150)
    draw_text(c, lab, W / 2, 850, font('anton', 100), P['a2'], stroke=8, alpha=255 * ease_out(p * 3))
    if sub: draw_text(c, sub, W / 2, 930, font('black', 44), 0xffffff, stroke=6, alpha=255 * ease_out(p * 3 - 0.5))

def widget_bars(c, p, P, d, t):
    items = d['items']; mx = d.get('max', 100); lo = d.get('lo', 0)
    y0 = 330; gap = 125
    for i, (lab, val, hl) in enumerate(items):
        pp = ease_out(p * 2.2 - i * 0.18)
        y = y0 + i * gap
        draw_text(c, lab, 70, y, font('anton', 62), P['a2'] if hl else 0xffffff, stroke=7, align='l', alpha=255 * clamp(pp * 3))
        frac = (val - lo) / (mx - lo)
        bw = (W - 260) * frac * pp
        r = skia.RRect.MakeRectXY(skia.Rect(70, y + 18, 70 + max(bw, 1), y + 70), 18, 18)
        sh = skia.GradientShader.MakeLinear([(70, 0), (W, 0)], [col(P['a1'] if hl else 0x8a8fa8), col(P['a2'] if hl else 0xcfd3e6)])
        c.drawRRect(r, skia.Paint(AntiAlias=True, Shader=sh))
        draw_text(c, str(val), 70 + bw - 18 if bw > 150 else 70 + bw + 80, y + 62, font('anton', 52), 0x10101a if bw > 150 else 0xffffff, shadow=False, align='c', alpha=255 * clamp(pp * 3))

def widget_stats(c, p, P, d, t):
    items = d['items']  # (big, small)
    for i, (big, small) in enumerate(items):
        pp = pop(p * 2.4 - i * 0.5)
        y = 520 + i * 360
        c.save(); c.translate(W / 2, y); c.scale(max(pp, 0.01), max(pp, 0.01)); c.translate(-W / 2, -y)
        rr = skia.RRect.MakeRectXY(skia.Rect(80, y - 250, W - 80, y + 70), 40, 40)
        c.drawRRect(rr, skia.Paint(AntiAlias=True, Color=skia.Color(10, 8, 30, 205)))
        c.drawRRect(rr, skia.Paint(AntiAlias=True, Color=col(P['a1'] if i % 2 == 0 else P['a2']), Style=skia.Paint.kStroke_Style, StrokeWidth=7))
        draw_text(c, str(big), W / 2, y - 60, font('anton', 210), 0xffffff, stroke=10, maxw=W - 240)
        draw_text(c, small, W / 2, y + 30, font('black', 46), P['a1'] if i % 2 == 0 else P['a2'], stroke=5, maxw=W - 240)
        c.restore()

def widget_list(c, p, P, d, t):
    items = d['items']
    for i, it in enumerate(items):
        pp = ease_out(p * 2.2 - i * 0.45)
        y = 520 + i * 220
        xoff = (1 - pp) * 900
        rr = skia.RRect.MakeRectXY(skia.Rect(70 + xoff, y - 130, W - 70 + xoff, y + 40), 36, 36)
        c.drawRRect(rr, skia.Paint(AntiAlias=True, Color=skia.Color(10, 8, 30, 215)))
        c.drawRRect(rr, skia.Paint(AntiAlias=True, Color=col(P['a1'] if i % 2 == 0 else P['a2']), Style=skia.Paint.kStroke_Style, StrokeWidth=6))
        draw_text(c, it, W / 2 + xoff, y - 10, font('anton', 100), 0xffffff, stroke=8, maxw=W - 200)

def widget_cta(c, p, P, d, t):
    pp = pop(p * 3)
    pulse = 1 + 0.04 * math.sin(t * 6)
    draw_text(c, d.get('big', 'YOUR TAKE?'), W / 2, 700, font('anton', 220), 0xffffff, stroke=12, scale=pp * pulse, maxw=W - 140)
    draw_text(c, d.get('small', 'COMMENT BELOW'), W / 2, 820, font('black', 66), P['a2'], stroke=8, scale=pp)
    # arrow down
    ay = 1000 + 20 * math.sin(t * 5)
    path = skia.Path(); path.moveTo(W / 2 - 70, ay); path.lineTo(W / 2 + 70, ay); path.lineTo(W / 2, ay + 100); path.close()
    c.drawPath(path, skia.Paint(AntiAlias=True, Color=col(P['a1'])))

_IMG_CACHE = {}
def widget_photo(c, p, P, d, t):
    """Licensed photo card: d={'file':path,'credit':'Photo: Author / Wikimedia Commons / CC BY-SA 4.0'}"""
    f = d['file']
    if f not in _IMG_CACHE:
        _IMG_CACHE[f] = skia.Image.open(f)
    im = _IMG_CACHE[f]
    cw, ch = 940, 720; cx, cy = W / 2, 640
    k = 1.0 + 0.10 * p
    sc = max(cw / im.width(), ch / im.height()) * k
    pp = pop(p * 4)
    c.save(); c.translate(cx, cy); c.scale(pp, pp)
    rr = skia.RRect.MakeRectXY(skia.Rect(-cw / 2, -ch / 2, cw / 2, ch / 2), 36, 36)
    c.drawRRect(rr.makeOffset(0, 14), skia.Paint(AntiAlias=True, Color=col(0x000000, 140)))
    c.clipRRect(rr, doAntiAlias=True)
    c.save(); c.scale(sc, sc); c.drawImage(im, -im.width() / 2, -im.height() / 2, skia.SamplingOptions(skia.FilterMode.kLinear)); c.restore()
    c.restore()
    c.save(); c.translate(cx, cy); c.scale(pp, pp)
    st = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=8, Color=col(P['a1']))
    c.drawRRect(rr, st); c.restore()
    draw_text(c, d.get('credit', ''), W / 2, cy + ch / 2 + 60, font('black', 34), 0xffffff, stroke=5, maxw=W - 120)

WIDGETS = dict(bignum=widget_bignum, bars=widget_bars, stats=widget_stats, list=widget_list, cta=widget_cta, photo=widget_photo)

def captions(c, t, P, words):
    # words: list of (start, end, text, group_id)
    cur = None
    for i, (a, b, w, g) in enumerate(words):
        if a <= t < b + 0.0: cur = i
    if cur is None:
        past = [i for i, (a, b, w, g) in enumerate(words) if b <= t]
        if not past: return
        cur = past[-1]
        if t - words[cur][1] > 0.6: return
    g = words[cur][3]
    grp = [(i, w) for i, (a, b, w, gg) in enumerate(words) if gg == g]
    # layout in lines
    f = font('anton', 112)
    lines = []; line = []; lw = 0
    for i, w in grp:
        ww = text_w(w + ' ', f)
        if lw + ww > W - 140 and line: lines.append(line); line = []; lw = 0
        line.append((i, w)); lw += ww
    lines.append(line)
    gstart = words[grp[0][0]][0]
    ent = ease_out((t - gstart) / 0.14)
    y = 1300 - (len(lines) - 1) * 60
    for ln in lines:
        tw = sum(text_w(w + ' ', f) for _, w in ln) - text_w(' ', f)
        x = (W - tw) / 2
        for i, w in ln:
            a, b, _, _ = words[i]
            active = (i == cur)
            k = pop((t - a) / 0.16) if active else 1.0
            colr = P['a2'] if active else 0xffffff
            if i > cur: colr = 0xd9d9e6
            ww = text_w(w, f)
            draw_text(c, w, x + ww / 2, y + (1 - ent) * 40, f, colr, stroke=16, scale=(1.0 + 0.0) * (k if active else 1), alpha=255 * (ent if t >= gstart else 1))
            x += text_w(w + ' ', f)
        y += 132

def footer(c, t, P, source, T):
    if T - t < 6.5 or True:
        a = 255 * clamp(ease_out(t / 0.6))
        draw_text(c, source, W / 2, 1700, font('black', 30), 0xffffff, stroke=5, alpha=a * 0.95)
        draw_text(c, 'Fan page. Not affiliated with Rockstar Games or Take-Two. AI narration.', W / 2, 1745, font('black', 24), 0xdddddd, stroke=4, alpha=a * 0.8)

def progress(c, t, T, P):
    c.drawRect(skia.Rect(0, 0, W * (t / T), 10), skia.Paint(Color=col(P['a1'])))

def vignette(c):
    sh = skia.GradientShader.MakeRadial((W / 2, H / 2), 1250, [skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, 150)], [0, 0.55, 1])
    c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=sh))

def flash(c, t, starts):
    for s in starts:
        x = (t - s) / 0.25
        if 0 <= x < 1:
            c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Color=skia.Color(255, 255, 255, int(70 * (1 - x)))))

# ---------------------------------------------------------------- audio
def synth_voice(beats, outdir, voice='af_heart', speed=1.08):
    from kokoro_onnx import Kokoro
    k = Kokoro('/home/claude/kokoro/kokoro-v1.0.int8.onnx', '/home/claude/kokoro/voices-v1.0.bin')
    sig = []; t = 0.0; timings = []
    lead = 0.15
    out = np.zeros(int(lead * SR), dtype=np.float32); t = lead
    for bi, b in enumerate(beats):
        say = b.get('say', b['text'])
        s, sr = k.create(say, voice=voice, speed=b.get('speed', speed), lang='en-us')
        s = s.astype(np.float32)
        # trim silence
        env = np.abs(s); idx = np.where(env > 0.01)[0]
        if len(idx): s = s[max(0, idx[0] - 200): idx[-1] + 600]
        dur = len(s) / SR
        words = b['text'].split()
        tot = sum(len(w) + 1.5 for w in words); a = t
        for w in words:
            d = dur * (len(w) + 1.5) / tot
            timings.append((a, a + d, w, bi)); a += d
        beats[bi]['_t0'] = t; beats[bi]['_t1'] = t + dur
        out = np.concatenate([out, s, np.zeros(int(b.get('gap', 0.18) * SR), dtype=np.float32)])
        t += dur + b.get('gap', 0.18)
    out = np.concatenate([out, np.zeros(int(0.9 * SR), dtype=np.float32)])
    return out, timings, len(out) / SR

def lp(x, a):
    y = np.zeros_like(x); s = 0.0
    for i in range(len(x)):
        s += a * (x[i] - s); y[i] = s
    return y

def make_music(dur, bpm=104, key=57, seed=1, mood='minor'):
    rng = np.random.RandomState(seed)
    n = int(dur * SR); t = np.arange(n) / SR
    beat = 60 / bpm
    prog = [0, -4, -7, -2] if mood == 'minor' else [0, 5, 7, 3]
    def f(m): return 440 * 2 ** ((m - 69) / 12)
    out = np.zeros(n, dtype=np.float32)
    bars = int(dur / (beat * 4)) + 2
    for bar in range(bars):
        root = key + prog[bar % 4]
        t0 = bar * beat * 4
        # bass: 8th notes
        for e in range(8):
            ts = t0 + e * beat / 2; i0 = int(ts * SR)
            if i0 >= n: break
            L = int(beat / 2 * SR * 0.9); L = min(L, n - i0)
            tt = np.arange(L) / SR
            fr = f(root - 12)
            saw = 2 * ((tt * fr) % 1) - 1
            env = np.exp(-tt * 6) * 0.9 + 0.1
            v = (saw * 0.6 + np.sign(np.sin(2 * np.pi * fr * tt)) * 0.2) * env
            out[i0:i0 + L] += (v * 0.30).astype(np.float32)
        # arp
        notes = [0, 7, 12, 15, 12, 7, 3, 7] if mood == 'minor' else [0, 4, 7, 12, 7, 4, 0, 4]
        for e in range(16):
            ts = t0 + e * beat / 4; i0 = int(ts * SR)
            if i0 >= n: break
            L = min(int(beat / 4 * SR * 1.6), n - i0); tt = np.arange(L) / SR
            fr = f(root + 12 + notes[e % 8] + (12 if e % 5 == 4 else 0))
            v = np.sin(2 * np.pi * fr * tt) + 0.4 * np.sin(4 * np.pi * fr * tt) + 0.2 * np.sin(6 * np.pi * fr * tt)
            out[i0:i0 + L] += (v * np.exp(-tt * 10) * 0.10).astype(np.float32)
        # pad
        i0 = int(t0 * SR); L = min(int(beat * 4 * SR), n - i0)
        if L > 0:
            tt = np.arange(L) / SR; v = np.zeros(L)
            for iv in (0, 3, 7, 10):
                fr = f(root + iv)
                v += np.sin(2 * np.pi * fr * tt) + np.sin(2 * np.pi * fr * 1.004 * tt)
            ev = np.minimum(1, tt / 0.6) * np.minimum(1, (L / SR - tt) / 0.4)
            out[i0:i0 + L] += (v * ev * 0.035).astype(np.float32)
        # drums
        for e in range(4):
            ts = t0 + e * beat; i0 = int(ts * SR)
            if i0 >= n: break
            L = min(int(0.28 * SR), n - i0); tt = np.arange(L) / SR
            if e % 2 == 0:
                fr = 110 * np.exp(-tt * 22) + 42
                v = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-tt * 9)
                out[i0:i0 + L] += (v * 0.6).astype(np.float32)
            else:
                nz = rng.randn(L) * np.exp(-tt * 16); out[i0:i0 + L] += (nz * 0.14).astype(np.float32)
        for e in range(8):
            ts = t0 + e * beat / 2 + beat / 4; i0 = int(ts * SR)
            if i0 >= n: break
            L = min(int(0.05 * SR), n - i0); tt = np.arange(L) / SR
            nz = rng.randn(L); nz = nz - lp(nz, 0.3)
            out[i0:i0 + L] += (nz * np.exp(-tt * 70) * 0.05).astype(np.float32)
    fade = np.minimum(1, t / 0.5) * np.minimum(1, (dur - t) / 1.0)
    return (out * fade).astype(np.float32)

def sfx_whoosh(L=0.45, up=True, seed=0):
    rng = np.random.RandomState(seed); n = int(L * SR); tt = np.arange(n) / SR
    nz = rng.randn(n)
    a = lp(nz, 0.02 + 0.3 * (tt / L) ** 2 if False else 0.12)
    env = np.sin(np.pi * tt / L) ** 2
    y = (nz - lp(nz, 0.02)) * 0.0 + lp(nz, 0.25) * env
    return (y * 0.55).astype(np.float32)

def sfx_hit():
    n = int(0.6 * SR); tt = np.arange(n) / SR
    fr = 160 * np.exp(-tt * 9) + 38
    v = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-tt * 5)
    nz = np.random.RandomState(3).randn(n) * np.exp(-tt * 30) * 0.2
    return ((v + nz) * 0.9).astype(np.float32)

def sfx_tick():
    n = int(0.08 * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1800 * tt) * np.exp(-tt * 60) * 0.25).astype(np.float32)

def mix(voice, music, sfx_events, dur):
    n = int(dur * SR)
    v = np.zeros(n, dtype=np.float32); v[:min(n, len(voice))] = voice[:n]
    # sidechain duck
    env = np.abs(v); env = lp(env, 0.0015); env = env / (env.max() + 1e-9)
    duck = 1 - 0.55 * np.clip(env * 3, 0, 1)
    m = music[:n] * duck * 0.9
    s = np.zeros(n, dtype=np.float32)
    for (ts, kind) in sfx_events:
        w = {'whoosh': sfx_whoosh(0.5), 'hit': sfx_hit(), 'tick': sfx_tick()}[kind]
        i0 = int(ts * SR)
        if i0 < n: s[i0:i0 + len(w)] += w[:n - i0] * (0.5 if kind != 'hit' else 0.55)
    return (v * 1.0 + m * 0.55 + s * 0.8)

# ---------------------------------------------------------------- build
def build(spec, outpath, workdir, test_secs=None):
    os.makedirs(workdir, exist_ok=True)
    beats = spec['beats']; P = PALS[spec['pal']]
    voice, words, vdur = synth_voice(beats, workdir, voice=spec.get('voice', 'af_heart'), speed=spec.get('speed', 1.08))
    T = vdur + 0.1
    music = make_music(T + 1, bpm=spec.get('bpm', 104), key=spec.get('key', 57), seed=spec.get('seed', 1), mood=spec.get('mood', 'minor'))
    sfx = []
    for i, b in enumerate(beats):
        sfx.append((max(0, b['_t0'] - 0.12), 'whoosh'))
        if b.get('hit'): sfx.append((b['_t0'] + b.get('hit_at', 0.25), 'hit'))
    audio = mix(voice, music, sfx, T)
    pk = np.abs(audio).max(); audio = audio / pk * 0.89
    wav = os.path.join(workdir, 'audio.wav'); sf.write(wav, audio, SR)
    json.dump(dict(words=words, T=T, beats=[{k: v for k, v in b.items() if k in ('_t0', '_t1')} for b in beats]), open(os.path.join(workdir, 'timing.json'), 'w'))
    json.dump(spec, open(os.path.join(workdir, 'spec.json'), 'w'))
    nf = int(T * FPS) if not test_secs else int(test_secs * FPS)
    mid = nf // 2
    procs = []
    for k, (a, b) in enumerate([(0, mid), (mid, nf)]):
        procs.append(subprocess.Popen([sys.executable, __file__, '--render', workdir, str(a), str(b), os.path.join(workdir, f'part{k}.mp4')]))
    for p in procs: assert p.wait() == 0
    open(os.path.join(workdir, 'list.txt'), 'w').write(f"file '{workdir}/part0.mp4'\nfile '{workdir}/part1.mp4'\n")
    subprocess.check_call(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', os.path.join(workdir, 'list.txt'), '-c', 'copy', os.path.join(workdir, 'video.mp4')])
    subprocess.check_call(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(workdir, 'video.mp4'), '-i', wav,
                           '-af', 'loudnorm=I=-14:TP=-1.5:LRA=9', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-shortest', '-movflags', '+faststart', outpath])
    return T

def render_range(workdir, a, b, outp):
    spec = json.load(open(os.path.join(workdir, 'spec.json'))); tm = json.load(open(os.path.join(workdir, 'timing.json')))
    P = PALS[spec['pal']]; T = tm['T']; words = [tuple(x) for x in tm['words']]
    scene = Scene(spec['pal'], spec.get('seed', 1), 0)
    beats = spec['beats']
    for i, bt in enumerate(tm['beats']): beats[i].update(bt)
    surf = skia.Surface(W, H); c = surf.getCanvas()
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-g', '30', '-movflags', '+faststart', outp], stdin=subprocess.PIPE)
    starts = [bt['_t0'] for bt in beats]
    rng = np.random.RandomState(5)
    for fi in range(a, b):
        t = fi / FPS
        scene.draw(c, t, T)
        # current beat widget
        bi = max([i for i, s in enumerate(starts) if s - 0.05 <= t] or [0])
        bt = beats[bi]
        if bt.get('widget'):
            name, d = bt['widget']
            nxt = starts[bi + 1] if bi + 1 < len(starts) else T
            p = clamp((t - bt['_t0'] + 0.1) / max(nxt - bt['_t0'], 0.5))
            c.save()
            a_in = ease_out((t - bt['_t0'] + 0.1) / 0.25); a_out = 1 - ease_out((t - (nxt - 0.12)) / 0.2) if bi + 1 < len(starts) else 1
            c.saveLayerAlpha(None, int(255 * clamp(a_in * a_out)))
            WIDGETS[name](c, p, P, d, t)
            c.restore(); c.restore()
        captions(c, t, P, words)
        chip(c, t, P, spec['topic'])
        footer(c, t, P, spec['source'], T)
        flash(c, t, starts)
        vignette(c)
        progress(c, t, T, P)
        # film grain (cheap): random sparse dots
        img = surf.makeImageSnapshot()
        arr = np.frombuffer(img.tobytes(), dtype=np.uint8) if hasattr(img, 'tobytes') else None
        ff.stdin.write(arr.tobytes())
    ff.stdin.close(); ff.wait()

if __name__ == '__main__':
    if sys.argv[1] == '--render':
        render_range(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
    else:
        spec = json.load(open(sys.argv[1])); out = sys.argv[2]
        T = build(spec, out, '/tmp/zv_' + os.path.basename(out).split('.')[0], test_secs=float(sys.argv[3]) if len(sys.argv) > 3 else None)
        print('done', T)
