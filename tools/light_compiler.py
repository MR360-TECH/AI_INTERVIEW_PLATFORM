"""Turns the dark styling of a page into a navy-and-light-blue light theme (used by build_light_theme.py).

It reads a page's CSS and writes extra rules scoped to  html.light-theme  that change only what is dark:
  - dark backgrounds (and dark borders)  -> light blue-white tints
  - white / light grey text              -> navy
  - bright accent text (cyan, green ...) -> a darker blue / the same hue, darker
  - glows and black shadows              -> soft blue shadows
Light colours that already work on a light page are left alone, so nothing is inverted twice.
"""
import colorsys
import re

COLOR_RE = re.compile(r"#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3,4}\b|rgba?\(\s*[^)]*\)|hsla?\(\s*[^)]*\)|\bwhite\b|\bblack\b")
TEXT_PROPS = {"color", "-webkit-text-fill-color", "fill", "stroke", "caret-color", "text-decoration-color"}
BG_PROPS = {"background", "background-color", "background-image"}
BORDER_PROPS = ("border", "outline", "column-rule")
NAVY_H, NAVY_S = 222 / 360, 0.62
PALETTE = "navy"      # one blue family; purple and pink appear only as soft background fill (see light_polish/base.css)


def parse_color(text):
    t = text.strip().lower()
    if t == "white":
        return 255, 255, 255, 1.0
    if t == "black":
        return 0, 0, 0, 1.0
    if t.startswith("#"):
        h = t[1:]
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return r, g, b, a
    m = re.match(r"rgba?\(\s*([^)]*)\)", t)
    if m:
        parts = [p for p in re.split(r"[\s,/]+", m.group(1).strip()) if p]
        if len(parts) >= 3 and all(re.fullmatch(r"[\d.]+%?", p) for p in parts[:3]):
            vals = [float(p[:-1]) * 2.55 if p.endswith("%") else float(p) for p in parts[:3]]
            a = 1.0
            if len(parts) >= 4:
                a = float(parts[3][:-1]) / 100 if parts[3].endswith("%") else float(parts[3])
            return vals[0], vals[1], vals[2], a
    return None            # hsl(), variables, anything unusual: left untouched


def fmt(r, g, b, a):
    r, g, b = (max(0, min(255, round(v))) for v in (r, g, b))
    if a >= 0.999:
        return "#%02x%02x%02x" % (r, g, b)
    return "rgba(%d,%d,%d,%s)" % (r, g, b, ("%.3f" % a).rstrip("0").rstrip("."))


def hls(r, g, b):
    return colorsys.rgb_to_hls(r / 255, g / 255, b / 255)


def from_hls(h, l, s):
    r, g, b = colorsys.hls_to_rgb(h % 1.0, max(0, min(1, l)), max(0, min(1, s)))
    return r * 255, g * 255, b * 255


def is_cyanish(h):
    return 150 / 360 <= h <= 205 / 360


def to_palette(rgba):
    """Keeps the page in one navy / blue family: cyan and sky become blue, violet becomes indigo-blue.
    Greens, ambers and reds keep their meaning."""
    r, g, b, a = rgba
    h, l, s = hls(r, g, b)
    if s > 0.45 and l > 0.3:
        if is_cyanish(h):
            r2, g2, b2 = from_hls(216 / 360, l if l < 0.6 else 0.55, s)
            return r2, g2, b2, a
        if 250 / 360 <= h <= 295 / 360 and PALETTE == "navy":
            r2, g2, b2 = from_hls(228 / 360, l, s)
            return r2, g2, b2, a
    return rgba


def bg_color(rgba):
    rgba = to_palette(rgba)
    r, g, b, a = rgba
    h, l, s = hls(r, g, b)
    if l < 0.40:                                           # a dark background becomes a light, blue-tinted one
        nl = 1 - l * 0.45
        ns = max(min(s, 0.9) * 0.55, 0.30) if s > 0.05 else 0.30
        nh = h if s > 0.15 else NAVY_H
        r2, g2, b2 = from_hls(nh, nl, ns)
        return fmt(r2, g2, b2, a)
    return fmt(r, g, b, a)


def _text_color(rgba):
    rgba = to_palette(rgba)
    r, g, b, a = rgba
    h, l, s = hls(r, g, b)
    if s < 0.35 and l > 0.55:                              # white / light grey text becomes navy
        t = (l - 0.55) / 0.45
        r2, g2, b2 = from_hls(NAVY_H, 0.45 - t * 0.28, NAVY_S)
        return fmt(r2, g2, b2, max(a, 0.86))          # see-through white text needs real strength once it turns navy
    if s >= 0.35 and l > 0.45:                             # bright accent text becomes a darker blue / darker same hue
        if is_cyanish(h):
            r2, g2, b2 = from_hls(214 / 360, 0.40, 0.80)
        else:
            r2, g2, b2 = from_hls(h, 0.36, min(1.0, s) * 0.9)
        return fmt(r2, g2, b2, a)
    return fmt(r, g, b, a)


REF_BG = (232, 238, 250)       # the darkest ordinary card colour on a light page: text must read clearly on it
MIN_RATIO = 5.2


def _luminance(r, g, b):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _ratio(rgb):
    a, b = _luminance(*rgb), _luminance(*REF_BG)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def text_color(rgba):
    """Text on a light page must be readable: anything still too pale (slate, sky, green, amber ...) is darkened, keeping its hue."""
    out = parse_color(_text_color(rgba))
    if not out:
        return _text_color(rgba)
    r, g, b, a = out
    if a < 0.35:                                           # almost invisible on purpose (watermarks): leave
        return fmt(r, g, b, a)
    h, l, s = hls(r, g, b)
    while _ratio((r, g, b)) < MIN_RATIO and l > 0.04:
        l -= 0.015
        r, g, b = from_hls(h, l, s)
    return fmt(r, g, b, max(a, 0.9) if a < 1 else a)


def gradient_text_color(rgba):
    """Headline gradients: cyan, violet and pink all end up in the blue family."""
    r, g, b, a = rgba
    h, l, s = hls(r, g, b)
    if PALETTE == "navy" and s > 0.45 and 250 / 360 <= h <= 350 / 360:
        r, g, b = from_hls(228 / 360, 0.42, 0.78)
        return fmt(r, g, b, a)
    if PALETTE == "bp" and s > 0.45:
        if is_cyanish(h):
            r, g, b = from_hls(222 / 360, 0.44, 0.85)
        else:
            r, g, b = from_hls(h, 0.42, 0.78)
        return fmt(r, g, b, a)
    return text_color(rgba)


def border_color(rgba):
    rgba = to_palette(rgba)
    r, g, b, a = rgba
    h, l, s = hls(r, g, b)
    if l > 0.6 and a < 1:                                  # glass lines: white or cyan with transparency
        if s > 0.4:
            r2, g2, b2 = from_hls(214 / 360, 0.5, 0.8)
            return fmt(r2, g2, b2, min(1, a * 1.1))
        return fmt(30, 64, 175, min(1, a * 0.8))
    return bg_color(rgba)


def shadow_color(rgba):
    rgba = to_palette(rgba)
    r, g, b, a = rgba
    h, l, s = hls(r, g, b)
    if l < 0.2:                                            # black shadows become soft blue ones
        return fmt(30, 64, 175, min(a * 0.30, 0.22))
    if s > 0.4 and l > 0.4:                                # coloured glow
        return fmt(37, 99, 235, min(a * 0.7, 0.45))
    if l > 0.85:
        return fmt(255, 255, 255, a)
    return fmt(r, g, b, a)


def convert(value, fn):
    def repl(m):
        c = parse_color(m.group(0))
        return fn(c) if c else m.group(0)
    return COLOR_RE.sub(repl, value)


def transform_decl(prop, value, text_clip):
    p = prop.strip().lower()
    if "var(" in value and not COLOR_RE.search(value):
        return None
    if p in BG_PROPS and text_clip and "gradient" in value:
        new = convert(value, gradient_text_color)
    elif p in TEXT_PROPS:
        new = convert(value, text_color)
    elif p in BG_PROPS:
        new = convert(value, bg_color)
    elif p.startswith(BORDER_PROPS):
        new = convert(value, border_color)
    elif p in ("box-shadow", "text-shadow", "drop-shadow"):
        new = convert(value, shadow_color)
    elif p.startswith("--"):
        new = convert(value, bg_color if is_dark_value(value) else text_color)
    else:
        return None
    return new if new != value else None


def is_dark_value(value):
    m = COLOR_RE.search(value)
    c = parse_color(m.group(0)) if m else None
    return bool(c) and hls(c[0], c[1], c[2])[1] < 0.5


def split_decls(body):
    out, depth, cur = [], 0, ""
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == ";" and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


def scope_selector(sel):
    sel = sel.strip()
    if not sel:
        return ""
    if sel.startswith(("html", ":root")):
        return re.sub(r"^(html|:root)", "html.light-theme", sel, count=1)
    if sel == "body" or sel.startswith(("body ", "body.", "body:")):
        return "html.light-theme " + sel
    return "html.light-theme " + sel


def rules(css):
    """Yields (selector_text, body_text, at_prefix) for style rules, walking into @media / @supports."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"@(?:import|charset|namespace)\b[^\n]*;[ \t]*(?=\n|$)", "", css)          # statements without a block would swallow the next rule (an @import URL can contain ";")
    i, n = 0, len(css)
    stack = []
    while i < n:
        j = css.find("{", i)
        if j == -1:
            break
        head = css[i:j].strip()
        # find the matching close brace
        depth, k = 1, j + 1
        while k < n and depth:
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
            k += 1
        body = css[j + 1:k - 1]
        i = k
        if head.startswith("@media") or head.startswith("@supports"):
            for sel, b, pre in rules(body):
                yield sel, b, (head if not pre else head + "|" + pre)
        elif head.startswith("@"):
            continue                                       # keyframes, font-face, import: left as they are
        elif head:
            yield head, body, ""


def compile_light(css, skip_root=False):
    """Returns the light-theme override rules for one stylesheet."""
    out = []
    for sel_text, body, at in rules(css):
        sels = [s.strip() for s in sel_text.split(",") if s.strip()]
        if any("dark-theme" in s or '[data-theme="dark"]' in s or "[data-theme='dark']" in s for s in sels):
            continue                                       # dark-only rules do not apply in light mode
        is_root = all(s.startswith((":root", "html")) and "." not in s.split(":")[0][4:] for s in sels) and any(s.startswith(":root") for s in sels)
        if is_root and skip_root:
            continue
        decls = split_decls(body)
        clip = any(d.split(":", 1)[0].strip().lower().endswith("background-clip") and "text" in d for d in decls if ":" in d)
        new = []
        for d in decls:
            if ":" not in d:
                continue
            prop, val = d.split(":", 1)
            important = "!important" in val
            v = val.replace("!important", "").strip()
            changed = transform_decl(prop, v, clip)
            if changed is not None:
                new.append("%s:%s !important" % (prop.strip(), changed))
        solid_cyan = any(
            d.split(":", 1)[0].strip().lower() in BG_PROPS and not clip and
            any((c := parse_color(m.group(0))) and c[3] >= 0.85 and hls(c[0], c[1], c[2])[2] > 0.6 and hls(c[0], c[1], c[2])[1] > 0.4 and is_cyanish(hls(c[0], c[1], c[2])[0])
                for m in COLOR_RE.finditer(d.split(":", 1)[1]))
            for d in decls if ":" in d)
        if solid_cyan:                                     # a primary button: navy-to-blue fill, white text
            new = [x for x in new if not x.lower().startswith(("background", "color"))]
            new.append("background:linear-gradient(135deg,#0b3a9e,#2563eb) !important" if PALETTE == "navy" else "background:linear-gradient(135deg,#2563eb,#7c3aed) !important")
            new.append("color:#ffffff !important")
            new.append("border-color:transparent !important")
        if not new:
            continue
        if clip:                                           # the background shorthand resets the clip: keep gradient text as text
            new.append("-webkit-background-clip:text !important")
            new.append("background-clip:text !important")
        scoped = ",".join(scope_selector(s) for s in sels)
        rule = "%s{%s}" % (scoped, ";".join(new))
        if at:
            for part in reversed(at.split("|")):
                rule = "%s{%s}" % (part, rule)
        out.append(rule)
    return "\n".join(out)


def style_blocks(html):
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, flags=re.S | re.I))
