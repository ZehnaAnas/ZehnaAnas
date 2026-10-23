"""
The "playground": a tmux session with five panes, rendered as one animated SVG.

    0: ik_arm.py   two-link robot arm stacking blocks, motion from real inverse kinematics
    1: htop        parody process list
    2: synth.glsl  synthwave perspective grid flyover
    3: lorenz.py   Lorenz attractor drawing itself (RK4-integrated)
    4: pong        two scripted agents, one of which is a bit chaotic

Everything is precomputed here in Python and baked into SMIL/CSS keyframes, so
the SVG needs no JavaScript and works inside GitHub's <img> sandbox.
Imported and called by build_assets.py.
"""
from __future__ import annotations

import math
import random

from build_assets import C, CHAR_W, appear, crt_overlay, esc, f1, glow_filter, svg

W, H = 1000, 600
TOP, ROW1_H, ROW2_H = 38, 268, 265
BAR_Y = TOP + ROW1_H + 1 + ROW2_H  # 572


def smooth(t: float) -> float:
    return t * t * (3 - 2 * t)


def discrete_window(start: float, end: float, total: float) -> str:
    """opacity animation: visible only in [start, end) of a repeating timeline."""
    s, e = start / total, end / total
    if s <= 0:
        vals, kt = "1;0", f"0;{e:.4f}"
    elif e >= 1:
        vals, kt = "0;1", f"0;{s:.4f}"
    else:
        vals, kt = "0;1;0", f"0;{s:.4f};{e:.4f}"
    return (f'<animate attributeName="opacity" values="{vals}" keyTimes="{kt}" calcMode="discrete" '
            f'dur="{total:.2f}s" repeatCount="indefinite"/>')


def pane_title(text: str, active: bool = False) -> str:
    col = C["green"] if active else C["dim"]
    return f'<text x="10" y="16" font-size="11" fill="{col}">{esc(text)}</text>'


# --------------------------------------------------------------------------- #
# 0: robot arm
# --------------------------------------------------------------------------- #
def pane_arm(w: float, h: float) -> str:
    FLOOR, BASE = 238, (170, 210)
    L1, L2 = 105, 90
    BS = 26                        # block size
    FING = 16                      # finger length below the wrist
    TRAVEL = 100
    STACK_X = 290
    blocks = [("AI", 30, C["cyan"]), ("ML", 62, C["green"]), ("3D", 94, C["mag"]), ("WEB", 126, C["amber"])]
    pick_order = [3, 2, 1, 0]       # nearest first; AI ends up on top

    def ik(tx, ty):
        dx, dy = tx - BASE[0], ty - BASE[1]
        d = min(max(math.hypot(dx, dy), abs(L1 - L2) + 1e-3), L1 + L2 - 1e-3)
        c2 = (d * d - L1 * L1 - L2 * L2) / (2 * L1 * L2)
        best = None
        for sgn in (1, -1):
            a2 = sgn * math.acos(max(-1, min(1, c2)))
            a1 = math.atan2(dy, dx) - math.atan2(L2 * math.sin(a2), L1 + L2 * math.cos(a2))
            ex, ey = BASE[0] + L1 * math.cos(a1), BASE[1] + L1 * math.sin(a1)
            if best is None or ey < best[2]:          # elbow-up solution
                best = (a1, a2, ey, ex)
        a1, a2, ey, ex = best
        return (ex, ey), (-math.degrees(a1), -math.degrees(a2))

    # ---- build a timeline of segments ---- #
    segs = []   # (dur, start_pos, end_pos, grip_from, grip_to, carried, label)
    pos = (220.0, 120.0)
    grip = 0.0  # 0 open, 1 closed
    stacked = []

    def move(to, dur, label, carried=None):
        nonlocal pos
        segs.append((dur, pos, to, grip, grip, carried, label))
        pos = to

    def set_grip(g, dur, label, carried=None):
        nonlocal grip
        segs.append((dur, pos, pos, grip, g, carried, label))
        grip = g

    for k, bi in enumerate(pick_order):
        name, sx, _ = blocks[bi]
        pick_y = FLOOR - BS / 2 - FING
        place_y = FLOOR - BS / 2 - BS * k - FING
        move((sx, TRAVEL), 0.9, f"seek({name})")
        move((sx, pick_y), 0.55, f"descend → {name}")
        set_grip(1.0, 0.3, f"grip({name})")
        move((sx, TRAVEL), 0.55, f"lift({name})", bi)
        move((STACK_X, TRAVEL), 1.0, f"carry → stack[{k}]", bi)
        move((STACK_X, place_y), 0.55, f"place({name})", bi)
        set_grip(0.0, 0.3, "release")
        stacked.append(bi)
        move((STACK_X, TRAVEL), 0.45, "retract")
    segs.append((0.9, pos, pos, 0, 0, None, "stack complete ✓"))
    segs.append((0.9, pos, (220.0, 120.0), 0, 0, "reset", "reset()"))

    total = sum(s[0] for s in segs)
    fps = 10
    n = int(total * fps)

    # block home positions (centres)
    home = {i: (b[1], FLOOR - BS / 2) for i, b in enumerate(blocks)}
    arm_d, elbow, wrist = [], [], []
    bpos = {i: [] for i in range(len(blocks))}
    placed: dict[int, tuple] = {}
    seg_starts = []
    acc = 0.0
    for s in segs:
        seg_starts.append(acc)
        acc += s[0]

    for f in range(n + 1):
        t = min(f / fps, total - 1e-6)
        si = max(i for i, st in enumerate(seg_starts) if st <= t)
        dur, a, b, g0, g1, carried, _ = segs[si]
        u = smooth((t - seg_starts[si]) / dur)
        wx, wy = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
        g = g0 + (g1 - g0) * u
        (ex, ey), _ = ik(wx, wy)
        gap = 17 - 3.5 * g
        arm_d.append(f"M{BASE[0]},{BASE[1]}L{f1(ex)},{f1(ey)}L{f1(wx)},{f1(wy)}"
                     f"M{f1(wx-gap)},{f1(wy)}L{f1(wx+gap)},{f1(wy)}"
                     f"M{f1(wx-gap)},{f1(wy)}L{f1(wx-gap)},{f1(wy+FING+4)}"
                     f"M{f1(wx+gap)},{f1(wy)}L{f1(wx+gap)},{f1(wy+FING+4)}")
        elbow.append((ex, ey))
        wrist.append((wx, wy))
        # which blocks are already placed at this time?
        done = 0
        for k2, bi in enumerate(pick_order):
            # block bi counts as placed once its "release" segment has started
            rel_idx = k2 * 8 + 6
            if si >= rel_idx and carried != "reset":
                placed[bi] = (STACK_X, FLOOR - BS / 2 - BS * k2)
            elif carried == "reset":
                placed.pop(bi, None)
        for bi in range(len(blocks)):
            if carried == bi:
                bpos[bi].append((wx, wy + FING))
            elif bi in placed:
                bpos[bi].append(placed[bi])
            else:
                bpos[bi].append(home[bi])

    D = f"{total:.2f}s"
    out = []
    # workspace envelope + floor + pedestal
    out.append(f'<circle cx="{BASE[0]}" cy="{BASE[1]}" r="{L1+L2}" fill="none" stroke="{C["line"]}" '
               f'stroke-dasharray="2 6"/>')
    out.append(f'<line x1="10" y1="{FLOOR}" x2="{w-10}" y2="{FLOOR}" stroke="{C["dim"]}"/>')
    for x in range(14, int(w) - 10, 14):
        out.append(f'<line x1="{x}" y1="{FLOOR}" x2="{x-8}" y2="{FLOOR+8}" stroke="{C["line"]}"/>')
    out.append(f'<rect x="{BASE[0]-20}" y="{BASE[1]}" width="40" height="{FLOOR-BASE[1]}" fill="{C["bar"]}" '
               f'stroke="{C["green"]}" stroke-opacity=".6"/>')
    out.append(f'<text x="{STACK_X}" y="{FLOOR+20}" text-anchor="middle" font-size="10" fill="{C["dim"]}">stack</text>')
    out.append(f'<text x="78" y="{FLOOR+20}" text-anchor="middle" font-size="10" fill="{C["dim"]}">interests</text>')

    # blocks
    for bi, (name, _, col) in enumerate(blocks):
        vals = ";".join(f"{f1(x)},{f1(y)}" for x, y in bpos[bi])
        x0, y0 = bpos[bi][0]
        out.append(
            f'<g transform="translate({f1(x0)},{f1(y0)})">'
            f'<animateTransform attributeName="transform" type="translate" values="{vals}" dur="{D}" '
            f'repeatCount="indefinite"/>'
            f'<rect x="{-BS/2}" y="{-BS/2}" width="{BS}" height="{BS}" rx="3" fill="{C["bar"]}" stroke="{col}"/>'
            f'<text y="4" text-anchor="middle" font-size="{10 if len(name) > 2 else 11}" fill="{col}">{name}</text></g>')

    # arm
    out.append(f'<path d="{arm_d[0]}" fill="none" stroke="{C["green"]}" stroke-width="3.2" stroke-linecap="round" '
               f'filter="url(#glow)"><animate attributeName="d" values="{";".join(arm_d)}" dur="{D}" '
               f'repeatCount="indefinite"/></path>')
    for pts, r, col in ((elbow, 5, C["cyan"]), (wrist, 4, C["white"])):
        out.append(f'<circle cx="{f1(pts[0][0])}" cy="{f1(pts[0][1])}" r="{r}" fill="{C["panel"]}" stroke="{col}" stroke-width="2">'
                   f'<animate attributeName="cx" values="{";".join(f1(p[0]) for p in pts)}" dur="{D}" repeatCount="indefinite"/>'
                   f'<animate attributeName="cy" values="{";".join(f1(p[1]) for p in pts)}" dur="{D}" repeatCount="indefinite"/></circle>')
    out.append(f'<circle cx="{BASE[0]}" cy="{BASE[1]}" r="6" fill="{C["panel"]}" stroke="{C["green"]}" stroke-width="2"/>')

    # telemetry readout, one text per segment, shown only during that segment
    rx = 356
    out.append(f'<rect x="{rx-10}" y="34" width="{w-rx-2}" height="104" rx="4" fill="{C["bg"]}" stroke="{C["line"]}"/>')
    out.append(f'<text x="{rx}" y="54" font-size="11" fill="{C["dim"]}">ik_solver · 2-link · elbow-up</text>')
    for i, (dur, a, b, g0, g1, carried, label) in enumerate(segs):
        _, (t1, t2) = ik(*b)
        gs = "CLOSED" if g1 > .5 else "OPEN"
        gc = C["amber"] if g1 > .5 else C["dim"]
        out.append(
            f'<g opacity="0">{discrete_window(seg_starts[i], seg_starts[i] + dur, total)}'
            f'<text x="{rx}" y="76" font-size="12.5" fill="{C["white"]}">'
            f'<tspan fill="{C["green"]}">&gt; </tspan>{esc(label)}</text>'
            f'<text x="{rx}" y="98" font-size="12" fill="{C["text"]}">θ1 {t1:6.1f}°  θ2 {t2:6.1f}°</text>'
            f'<text x="{rx}" y="120" font-size="12" fill="{C["dim"]}">→ ({b[0]:.0f},{b[1]:.0f}) · '
            f'<tspan fill="{gc}">grip {gs}</tspan></text></g>')
    return "".join(out)


# --------------------------------------------------------------------------- #
# 1: htop parody
# --------------------------------------------------------------------------- #
def pane_htop(w: float, h: float) -> str:
    rnd = random.Random(3)
    out = []
    fs = 11.5
    # CPU meters
    for i in range(4):
        y = 34 + i * 15
        vals = ";".join(f1(rnd.uniform(40, 140)) for _ in range(8))
        vals += ";" + vals.split(";")[0]
        out.append(f'<text x="10" y="{y}" font-size="{fs}" fill="{C["cyan"]}">{i}</text>'
                   f'<text x="20" y="{y}" font-size="{fs}" fill="{C["dim"]}">[</text>'
                   f'<rect x="30" y="{y-9}" width="80" height="9" fill="{C["green"]}">'
                   f'<animate attributeName="width" values="{vals}" dur="{rnd.uniform(2.5,4):.2f}s" repeatCount="indefinite"/></rect>'
                   f'<text x="172" y="{y}" font-size="{fs}" fill="{C["dim"]}">]</text>')
    info = [("Tasks:", " 42, 1 running"), ("Load:", " 9.99 9.99 9.99"),
            ("Caffeine:", " critical"), ("Uptime:", " since first commit")]
    for i, (k, v) in enumerate(info):
        col = C["amber"] if k == "Caffeine:" else C["text"]
        out.append(f'<text x="196" y="{34+i*15}" font-size="{fs}" fill="{C["cyan"]}">{k}'
                   f'<tspan fill="{col}">{esc(v)}</tspan></text>')
    # table
    cols = (10, 52, 104, 148, 196)
    hy = 104
    out.append(f'<rect x="4" y="{hy-12}" width="{w-8}" height="16" fill="{C["green"]}"/>')
    for x, lab in zip(cols, ("PID", "USER", "CPU%", "MEM%", "COMMAND")):
        out.append(f'<text x="{x}" y="{hy}" font-size="{fs}" fill="{C["bg"]}" font-weight="700">{lab}</text>')
    rows = [
        ("1337", "zehna", ("99.9", "99.8"), "42.0", "coffee.exe", C["white"]),
        ("3000", "zehna", ("87.2", "91.4"), "13.1", "overthinking.py", C["text"]),
        ("2187", "zehna", ("64.0", "71.3"), "8.4", "debug_at_3am.sh", C["text"]),
        ("42", "zehna", ("33.3", "28.6"), "4.2", "learn --forever", C["text"]),
        ("8080", "zehna", ("21.5", "26.9"), "6.6", "side_project_17/", C["text"]),
        ("404", "root", ("0.0", "0.0"), "0.0", "sleep.service [FAILED]", C["red"]),
        ("1", "root", ("0.1", "0.1"), "0.1", "social_life <zombie>", C["dim"]),
    ]
    ry0, rh = 124, 18
    sel = ";".join(str(ry0 - 13 + rh * k) for k in (0, 1, 2, 1, 3, 4, 5, 6, 5, 0))
    out.append(f'<rect x="4" y="{ry0-13}" width="{w-8}" height="{rh-1}" fill="{C["cyan"]}" fill-opacity=".14">'
               f'<animate attributeName="y" values="{sel}" calcMode="discrete" dur="9s" repeatCount="indefinite"/></rect>')
    for i, (pid, user, cpu, mem, cmd, col) in enumerate(rows):
        y = ry0 + i * rh
        out.append(f'<text x="{cols[0]}" y="{y}" font-size="{fs}" fill="{C["dim"]}">{pid}</text>'
                   f'<text x="{cols[1]}" y="{y}" font-size="{fs}" fill="{C["dim"]}">{user}</text>'
                   f'<text x="{cols[3]}" y="{y}" font-size="{fs}" fill="{C["dim"]}">{mem}</text>'
                   f'<text x="{cols[4]}" y="{y}" font-size="{fs}" fill="{col}">{esc(cmd)}</text>')
        ccol = C["red"] if float(cpu[0]) > 80 else C["green"]
        if cpu[0] == cpu[1]:
            out.append(f'<text x="{cols[2]}" y="{y}" font-size="{fs}" fill="{ccol}">{cpu[0]}</text>')
        else:
            d = 1.3 + i * .37
            out.append(f'<text x="{cols[2]}" y="{y}" font-size="{fs}" fill="{ccol}">{cpu[0]}'
                       f'<animate attributeName="opacity" values="1;0" calcMode="discrete" dur="{d:.2f}s" repeatCount="indefinite"/></text>'
                       f'<text x="{cols[2]}" y="{y}" font-size="{fs}" fill="{ccol}" opacity="0">{cpu[1]}'
                       f'<animate attributeName="opacity" values="0;1" calcMode="discrete" dur="{d:.2f}s" repeatCount="indefinite"/></text>')
    # function-key bar
    keys = [("F1", "Help"), ("F5", "Tree"), ("F9", "Kill bugs"), ("F10", "Quit(never)")]
    x = 6
    for k, v in keys:
        kw = len(k) * fs * CHAR_W + 4
        out.append(f'<rect x="{x}" y="{h-21}" width="{kw:.1f}" height="15" fill="{C["cyan"]}"/>'
                   f'<text x="{x+2}" y="{h-10}" font-size="{fs}" fill="{C["bg"]}" font-weight="700">{k}</text>'
                   f'<text x="{x+kw+3:.1f}" y="{h-10}" font-size="{fs}" fill="{C["text"]}">{esc(v)}</text>')
        x += kw + len(v) * fs * CHAR_W + 12
    return "".join(out)


# --------------------------------------------------------------------------- #
# 2: synthwave grid
# --------------------------------------------------------------------------- #
def pane_synth(w: float, h: float) -> str:
    HZ = 150
    cx = w / 2
    out = []
    out.append('<defs>'
               '<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
               '<stop offset="0" stop-color="#05010d"/><stop offset=".75" stop-color="#2a0a3d"/>'
               f'<stop offset="1" stop-color="{C["mag"]}" stop-opacity=".55"/></linearGradient>'
               '<linearGradient id="sun" x1="0" y1="0" x2="0" y2="1">'
               f'<stop offset="0" stop-color="{C["amber"]}"/><stop offset="1" stop-color="{C["mag"]}"/></linearGradient>'
               f'<clipPath id="sunclip"><rect x="0" y="0" width="{w}" height="{HZ}"/></clipPath>'
               '</defs>')
    out.append(f'<rect x="0" y="0" width="{w}" height="{HZ}" fill="url(#sky)"/>')
    rnd = random.Random(11)
    for _ in range(22):
        x, y = rnd.uniform(5, w - 5), rnd.uniform(24, HZ - 50)
        d = rnd.uniform(1.5, 4)
        out.append(f'<circle cx="{f1(x)}" cy="{f1(y)}" r="{rnd.choice((0.7, 1, 1.3))}" fill="{C["white"]}">'
                   f'<animate attributeName="opacity" values=".2;1;.2" dur="{d:.1f}s" begin="{-rnd.uniform(0,d):.1f}s" '
                   f'repeatCount="indefinite"/></circle>')
    # sun with retro slits
    sun = [f'<circle cx="{cx}" cy="{HZ}" r="64" fill="url(#sun)" filter="url(#glow)"/>']
    for k in range(6):
        y = HZ - 8 - k * 9
        sun.append(f'<rect x="{cx-70}" y="{y}" width="140" height="{max(1, 5 - k*0.8):.1f}" fill="#1a0629"/>')
    out.append(f'<g clip-path="url(#sunclip)">{"".join(sun)}</g>')
    # wireframe mountains
    rnd = random.Random(5)
    pts, x = [], 0.0
    while x <= w:
        dist = abs(x - cx)
        peak = 6 if dist < 70 else rnd.uniform(14, 46)
        pts.append((x, HZ - peak))
        x += rnd.uniform(16, 30)
    poly = " ".join(f"{f1(a)},{f1(b)}" for a, b in [(0, HZ)] + pts + [(w, HZ)])
    out.append(f'<polygon points="{poly}" fill="#0b0216" stroke="{C["cyan"]}" stroke-width="1" stroke-opacity=".8"/>')
    for (a, b) in pts:
        out.append(f'<line x1="{f1(a)}" y1="{f1(b)}" x2="{f1(a + (cx - a) * .08)}" y2="{HZ}" '
                   f'stroke="{C["cyan"]}" stroke-opacity=".25"/>')
    # ground
    out.append(f'<rect x="0" y="{HZ}" width="{w}" height="{h-HZ}" fill="#08010f"/>')
    for k in range(-14, 15):
        out.append(f'<line x1="{cx}" y1="{HZ}" x2="{f1(cx + k*38)}" y2="{h}" stroke="{C["mag"]}" stroke-opacity=".6"/>')
    N, dur = 9, 2.4
    ys = [HZ + (h - HZ + 10) * (u ** 2.3) for u in [i / 24 for i in range(25)]]
    ops = [min(1, .15 + u * 1.4) for u in [i / 24 for i in range(25)]]
    yv, ov = ";".join(f1(y) for y in ys), ";".join(f"{o:.2f}" for o in ops)
    for i in range(N):
        b = -i * dur / N
        out.append(f'<line x1="0" x2="{w}" y1="{HZ}" y2="{HZ}" stroke="{C["mag"]}" stroke-width="1.2">'
                   f'<animate attributeName="y1" values="{yv}" dur="{dur}s" begin="{b:.2f}s" repeatCount="indefinite"/>'
                   f'<animate attributeName="y2" values="{yv}" dur="{dur}s" begin="{b:.2f}s" repeatCount="indefinite"/>'
                   f'<animate attributeName="stroke-opacity" values="{ov}" dur="{dur}s" begin="{b:.2f}s" repeatCount="indefinite"/></line>')
    out.append(f'<line x1="0" y1="{HZ}" x2="{w}" y2="{HZ}" stroke="{C["mag"]}" stroke-width="1.5" filter="url(#glow)"/>')
    return "".join(out)


# --------------------------------------------------------------------------- #
# 3: Lorenz attractor
# --------------------------------------------------------------------------- #
def pane_lorenz(w: float, h: float) -> str:
    s, r, b = 10.0, 28.0, 8 / 3
    def f(p):
        x, y, z = p
        return (s * (y - x), x * (r - z) - y, x * y - b * z)
    p, dt, pts = (0.1, 0.0, 0.0), 0.005, []
    for i in range(9000):
        k1 = f(p)
        k2 = f(tuple(p[j] + dt / 2 * k1[j] for j in range(3)))
        k3 = f(tuple(p[j] + dt / 2 * k2[j] for j in range(3)))
        k4 = f(tuple(p[j] + dt * k3[j] for j in range(3)))
        p = tuple(p[j] + dt / 6 * (k1[j] + 2 * k2[j] + 2 * k3[j] + k4[j]) for j in range(3))
        if i > 300 and i % 6 == 0:
            pts.append(p)
    a = 0.0
    proj = [(x * math.cos(a) - y * math.sin(a), -z) for x, y, z in pts]
    xs, ys = [q[0] for q in proj], [q[1] for q in proj]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    sc = min((w - 40) / (x1 - x0), (h - 70) / (y1 - y0))
    ox = (w - (x1 - x0) * sc) / 2
    oy = 30 + (h - 70 - (y1 - y0) * sc) / 2
    d = "M" + "L".join(f"{f1(ox + (x - x0) * sc)},{f1(oy + (y - y0) * sc)}" for x, y in proj)
    out = ['<defs><linearGradient id="lz" x1="0" y1="0" x2="1" y2="1">'
           f'<stop offset="0" stop-color="{C["cyan"]}"/><stop offset=".5" stop-color="{C["green"]}"/>'
           f'<stop offset="1" stop-color="{C["mag"]}"/></linearGradient></defs>']
    out.append(f'<path id="lzp" d="{d}" pathLength="1" fill="none" stroke="url(#lz)" stroke-width="1" '
               f'stroke-opacity=".9" class="lz"/>')
    out.append(f'<circle r="3" fill="{C["white"]}" filter="url(#glow)">'
               f'<animateMotion dur="14s" repeatCount="indefinite" keyPoints="0;1;1" keyTimes="0;.82;1" '
               f'calcMode="linear"><mpath href="#lzp"/></animateMotion></circle>')
    out.append(f'<text x="{w-10}" y="{h-10}" text-anchor="end" font-size="10.5" fill="{C["dim"]}">'
               f'σ=10 ρ=28 β=8/3 · RK4</text>')
    return "".join(out)


LORENZ_CSS = """
.lz { stroke-dasharray: 1 1; animation: lz 14s linear infinite; }
@keyframes lz { 0% { stroke-dashoffset: 1; opacity: 1 } 82% { stroke-dashoffset: 0; opacity: 1 }
  94% { stroke-dashoffset: 0; opacity: 1 } 100% { stroke-dashoffset: 0; opacity: 0 } }
"""


# --------------------------------------------------------------------------- #
# 4: pong, two scripted agents
# --------------------------------------------------------------------------- #
def pane_pong(w: float, h: float) -> str:
    T, B = 46, h - 28
    LX, RX, PH = 16, w - 20, 34
    bx, by, vx, vy = w / 2, (T + B) / 2, 160.0, 85.0
    pl = pr = (T + B) / 2
    dt, t, hits_r = 1 / 30, 0.0, 0
    frames, miss_t = [], None
    rnd = random.Random(2)
    while True:
        # agents
        pl += max(-150 * dt, min(150 * dt, by - pl))
        if vx > 0:
            sabotage = hits_r >= 3
            target = (T + PH / 2) if (sabotage and by > (T + B) / 2) else (B - PH / 2) if sabotage else \
                by + 14 * math.sin(t * 6.3)
        else:
            target = (T + B) / 2 + 20 * math.sin(t * 2)
        pr += max(-135 * dt, min(135 * dt, target - pr)) + rnd.uniform(-.6, .6)
        pl, pr = (max(T + PH / 2, min(B - PH / 2, v)) for v in (pl, pr))
        # ball
        bx, by = bx + vx * dt, by + vy * dt
        if by < T + 4 or by > B - 4:
            vy, by = -vy, max(T + 4, min(B - 4, by))
        if vx < 0 and bx <= LX + 7 and abs(by - pl) <= PH / 2 + 3:
            vx, vy = abs(vx) * 1.04, vy + (by - pl) * 3.2
        if vx > 0 and bx >= RX - 3 and abs(by - pr) <= PH / 2 + 3 and miss_t is None:
            vx, vy = -abs(vx) * 1.04, vy + (by - pr) * 3.2
            hits_r += 1
        vy = max(-190, min(190, vy))
        frames.append((bx, by, pl, pr))
        t += dt
        if miss_t is None and bx > w + 6:
            miss_t = t
        if miss_t is not None and t > miss_t + 1.4:
            break
        if t > 40:
            break
    keep = frames[::2]  # 15 fps
    total = len(keep) * dt * 2
    D = f"{total:.2f}s"
    out = [f'<line x1="{w/2}" y1="{T}" x2="{w/2}" y2="{B}" stroke="{C["line"]}" stroke-dasharray="4 6"/>',
           f'<line x1="6" y1="{T}" x2="{w-6}" y2="{T}" stroke="{C["dim"]}"/>',
           f'<line x1="6" y1="{B}" x2="{w-6}" y2="{B}" stroke="{C["dim"]}"/>']
    j = lambda i: ";".join(f1(fr[i]) for fr in keep)
    out.append(f'<rect x="{LX-4}" y="{f1(keep[0][2]-PH/2)}" width="5" height="{PH}" fill="{C["cyan"]}" filter="url(#glow)">'
               f'<animate attributeName="y" values="{";".join(f1(fr[2]-PH/2) for fr in keep)}" dur="{D}" repeatCount="indefinite"/></rect>')
    out.append(f'<rect x="{RX}" y="{f1(keep[0][3]-PH/2)}" width="5" height="{PH}" fill="{C["mag"]}" filter="url(#glow)">'
               f'<animate attributeName="y" values="{";".join(f1(fr[3]-PH/2) for fr in keep)}" dur="{D}" repeatCount="indefinite"/></rect>')
    out.append(f'<circle r="3.6" cx="{f1(keep[0][0])}" cy="{f1(keep[0][1])}" fill="{C["white"]}" filter="url(#glow)">'
               f'<animate attributeName="cx" values="{j(0)}" dur="{D}" repeatCount="indefinite"/>'
               f'<animate attributeName="cy" values="{j(1)}" dur="{D}" repeatCount="indefinite"/></circle>')
    mt = miss_t if miss_t else total
    sx = w / 2
    out.append(f'<text x="{sx-14}" y="{T-8}" text-anchor="end" font-size="15" font-weight="700" fill="{C["cyan"]}">0'
               f'{discrete_window(0, mt, total).replace("<animate", "<animate")}</text>')
    out.append(f'<text x="{sx-14}" y="{T-8}" text-anchor="end" font-size="15" font-weight="700" fill="{C["cyan"]}" opacity="0">1'
               f'{discrete_window(mt, total, total)}</text>')
    out.append(f'<text x="{sx+14}" y="{T-8}" font-size="15" font-weight="700" fill="{C["mag"]}">0</text>')
    out.append(f'<g opacity="0">{discrete_window(mt, total, total)}'
               f'<text x="{sx}" y="{(T+B)/2+4}" text-anchor="middle" font-size="12" fill="{C["amber"]}">'
               f'chaos.reward -= 1</text></g>')
    out.append(f'<text x="8" y="{h-10}" font-size="10.5" fill="{C["cyan"]}">policy: greedy</text>')
    out.append(f'<text x="{w-8}" y="{h-10}" text-anchor="end" font-size="10.5" fill="{C["mag"]}">policy: chaos</text>')
    return "".join(out)


# --------------------------------------------------------------------------- #
# assemble
# --------------------------------------------------------------------------- #
def build_playground(handle: str, host: str) -> str:
    panes = [
        # x, y, w, h, title, builder, active
        (2, TOP, 558, ROW1_H, "0: ik_arm.py", pane_arm, True),
        (561, TOP, 437, ROW1_H, "1: htop", pane_htop, False),
        (2, TOP + ROW1_H + 1, 378, ROW2_H, "2: synth.glsl", pane_synth, False),
        (381, TOP + ROW1_H + 1, 299, ROW2_H, "3: lorenz.py", pane_lorenz, False),
        (681, TOP + ROW1_H + 1, 317, ROW2_H, "4: pong --agents 2", pane_pong, False),
    ]
    defs = [glow_filter("glow", 1.8),
            f'<clipPath id="win"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="12"/></clipPath>']
    parts = [f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="12" fill="{C["panel"]}"/>',
             f'<path d="M1 13 a12 12 0 0 1 12 -12 H{W-13} a12 12 0 0 1 12 12 V35 H1 Z" fill="{C["bar"]}"/>',
             f'<circle cx="22" cy="18" r="6" fill="{C["red"]}"/><circle cx="42" cy="18" r="6" fill="{C["yellow"]}"/>'
             f'<circle cx="62" cy="18" r="6" fill="{C["ok"]}"/>',
             f'<text x="{W/2}" y="23" text-anchor="middle" font-size="13" fill="{C["dim"]}">'
             f'tmux attach -t playground — {handle}@{host}</text>']
    for i, (x, y, w, h, title, fn, active) in enumerate(panes):
        defs.append(f'<clipPath id="p{i}"><rect x="0" y="0" width="{w}" height="{h}"/></clipPath>')
        parts.append(f'<g transform="translate({x},{y})" clip-path="url(#p{i})" class="pane" '
                     f'style="animation-delay:{i*0.12:.2f}s">{fn(w, h)}{pane_title(title, active)}</g>')
    # pane borders (tmux style: active pane border in green)
    r2 = TOP + ROW1_H
    for x1, y1, x2, y2 in ((560.5, TOP, 560.5, r2), (2, r2 + .5, W - 2, r2 + .5),
                           (380.5, r2, 380.5, BAR_Y), (680.5, r2, 680.5, BAR_Y)):
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{C["line"]}"/>')
    parts.append(f'<path d="M2,{r2+.5} H560.5 V{TOP}" fill="none" stroke="{C["green"]}" stroke-opacity=".7"/>')
    # tmux status bar
    parts.append(f'<g clip-path="url(#win)"><rect x="0" y="{BAR_Y}" width="{W}" height="{H-BAR_Y}" fill="{C["green"]}"/></g>')
    win = [("[playground] ", False), ("0:arm*", True), ("  1:htop", False), ("  2:synth", False),
           ("  3:lorenz", False), ("  4:pong", False)]
    spans = "".join(f'<tspan font-weight="{"800" if a else "400"}">{esc(s)}</tspan>' for s, a in win)
    parts.append(f'<text x="14" y="{BAR_Y+17}" font-size="12.5" fill="{C["bg"]}">{spans}</text>')
    parts.append(f'<text x="{W-14}" y="{BAR_Y+17}" text-anchor="end" font-size="12.5" fill="{C["bg"]}">'
                 f'built for fun ♥ · "{handle}@{host}"</text>')
    parts.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="12" fill="none" stroke="{C["line"]}"/>')
    cdefs, cbody, ccss = crt_overlay(W, BAR_Y)
    defs.append(cdefs)
    parts.append(cbody)
    css = LORENZ_CSS + ccss + """
.pane { animation: pin .5s ease-out both; }
@keyframes pin { from { opacity: 0 } to { opacity: 1 } }
"""
    return svg(W, H, f'<defs>{"".join(defs)}</defs>{"".join(parts)}', css,
               "tmux playground: robot arm stacking blocks with inverse kinematics, htop parody, "
               "synthwave grid, Lorenz attractor, and AI-vs-AI pong")
