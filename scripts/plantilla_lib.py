#!/usr/bin/env python3
"""Renderiza la plantilla común de Kenti con la configuración de un módulo (src/grupo_<id>.json).
Lo usa prep.py. (Mismo código que Kenti Marino.)"""
import json, os, re, subprocess, sys, shutil
from collections import Counter
from pathlib import Path
R = Path(__file__).resolve().parent.parent

def dictionary(code="en", extra=()):
    """Lee i18n/<code>.tsv (y los archivos extra, p. ej. ictio-<code>.tsv): español → idioma (en, pt)."""
    d = {}
    for name in (code, *[f"{e}-{code}" for e in extra]):
      for i, line in enumerate((R / f"i18n/{name}.tsv").read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"): continue
        parts = line.split("\t")
        if len(parts) != 2: sys.exit(f"{name}.tsv:{i}: se esperaban 2 columnas")
        es, en = (re.sub(r"\s+", " ", x).strip() for x in parts)
        d[es] = re.sub(r"\{[#t](\d+)\}", r"{\1}", en)
    for es, en in list(d.items()):
        if es.startswith("· ") and en.startswith("· ") and es[2:] not in d: d[es[2:]] = en[2:]
    return d

def i18n_js(extra=()):
    allx = {c: dictionary(c, extra) for c in ("en", "pt") if (R / f"i18n/{c}.tsv").exists()}
    return "const I18N_ALL = " + json.dumps(allx, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";"

def render(cfgfile):
    cfg = json.loads((R / "src" / cfgfile).read_text(encoding="utf-8"))   # cfgfile puede ser "pro/grupo_x.json"
    s = (R / "src/plantilla.html").read_text(encoding="utf-8")
    vals = {k: v for k, v in cfg.items() if k != "GROUP"}
    vals["GROUP_JSON"] = json.dumps(cfg["GROUP"], ensure_ascii=False, separators=(",", ":"))
    fam = R / "src" / ("familias_" + Path(cfgfile).name[len("grupo_"):])   # lista género → familia del módulo, si la tiene
    vals["FAM_JSON"] = fam.read_text(encoding="utf-8").strip() if fam.exists() else "null"
    s = re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: vals[m.group(1)], s)
    js = i18n_js()
    s, n = re.subn(r"/\*I18N-BEGIN\*/.*?/\*I18N-END\*/", lambda m: "/*I18N-BEGIN*/" + js + "/*I18N-END*/", s, flags=re.S)
    assert n == 1, "bloque I18N no encontrado"
    names = re.findall(r"^\s*function ([A-Za-z0-9_$]+)\s*\(", s[s.rindex("<script>"):], re.M)
    dup = sorted(k for k, v in Counter(names).items() if v > 1)
    assert not dup, "funciones repetidas: " + ", ".join(dup)
    return s


def inject_i18n(s, extra=()):
    """Agrega ES/EN/PT a una página que no sale de la plantilla (peces): arranque del idioma, motor de traducción,
    botones ES/EN/PT, y números según el idioma (la página usaba siempre es-AR y coma decimal)."""
    t = (R / "src/plantilla.html").read_text(encoding="utf-8")
    head = re.search(r"<script>\n// Idioma de la interfaz.*?</script>\n", t, re.S).group(0)
    a = t.index("const LANG = window.KENTI_LANG"); b = t.index('const VERSION = "{{VERSION}}";')
    eng = t[a:b]
    eng = re.sub(r"/\*I18N-BEGIN\*/.*?/\*I18N-END\*/", lambda m: "/*I18N-BEGIN*/" + i18n_js(extra) + "/*I18N-END*/", eng, flags=re.S)
    css = "<style>[hidden]{display:none!important} html.i18n-wait body{visibility:hidden} .lang-seg button{padding:4px 9px; font-size:12px; letter-spacing:.04em} .head-right{display:flex; align-items:center; gap:14px 18px; flex-wrap:wrap}</style>\n"
    s = s.replace("<style>[hidden]{display:none!important}</style>\n", "", 1)
    s = s.replace("<title>", css + head + "<title>", 1)
    btns = '<div class="seg lang-seg" role="group" aria-label="Idioma · Language" data-notr><button type="button" data-lang="es" aria-pressed="false" title="Español">ES</button><button type="button" data-lang="en" aria-pressed="false" title="English">EN</button><button type="button" data-lang="pt" aria-pressed="false" title="Português">PT</button></div>\n  '
    s, n = re.subn(r'(<div class="user" title=.*?<b>[^<]*</b></div>\s*</div>)', lambda m: '<div class="head-right">\n    ' + btns + m.group(1) + '\n    </div>', s, count=1, flags=re.S)
    assert n == 1, "no se encontró el bloque del usuario"
    glue = ("<script>(function(){\n" + eng + '\nwindow.tr = tr; window.trTree = trTree; window.trCells = trCells; window.KENTI_LOC = LOC; window.KENTI_DEC = LANG === "en" ? "." : ",";\n'
      'document.querySelectorAll(".lang-seg button").forEach(b => { b.setAttribute("aria-pressed", String(b.dataset.lang === LANG));'
      ' b.onclick = async () => { if (b.dataset.lang === LANG) return; try { localStorage.setItem("kenti-lang", b.dataset.lang); } catch(e){} try { await fetch("/api/idioma", {method:"PUT", headers:{"Content-Type":"application/json", "X-Kenti":"1"}, body: JSON.stringify({idioma: b.dataset.lang})}); } catch(e){} location.reload(); }; });\n'
      "})();</script>\n")
    s = s.replace('"es-AR"', "window.KENTI_LOC")
    s = s.replace("Monitoreo ambiental Salar de Olaroz · Campaña 2, junio 2026", "Peces · diversidad, tallas e IBI")
    s = s.replace("toast(`Medida: ${unitOf().label.toLowerCase()}`);", "toast(`Medida: ${tr(unitOf().label).replace(/^[^(]+/, m => m.toLowerCase())}`);")
    # exportación a Excel y copia de tablas: pasan por tr(), igual que en la plantilla
    for old, new in (
      ("constructor(name){ this.name = name;", "constructor(name){ this.name = tr(name).slice(0, 31);"),
      ("this.images.push({r, c, ...fig, descr});", "this.images.push({r, c, ...fig, descr: tr(descr)});"),
      ('<t xml:space="preserve">${XE(v)}</t></is></c>', '<t xml:space="preserve">${XE(tr(v))}</t></is></c>'),
      ('fill:#465040">Similitud</text>', 'fill:#465040">${tr("Similitud")}</text>'),
      ("  const inner = inlineSvg(svgEl);\n", "  const inner = trTree(inlineSvg(svgEl));\n  title = tr(title); subtitle = tr(subtitle); note = tr(note);\n"),
      ("async function copyText(txt){\n", "async function copyText(txt){\n  txt = trCells(txt);\n"),
    ):
        assert s.count(old) == 1, old
        s = s.replace(old, new)
    s = s.replace('.replace(".", ",")', '.replace(".", window.KENTI_DEC)')
    # números escritos por la persona: en inglés «1,234.5» y «4.5»
    old = r'if (/^[1-9]\d{0,2}(\.\d{3})+(,\d+)?$/.test(t)) t = t.replace(/\./g,"");'
    assert s.count(old) == 1
    s = s.replace(old, r'if (window.KENTI_LANG === "en"){ if (/^[1-9]\d{0,2}(,\d{3})+(\.\d+)?$/.test(t)) t = t.replace(/,/g,""); } else if (/^[1-9]\d{0,2}(\.\d{3})+(,\d+)?$/.test(t)) t = t.replace(/\./g,"");')
    i = s.rindex("<script>")
    s = s[:i] + glue + s[i:]
    return s
