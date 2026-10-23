#!/usr/bin/env python3
"""
Generates every animated SVG used by the profile README.

    python scripts/build_assets.py        # writes ./assets/*.svg

Why self-hosted SVGs instead of third-party widget services:
  * GitHub strips <script>/<style> from README HTML, but an SVG loaded through
    <img> may still run its own CSS @keyframes and SMIL <animate> elements.
  * The images live in this repo, so they never break when a free Vercel
    instance gets rate-limited, and they look like nobody else's profile.
  * Images in <img> are sandboxed: no web fonts, no JS, no external fetches.
    So text uses a local monospace stack and all motion is CSS/SMIL.

Edit the CONTENT section, re-run, commit. No dependencies beyond Python 3.8+.
"""
from __future__ import annotations

import html
import math
import pathlib
import random
from itertools import product

OUT = pathlib.Path(__file__).resolve().parent.parent / "assets"

# --------------------------------------------------------------------------- #
# CONTENT — edit me
# --------------------------------------------------------------------------- #
NAME = "ZEHNA ANAS"
HANDLE = "zehna"
HOST = "neural-core"

HEADER_LINES = [
    # (command, output segments [(text, colour-key)])
    ("whoami", [("Zehna Anas", "white"), (" · ", "dim"), ("2nd-year undergrad", "text"),
                (" · ", "dim"), ("aspiring AI engineer", "cyan")]),
    ("cat interests.txt", [("robotics", "green"), (" · ", "dim"), ("ai", "cyan"), (" · ", "dim"),
                           ("ml", "green"), (" · ", "dim"), ("cloud", "cyan"), (" · ", "dim"),
                           ("fullstack", "green"), (" · ", "dim"), ("3d/vfx", "mag")]),
    ("./init_next_project.sh", None),  # last line: no output, blinking cursor
]

MODULES = [
    # (unit, active?, description)
    ("ai-ml.service", True, "llms · rag · agents"),
    ("fullstack.service", True, "fastapi · react · tailwind"),
    ("cloud.service", False, "containers · deploy · infra"),
    ("robotics.service", False, "perception · control · sim"),
    ("vfx-3d.service", False, "3d · motion · compositing"),
]

PROJECTS = {
    "nexusrag": dict(
        title="nexusrag",
        tagline="hybrid-retrieval RAG platform, beyond chat-with-PDF",
        bullets=["dense + BM25 → ensemble → Cohere rerank",
                 "history-aware chat with source metadata",
                 "api-key auth · doc isolation · logging · docker"],
        tags=["FastAPI", "LangChain", "Chroma", "React", "Docker"],
        diagram="nexusrag",
    ),
    "tripweaver": dict(
        title="tripweaver",
        tagline="multi-agent travel planner built on MCP",
        bullets=["LangGraph router dispatches to specialist agents",
                 "every external service behind an MCP server",
                 "FastAPI + React 19 · one-command local stack"],
        tags=["LangGraph", "MCP", "FastAPI", "React", "Tailwind"],
        diagram="tripweaver",
    ),
    "pdf_mind": dict(
        title="pdf_mind",
        tagline="ask questions, get answers grounded in your PDFs",
        bullets=["upload → chunk → embed → semantic search",
                 "retrieved context fed to an LLM for answers",
                 "python backend + react/vite frontend"],
        tags=["Python", "React", "Vite", "RAG"],
        diagram="pdf_mind",
    ),
}

# --------------------------------------------------------------------------- #
# THEME
# --------------------------------------------------------------------------- #
C = dict(
    bg="#070b08", panel="#0a100c", bar="#101a13", line="#1d3a29",
    green="#00ff9c", dim="#4d7a60", text="#b8f5d2", white="#eafff3",
    cyan="#00e5ff", mag="#ff2bd6", amber="#ffb000",
    red="#ff5f56", yellow="#ffbd2e", ok="#27c93f",
)
FONT = ("'JetBrains Mono','Fira Code','Cascadia Code',ui-monospace,SFMono-Regular,"
        "Menlo,Consolas,'Liberation Mono',monospace")
CHAR_W = 0.602  # monospace advance as a fraction of font-size

BASE_CSS = f"""
text {{ font-family: {FONT}; }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
"""

esc = lambda s: html.escape(s, quote=True)
f1 = lambda v: f"{v:.1f}".rstrip("0").rstrip(".")


def svg(w: int, h: int, body: str, css: str = "", title: str = "") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">'
            f'<title>{esc(title)}</title>'
            f'<style>{BASE_CSS}{css}</style>{body}</svg>')


def glow_filter(fid: str, std: float = 2.2) -> str:
    return (f'<filter id="{fid}" x="-50%" y="-50%" width="200%" height="200%">'
            f'<feGaussianBlur stdDeviation="{std}" result="b"/>'
            f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')


def window(w: int, h: int, title: str) -> str:
    """macOS-ish terminal chrome."""
    return (
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="12" fill="{C["panel"]}" stroke="{C["line"]}"/>'
        f'<path d="M1 13 a12 12 0 0 1 12 -12 H{w-13} a12 12 0 0 1 12 12 V35 H1 Z" fill="{C["bar"]}"/>'
        f'<line x1="1" y1="35" x2="{w-1}" y2="35" stroke="{C["line"]}"/>'
        f'<circle cx="22" cy="18" r="6" fill="{C["red"]}"/>'
        f'<circle cx="42" cy="18" r="6" fill="{C["yellow"]}"/>'
        f'<circle cx="62" cy="18" r="6" fill="{C["ok"]}"/>'
        f'<text x="{w/2}" y="23" text-anchor="middle" font-size="13" fill="{C["dim"]}">{esc(title)}</text>'
    )


def crt_overlay(w: int, h: int, top: int = 36) -> tuple[str, str, str]:
    """Static scanline texture + a slow moving refresh band. Returns (defs, body, css)."""
    defs = (
        '<pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse">'
        '<rect width="4" height="1" fill="#000" opacity=".35"/></pattern>'
        '<linearGradient id="band" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{C["green"]}" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="{C["green"]}" stop-opacity=".06"/>'
        f'<stop offset="1" stop-color="{C["green"]}" stop-opacity="0"/></linearGradient>'
    )
    body = (
        f'<rect x="2" y="{top}" width="{w-4}" height="{h-top-2}" fill="url(#scan)" opacity=".5"/>'
        f'<rect class="band" x="2" y="{top-80}" width="{w-4}" height="80" fill="url(#band)"/>'
    )
    css = (f'.band {{ animation: band 7s linear infinite; }}'
           f'@keyframes band {{ from {{ transform: translateY(0) }} to {{ transform: translateY({h-top+80}px) }} }}')
    return defs, body, css


def typing_clip(cid: str, x: float, y: float, n: int, fs: float, start: float, step: float) -> str:
    """clipPath whose width grows one character per `step` seconds after `start`.

    Implemented with SMIL discrete values so it works inside <img>. The rect's
    static width is the full line, so renderers without SMIL still show text.
    """
    cw = fs * CHAR_W
    frames = int(round((start + n * step) / step))
    vals = []
    for k in range(frames + 1):
        t = k * step
        typed = 0 if t < start else min(n, int(round((t - start) / step)))
        vals.append(f1(typed * cw + (0 if typed < n else cw)))
    dur = frames * step
    return (f'<clipPath id="{cid}"><rect x="{x}" y="{y - fs}" width="{f1(n*cw+cw)}" height="{fs*1.5}">'
            f'<animate attributeName="width" values="{";".join(vals)}" dur="{dur:.3f}s" '
            f'calcMode="discrete" fill="freeze"/></rect></clipPath>')


def appear(t: float) -> str:
    """SMIL reveal. CSS animation-delay is unreliable for SVG-in-<img> in
    Chromium (long delays never fire), but SMIL begin times are honoured."""
    return f'<set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/>'


def blink_cursor(x: float, y: float, w: float, h: float, t: float) -> str:
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{C["green"]}" opacity="0">'
            f'{appear(t)}<animate attributeName="fill-opacity" values="1;0" calcMode="discrete" '
            f'dur="1.05s" begin="{t:.2f}s" repeatCount="indefinite"/></rect>')


# --------------------------------------------------------------------------- #
# HEADER: matrix rain + glitch name + typed prompt + rotating tesseract
# --------------------------------------------------------------------------- #
def tesseract_frames(n_frames: int, cx: float, cy: float, radius: float):
    verts4 = [list(v) for v in product((-1, 1), repeat=4)]
    edges = [(i, j) for i in range(16) for j in range(i + 1, 16)
             if sum(a != b for a, b in zip(verts4[i], verts4[j])) == 1]  # 32 edges
    frames = []
    tilt = 0.42
    for k in range(n_frames):
        phi = 2 * math.pi * k / n_frames
        pts = []
        for x, y, z, w in verts4:
            # rotate in the XW plane (the "inside-out" 4D motion)
            x, w = x * math.cos(phi) - w * math.sin(phi), x * math.sin(phi) + w * math.cos(phi)
            # 4D -> 3D perspective
            f4 = 1 / (3 - w)
            x, y, z = x * f4, y * f4, z * f4
            # 3D rotation: spin around Y, fixed tilt around X
            x, z = x * math.cos(phi / 2) + z * math.sin(phi / 2), -x * math.sin(phi / 2) + z * math.cos(phi / 2)
            y, z = y * math.cos(tilt) - z * math.sin(tilt), y * math.sin(tilt) + z * math.cos(tilt)
            # 3D -> 2D perspective
            f3 = 1 / (2.6 - z)
            pts.append((x * f3, y * f3))
        frames.append(pts)
    m = max(max(abs(a), abs(b)) for fr in frames for a, b in fr)
    s = radius / m
    frames = [[(cx + a * s, cy + b * s) for a, b in fr] for fr in frames]
    return edges, frames


def build_header() -> str:
    W, H = 1000, 340
    rnd = random.Random(7)
    defs, parts, css = [], [], []

    defs.append(glow_filter("glow", 2.4))
    defs.append(glow_filter("glowS", 1.4))
    defs.append(f'<clipPath id="body"><rect x="2" y="36" width="{W-4}" height="{H-38}" rx="10"/></clipPath>')
    defs.append('<linearGradient id="fade" x1="0" y1="0" x2="1" y2="0">'
                f'<stop offset="0" stop-color="{C["panel"]}" stop-opacity=".92"/>'
                f'<stop offset=".55" stop-color="{C["panel"]}" stop-opacity=".75"/>'
                f'<stop offset="1" stop-color="{C["panel"]}" stop-opacity=".15"/></linearGradient>')

    parts.append(window(W, H, f"{HANDLE}@{HOST}: ~/profile — zsh"))

    # --- matrix rain ------------------------------------------------------- #
    glyphs = "0123456789ABCDEF<>{}[]=+*#$%/\\"  # ASCII only: safe in every font
    rain = ['<g clip-path="url(#body)" font-size="14">']
    cols = 30
    for i in range(cols):
        x = 18 + i * (W - 30) / cols + rnd.uniform(-4, 4)
        n = rnd.randint(10, 20)
        dur = rnd.uniform(6, 13)
        delay = -rnd.uniform(0, dur)
        chars = "".join(
            f'<tspan x="{f1(x)}" dy="15"'
            + (f' fill="{C["white"]}" fill-opacity="1"' if k == n - 1 else "")
            + f'>{esc(rnd.choice(glyphs))}</tspan>' for k in range(n))
        rain.append(f'<text class="rain" style="animation-duration:{dur:.2f}s;animation-delay:{delay:.2f}s" '
                    f'y="{36 - n*15}" fill="{C["green"]}" fill-opacity=".55">{chars}</text>')
    rain.append("</g>")
    parts.append(f'<g opacity=".22">{"".join(rain)}</g>')
    css.append(f'.rain {{ animation: fall linear infinite; }}'
               f'@keyframes fall {{ from {{ transform: translateY(0) }} to {{ transform: translateY({H+320}px) }} }}')
    parts.append(f'<rect x="2" y="36" width="{W-4}" height="{H-38}" fill="url(#fade)" clip-path="url(#body)"/>')

    # --- tesseract --------------------------------------------------------- #
    cx, cy, R = 835, 188, 118
    edges, frames = tesseract_frames(60, cx, cy, R)
    dur = "14s"
    tes = [f'<g filter="url(#glowS)" class="tes">']
    for i, j in edges:
        xs1 = ";".join(f1(fr[i][0]) for fr in frames + frames[:1])
        ys1 = ";".join(f1(fr[i][1]) for fr in frames + frames[:1])
        xs2 = ";".join(f1(fr[j][0]) for fr in frames + frames[:1])
        ys2 = ";".join(f1(fr[j][1]) for fr in frames + frames[:1])
        p, q = frames[0][i], frames[0][j]
        tes.append(
            f'<line x1="{f1(p[0])}" y1="{f1(p[1])}" x2="{f1(q[0])}" y2="{f1(q[1])}" '
            f'stroke="{C["green"]}" stroke-width="1.3" stroke-opacity=".75">'
            f'<animate attributeName="x1" values="{xs1}" dur="{dur}" repeatCount="indefinite"/>'
            f'<animate attributeName="y1" values="{ys1}" dur="{dur}" repeatCount="indefinite"/>'
            f'<animate attributeName="x2" values="{xs2}" dur="{dur}" repeatCount="indefinite"/>'
            f'<animate attributeName="y2" values="{ys2}" dur="{dur}" repeatCount="indefinite"/></line>')
    for v in range(16):
        xs = ";".join(f1(fr[v][0]) for fr in frames + frames[:1])
        ys = ";".join(f1(fr[v][1]) for fr in frames + frames[:1])
        col = C["cyan"] if v % 5 == 0 else C["white"]
        tes.append(f'<circle cx="{f1(frames[0][v][0])}" cy="{f1(frames[0][v][1])}" r="2.6" fill="{col}">'
                   f'<animate attributeName="cx" values="{xs}" dur="{dur}" repeatCount="indefinite"/>'
                   f'<animate attributeName="cy" values="{ys}" dur="{dur}" repeatCount="indefinite"/></circle>')
    tes.append("</g>")
    parts.append("".join(tes))
    parts.append(f'<text x="{cx}" y="{H-16}" text-anchor="middle" font-size="12" fill="{C["dim"]}">'
                 f'tesseract.render(xw_rotation) // 4D → 2D</text>')
    css.append('.tes { animation: boot 1.2s ease-out .3s both; }'
               '@keyframes boot { from { opacity: 0 } to { opacity: 1 } }')

    # --- glitch name -------------------------------------------------------- #
    nx, ny, nfs = 40, 120, 60
    name_attrs = f'x="{nx}" y="{ny}" font-size="{nfs}" font-weight="800" letter-spacing="5"'
    parts.append(f'<g class="name">'
                 f'<text class="gl1" {name_attrs} fill="{C["mag"]}">{esc(NAME)}</text>'
                 f'<text class="gl2" {name_attrs} fill="{C["cyan"]}">{esc(NAME)}</text>'
                 f'<text class="gl0" {name_attrs} fill="{C["green"]}" filter="url(#glow)">{esc(NAME)}</text>'
                 f'</g>')
    css.append("""
.name { animation: boot .6s steps(4) both; }
.gl0 { animation: flick 4.6s infinite; }
.gl1 { opacity: 0; animation: g1 4.6s infinite; }
.gl2 { opacity: 0; animation: g2 4.6s infinite; }
@keyframes flick { 0%,86%,100% { opacity: 1; transform: none }
  87% { opacity: .55; transform: translateX(2px) skewX(-8deg) }
  89% { opacity: 1; transform: translateX(-2px) }
  91% { opacity: .8; transform: none } }
@keyframes g1 { 0%,85%,95%,100% { opacity: 0; transform: none }
  86% { opacity: .9; transform: translate(-6px, 2px) }
  89% { opacity: .9; transform: translate(4px, -2px) }
  92% { opacity: .7; transform: translate(-3px, 0) } }
@keyframes g2 { 0%,85%,95%,100% { opacity: 0; transform: none }
  86% { opacity: .9; transform: translate(5px, -1px) }
  89% { opacity: .9; transform: translate(-4px, 2px) }
  92% { opacity: .7; transform: translate(2px, 1px) } }
""")

    # --- typed prompt ------------------------------------------------------ #
    fs, step = 17, 0.055
    cw = fs * CHAR_W
    prompt = f"{HANDLE}@{HOST}"
    y, t = 172, 0.9
    for idx, (cmd, out) in enumerate(HEADER_LINES):
        # prompt prefix appears instantly, then the command types out
        px = nx
        pre = (f'<text x="{px}" y="{y}" font-size="{fs}" opacity="0">{appear(t - 0.15)}'
               f'<tspan fill="{C["green"]}">➜ </tspan><tspan fill="{C["cyan"]}">~</tspan>'
               f'<tspan fill="{C["dim"]}"> $ </tspan></text>')
        parts.append(pre)
        cx0 = px + 6 * cw
        cid = f"type{idx}"
        defs.append(typing_clip(cid, cx0, y, len(cmd), fs, t, step))
        parts.append(f'<text x="{f1(cx0)}" y="{y}" font-size="{fs}" fill="{C["white"]}" '
                     f'clip-path="url(#{cid})">{esc(cmd)}</text>')
        t_done = t + len(cmd) * step
        if out:
            y += 27
            spans = "".join(f'<tspan fill="{C[c]}">{esc(s)}</tspan>' for s, c in out)
            parts.append(f'<text x="{px}" y="{y}" font-size="{fs}" opacity="0">'
                         f'{appear(t_done + 0.25)}{spans}</text>')
            y += 33
            t = t_done + 0.75
        else:
            cur_x = cx0 + len(cmd) * cw + 4
            parts.append(blink_cursor(cur_x, y - fs + 3, cw, fs + 1, t_done))

    cdefs, cbody, ccss = crt_overlay(W, H)
    defs.append(cdefs)
    parts.append(cbody)
    css.append(ccss)

    body = f'<defs>{"".join(defs)}</defs>{"".join(parts)}'
    return svg(W, H, body, "".join(css),
               f"Terminal window: {NAME}. Interests: robotics, AI, ML, cloud, fullstack, 3D/VFX.")


# --------------------------------------------------------------------------- #
# MODULES: systemctl-style interest list with live/indeterminate activity bars
# --------------------------------------------------------------------------- #
def build_modules() -> str:
    W = 1000
    row_h, top = 38, 116
    H = top + len(MODULES) * row_h + 44
    defs, parts, css = [glow_filter("glow", 1.6)], [window(W, H, "systemctl --user status 'zehna-*'")], []
    fs = 15
    parts.append(f'<text x="30" y="72" font-size="{fs}"><tspan fill="{C["green"]}">➜ </tspan>'
                 f'<tspan fill="{C["cyan"]}">~</tspan><tspan fill="{C["dim"]}"> $ </tspan>'
                 f'<tspan fill="{C["white"]}">systemctl --user list-units \'zehna-*\'</tspan></text>')
    for hx, lab in ((54, "UNIT"), (250, "STATE"), (400, "ACTIVITY"), (640, "DESCRIPTION")):
        parts.append(f'<text x="{hx}" y="100" font-size="11.5" fill="{C["dim"]}" letter-spacing="1.5">{lab}</text>')
    bx, bw = 400, 200
    for i, (unit, active, desc) in enumerate(MODULES):
        y = top + i * row_h + 14
        d = i * 0.18
        col = C["green"] if active else C["amber"]
        parts.append(f'<g class="row" style="animation-delay:{d:.2f}s">')
        parts.append(f'<circle cx="38" cy="{y-5}" r="5" fill="{col}" filter="url(#glow)" class="'
                     f'{"pulse" if active else "blinkd"}"/>')
        parts.append(f'<text x="54" y="{y}" font-size="{fs}" fill="{C["white"]}">{esc(unit)}</text>')
        parts.append(f'<text x="250" y="{y}" font-size="{fs}" fill="{col}">'
                     f'{"active" if active else "activating"}</text>')
        parts.append(f'<rect x="{bx}" y="{y-11}" width="{bw}" height="10" rx="2" fill="{C["bar"]}" '
                     f'stroke="{C["line"]}"/>')
        if active:
            # live equaliser: 20 bars bouncing at different rates
            rnd = random.Random(i)
            for k in range(20):
                h0 = rnd.uniform(.3, 1)
                parts.append(f'<rect x="{bx + 3 + k*9.8:.1f}" y="{y-10}" width="6" height="8" fill="{col}" '
                             f'class="eq" style="transform-origin:{bx + 6 + k*9.8:.1f}px {y-2}px;'
                             f'animation-duration:{rnd.uniform(.5,1.2):.2f}s;animation-delay:{-rnd.uniform(0,1):.2f}s;'
                             f'--h:{h0:.2f}"/>')
        else:
            defs.append(f'<clipPath id="bc{i}"><rect x="{bx}" y="{y-11}" width="{bw}" height="10" rx="2"/></clipPath>')
            parts.append(f'<g clip-path="url(#bc{i})"><rect class="sweep" x="{bx-70}" y="{y-10}" width="60" '
                         f'height="8" fill="{col}" style="animation-delay:{-i*0.7:.2f}s"/></g>')
        parts.append(f'<text x="640" y="{y}" font-size="{fs-1}" fill="{C["dim"]}">{esc(desc)}</text>')
        parts.append("</g>")
    n_on = sum(1 for m in MODULES if m[1])
    parts.append(f'<text x="30" y="{H-20}" font-size="13" fill="{C["dim"]}">{len(MODULES)} loaded units · '
                 f'<tspan fill="{C["green"]}">{n_on} active</tspan> · '
                 f'<tspan fill="{C["amber"]}">{len(MODULES)-n_on} activating</tspan>'
                 f'  — learning in public</text>')
    css.append("""
.row { opacity: 0; animation: rowin .5s ease-out both; }
@keyframes rowin { from { opacity: 0; transform: translateX(-12px) } to { opacity: 1; transform: none } }
.pulse { animation: pulse 1.6s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: .35 } }
.blinkd { animation: pulse .8s steps(1) infinite; }
.eq { animation: eq ease-in-out infinite alternate; }
@keyframes eq { from { transform: scaleY(.2) } to { transform: scaleY(1) } }
.sweep { animation: sweep 1.8s ease-in-out infinite; }
@keyframes sweep { from { transform: translateX(0) } to { transform: translateX(280px) } }
""")
    cdefs, cbody, ccss = crt_overlay(W, H)
    defs.append(cdefs)
    parts.append(cbody)
    css.append(ccss)
    return svg(W, H, f'<defs>{"".join(defs)}</defs>{"".join(parts)}', "".join(css),
               "Interests: AI/ML and fullstack active; cloud, robotics and 3D/VFX in progress.")


# --------------------------------------------------------------------------- #
# PROJECT CARDS with animated pipeline diagrams
# --------------------------------------------------------------------------- #
def node(cx, cy, label, w=64, h=28, sub=None):
    s = (f'<rect x="{cx-w/2}" y="{cy-h/2}" width="{w}" height="{h}" rx="4" '
         f'fill="{C["bar"]}" stroke="{C["green"]}" stroke-opacity=".8"/>'
         f'<text x="{cx}" y="{cy+4}" text-anchor="middle" font-size="11" fill="{C["text"]}">{esc(label)}</text>')
    if sub:
        s += f'<text x="{cx}" y="{cy+h/2+13}" text-anchor="middle" font-size="10" fill="{C["dim"]}">{esc(sub)}</text>'
    return s


def wire(d):
    return f'<path d="{d}" fill="none" stroke="{C["line"]}" stroke-width="1.6"/>' \
           f'<path d="{d}" fill="none" stroke="{C["green"]}" stroke-width="1.2" stroke-opacity=".35" ' \
           f'stroke-dasharray="3 5" class="flow"/>'


def packet(path, dur, begin, col=None):
    col = col or C["cyan"]
    return (f'<circle r="3.4" fill="{col}" filter="url(#glow)" opacity="0">'
            f'<animateMotion path="{path}" dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.08;.9;1" dur="{dur}s" '
            f'begin="{begin}s" repeatCount="indefinite"/></circle>')


def flash(cx, cy, w, h, dur, begin, kt):
    return (f'<rect x="{cx-w/2}" y="{cy-h/2}" width="{w}" height="{h}" rx="4" fill="{C["green"]}" fill-opacity="0">'
            f'<animate attributeName="fill-opacity" values="0;0;.35;0;0" keyTimes="0;{kt-.06:.2f};{kt:.2f};{kt+.1:.2f};1" '
            f'dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/></rect>')


def diagram_nexusrag():
    Y = 128
    q, d, b, f, r, l = (577, Y), (669, Y - 32), (669, Y + 32), (761, Y), (853, Y), (945, Y)
    A = f"M577,{Y} L609,{Y} C623,{Y} 623,{d[1]} 637,{d[1]} L701,{d[1]} C715,{d[1]} 715,{Y} 729,{Y} L945,{Y}"
    B = f"M577,{Y} L609,{Y} C623,{Y} 623,{b[1]} 637,{b[1]} L701,{b[1]} C715,{b[1]} 715,{Y} 729,{Y} L945,{Y}"
    s = [wire(A), wire(B)]
    for k in range(3):
        s.append(packet(A, 3.6, k * 1.2))
        s.append(packet(B, 3.6, k * 1.2 + .6, C["mag"]))
    s += [node(*q, "QUERY"), node(*d, "DENSE", sub=None), node(*b, "BM25"),
          node(*f, "FUSE", sub="0.5 / 0.5"), node(*r, "RERANK", sub="cohere top-6"),
          node(*l, "LLM", sub="grounded")]
    s.append(f'<text x="669" y="{d[1]-22}" text-anchor="middle" font-size="10" fill="{C["dim"]}">embeddings</text>')
    s.append(f'<text x="669" y="{b[1]+29}" text-anchor="middle" font-size="10" fill="{C["dim"]}">lexical</text>')
    for k in range(3):
        s.append(flash(*l, 64, 28, 3.6, k * 1.2, .97))
    return "".join(s)


def diagram_tripweaver():
    Y = 136
    user, router = (577, Y), (679, Y)
    agents = [("HOTEL", 76), ("FLIGHT", 112), ("ACTIVITY", 160), ("GENERAL", 196)]
    agents = [(n, (791, y)) for n, y in agents]
    mcps = {"HOTEL": ("mcp:hotel", (917, 76)), "FLIGHT": ("mcp:flight", (917, 118)),
            "ACTIVITY": ("mcp:search", (917, 160))}
    s = [wire(f"M609,{Y} L643,{Y}")]
    routes = []
    for name, (ax, ay) in agents:
        seg = f"M715,{Y} C735,{Y} 735,{ay} 755,{ay}"
        s.append(wire(seg))
        path = f"M577,{Y} L715,{Y} C735,{Y} 735,{ay} 755,{ay} L791,{ay}"
        if name in mcps:
            mx, my = mcps[name][1]
            s.append(wire(f"M827,{ay} C854,{ay} 854,{my} 881,{my}"))
            path += f" L827,{ay} C854,{ay} 854,{my} 881,{my} L917,{my}"
        routes.append(path)
    dur = 6.0
    for k, path in enumerate(routes):
        s.append(packet(path, dur / 2, k * dur / 4, [C["cyan"], C["mag"], C["green"], C["amber"]][k]))
    s += [node(*user, "USER"), node(*router, "ROUTER", w=72, sub="langgraph")]
    for k, (name, (ax, ay)) in enumerate(agents):
        s.append(node(ax, ay, name, w=72, h=26))
        s.append(flash(ax, ay, 72, 26, dur / 2, k * dur / 4, .55))
    for name, (lab, (mx, my)) in mcps.items():
        s.append(node(mx, my, lab, w=72, h=26))
    s.append(f'<text x="917" y="188" text-anchor="middle" font-size="10" fill="{C["dim"]}">streamable http</text>')
    return "".join(s)


def diagram_pdf_mind():
    T, Bm = 92, 170
    pdf, chunk, emb, vec = (577, T), (669, T), (761, T), (853, T)
    ask, ret, llm, ans = (577, Bm), (731, Bm), (853, Bm), (945, Bm)
    ing = f"M577,{T} L853,{T}"
    qry = f"M577,{Bm} L853,{Bm} L945,{Bm}"
    ctx = f"M853,{T+14} C853,{T+50} 731,{Bm-50} 731,{Bm-14} L731,{Bm} L945,{Bm}"
    s = [wire(ing), wire(f"M577,{Bm} L945,{Bm}"), wire(f"M853,{T+14} C853,{T+50} 731,{Bm-50} 731,{Bm-14}")]
    for k in range(3):
        s.append(packet(ing, 3, k, C["green"]))
    s.append(packet(qry, 3, .5))
    s.append(packet(ctx, 3, 1.4, C["mag"]))
    s += [node(*pdf, "PDF"), node(*chunk, "CHUNK"), node(*emb, "EMBED"), node(*vec, "VECTORS"),
          node(*ask, "ASK"), node(*ret, "RETRIEVE", w=72), node(*llm, "LLM"), node(*ans, "ANSWER")]
    s.append(f'<text x="577" y="{T-22}" font-size="10" fill="{C["dim"]}" text-anchor="middle">ingest</text>')
    s.append(f'<text x="577" y="{Bm+29}" font-size="10" fill="{C["dim"]}" text-anchor="middle">query</text>')
    return "".join(s)


DIAGRAMS = {"nexusrag": diagram_nexusrag, "tripweaver": diagram_tripweaver, "pdf_mind": diagram_pdf_mind}


def build_card(key: str, p: dict) -> str:
    W, H = 1000, 240
    defs = [glow_filter("glow", 1.8)]
    parts = [window(W, H, f"~/projects/{p['title']} — main")]
    parts.append(f'<line x1="530" y1="50" x2="530" y2="{H-16}" stroke="{C["line"]}" stroke-dasharray="2 4"/>')
    parts.append(f'<text x="30" y="80" font-size="30" font-weight="800" fill="{C["green"]}" filter="url(#glow)" '
                 f'class="ttl"><tspan fill="{C["dim"]}">./</tspan>{esc(p["title"])}</text>')
    parts.append(f'<text x="30" y="106" font-size="14.5" fill="{C["white"]}">{esc(p["tagline"])}</text>')
    for i, b in enumerate(p["bullets"]):
        parts.append(f'<text x="30" y="{134 + i*21}" font-size="13.5" fill="{C["text"]}" class="bl" '
                     f'style="animation-delay:{.3 + i*.15:.2f}s"><tspan fill="{C["green"]}">› </tspan>{esc(b)}</text>')
    x = 30
    for t in p["tags"]:
        w = len(t) * 12 * CHAR_W + 18
        parts.append(f'<rect x="{x}" y="{H-42}" width="{w:.1f}" height="22" rx="11" fill="none" stroke="{C["dim"]}"/>'
                     f'<text x="{x + w/2:.1f}" y="{H-27}" text-anchor="middle" font-size="12" fill="{C["cyan"]}">{esc(t)}</text>')
        x += w + 8
    parts.append(f'<text x="{W-20}" y="23" text-anchor="end" font-size="12" fill="{C["cyan"]}" '
                 f'fill-opacity=".8">open repo ↗</text>')
    parts.append(DIAGRAMS[p["diagram"]]())
    css = """
.flow { animation: flow 1.2s linear infinite; }
@keyframes flow { to { stroke-dashoffset: -16 } }
.ttl { animation: ttl 5s infinite; }
@keyframes ttl { 0%,92%,100% { opacity: 1 } 93% { opacity: .4 } 95% { opacity: 1 } 96% { opacity: .6 } }
.bl { opacity: 0; animation: rowin .5s ease-out both; }
@keyframes rowin { from { opacity: 0; transform: translateX(-10px) } to { opacity: 1; transform: none } }
"""
    cdefs, cbody, ccss = crt_overlay(W, H)
    defs.append(cdefs)
    parts.append(cbody)
    return svg(W, H, f'<defs>{"".join(defs)}</defs>{"".join(parts)}', css + ccss,
               f"Project {p['title']}: {p['tagline']}")


# --------------------------------------------------------------------------- #
# DIVIDER & FOOTER
# --------------------------------------------------------------------------- #
def build_divider() -> str:
    W, H = 1000, 18
    ticks = "".join(f'<rect x="{x}" y="7" width="2" height="4" fill="{C["line"]}"/>' for x in range(10, W, 40))
    body = (
        '<defs><linearGradient id="seg" x1="0" x2="1">'
        f'<stop offset="0" stop-color="{C["green"]}" stop-opacity="0"/>'
        f'<stop offset=".8" stop-color="{C["green"]}"/>'
        f'<stop offset="1" stop-color="{C["white"]}"/></linearGradient>'
        f'{glow_filter("glow", 2)}</defs>'
        f'<line x1="0" y1="9" x2="{W}" y2="9" stroke="{C["line"]}" stroke-width="1.5"/>{ticks}'
        f'<rect class="seg" x="-220" y="7.5" width="220" height="3" fill="url(#seg)" filter="url(#glow)"/>'
        f'<rect class="seg2" x="-120" y="8" width="120" height="2" fill="url(#seg)" opacity=".5"/>'
    )
    css = (".seg { animation: run 3.2s cubic-bezier(.6,0,.4,1) infinite; }"
           ".seg2 { animation: run 3.2s cubic-bezier(.6,0,.4,1) 1.6s infinite; }"
           f"@keyframes run {{ from {{ transform: translateX(0) }} to {{ transform: translateX({W+220}px) }} }}")
    return svg(W, H, body, css, "divider")


def build_footer() -> str:
    W, H = 1000, 110
    defs, parts, css = [], [window(W, H, "session")], []
    fs, step = 15, .06
    cw = fs * CHAR_W
    parts.append(f'<text x="30" y="68" font-size="{fs}"><tspan fill="{C["green"]}">➜ </tspan>'
                 f'<tspan fill="{C["cyan"]}">~</tspan><tspan fill="{C["dim"]}"> $ </tspan></text>')
    cmd = "logout"
    x0 = 30 + 6 * cw
    defs.append(typing_clip("tf", x0, 68, len(cmd), fs, .6, step))
    parts.append(f'<text x="{x0:.1f}" y="68" font-size="{fs}" fill="{C["white"]}" clip-path="url(#tf)">{cmd}</text>')
    t = .6 + len(cmd) * step + .3
    msg = "connection to zehna closed. thanks for visiting — see you in the next commit"
    parts.append(f'<text x="30" y="92" font-size="{fs}" fill="{C["dim"]}" opacity="0">{appear(t)}{esc(msg)}</text>')
    cx = 30 + len(msg) * cw + 6
    parts.append(blink_cursor(cx, 92 - fs + 3, cw, fs + 1, t))
    return svg(W, H, f'<defs>{"".join(defs)}</defs>{"".join(parts)}', "".join(css), "logout")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "header.svg": build_header(),
        "modules.svg": build_modules(),
        "divider.svg": build_divider(),
        "footer.svg": build_footer(),
    }
    for key, p in PROJECTS.items():
        files[f"project-{key}.svg"] = build_card(key, p)
    for name, content in files.items():
        (OUT / name).write_text(content, encoding="utf-8")
        print(f"{name:28s} {len(content)/1024:6.1f} KB")


if __name__ == "__main__":
    main()
