#!/usr/bin/env python3
"""Macroinvertebrados: compara el módulo suelto v0.5 (página construida con el build del repositorio publicado) con el módulo
integrado en Kenti Limnología. Mismos datos (las 43 muestras de campo, con sus nombres tal como vienen en la planilla), mismas
tablas (las de Kenti y una tabla de puntajes cargada por el diálogo) → mismo archivo de datos, mismo texto de índices y mismo Excel.
Uso: comparar_macro.py <carpeta del repositorio kenti-macroinvertebrados>"""
import subprocess, time, os, sys, json, csv, shutil, tempfile, importlib.util, collections
from pathlib import Path
from playwright.sync_api import sync_playwright
import openpyxl
R = Path(__file__).resolve().parent.parent; REPO = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("bm", REPO / "scripts" / "build.py"); bm = importlib.util.module_from_spec(spec); spec.loader.exec_module(bm)
html, _ = bm.render(); tmp = Path(tempfile.mkdtemp(prefix="kenti-mac-")); page = tmp / "macro-suelto.html"; page.write_text(html, encoding="utf-8")
rows = list(csv.DictReader(open(REPO / "datos" / "muestreos_numerados.csv", encoding="utf-8")))
sites = []; tax = collections.OrderedDict()
for r in rows:
    s = f'{r["sitio"].replace("Sitio ", "S")}-{r["estacion"][:3]}-{r["region"][:2]}'
    if s not in sites: sites.append(s)
    tax.setdefault(r["taxon_como_en_la_planilla"], {})[s] = tax.get(r["taxon_como_en_la_planilla"], {}).get(s, 0) + int(r["abundancia"])
TSV = "Taxón\t" + "\t".join(sites) + "\n" + "\n".join(n + "\t" + "\t".join(str(v.get(s, "")) for s in sites) for n, v in tax.items())
TAB = "\n".join("\t".join(r) for r in csv.reader(open(REPO / "tablas" / "bmwp_noa_dominguez_fernandez_1998.csv", encoding="utf-8")))
print(f"{len(sites)} sitios, {len(tax)} taxones")
def correr(url):
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1400, "height": 900}, locale="es-AR")
        pg.on("console", lambda m: errs.append(m.text) if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
        pg.on("response", lambda r: errs.append(f"HTTP {r.status}: {r.url}") if r.status >= 400 and not r.url.endswith("/api/datos") else None)
        pg.goto(url); pg.wait_for_timeout(1500)
        pg.evaluate("""txt => { const el = document.getElementById('g-0-0'); el.focus(); const dt = new DataTransfer(); dt.setData('text/plain', txt);
            el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true})); }""", TSV)
        pg.wait_for_timeout(2500)
        txts = {}
        for t in ("tab-alfa", "tab-beta", "tab-pca", "tab-bio"):
            try: pg.click("#" + t, timeout=3000); pg.wait_for_timeout(1000); txts[t] = pg.inner_text("#p-" + t.split("-")[1])
            except Exception as e: errs.append("tab " + t + ": " + str(e)[:80])
        # una tabla de puntajes cargada por el diálogo
        pg.click("#tab-bio"); pg.wait_for_timeout(300)
        pg.click("[data-refload='bmwp']"); pg.wait_for_timeout(300); pg.fill("#load-area", TAB); pg.click("#load-ok"); pg.wait_for_timeout(1200)
        txts["bio-con-tabla"] = pg.inner_text("#p-bio")
        pg.click("#tab-datos"); pg.wait_for_timeout(2500)
        pg.click("#btn-export"); pg.wait_for_timeout(5000)
        b.close()
    return errs, txts
def celdas(path):
    wb = openpyxl.load_workbook(path, data_only=False)
    return {ws.title: [[c.value for c in row] for row in ws.iter_rows()] for ws in wb.worksheets}
dA = tmp / "suelto"; web = R / "launcher" / "web"
sA = subprocess.Popen([sys.executable, "-I", str(R / "verificacion" / "servidor_suelto.py"), str(page), "kenti-macroinvertebrados", "47871", str(dA), str(web)])
docs = tmp / "docs"; env = dict(os.environ, KENTI_DOCS=str(docs), KENTI_NO_BROWSER="1")
sB = subprocess.Popen([str(R / "kenti-limnologia-linux")], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(2)
try:
    eA, tA = correr("http://127.0.0.1:47871/"); eB, tB = correr("http://127.0.0.1:47860/g/macro/")
finally:
    sA.terminate(); sB.terminate()
print("errores consola suelto:", eA[:5]); print("errores consola integrado:", eB[:5])
for k in tA: print(f"texto de {k}: {'idéntico' if tA[k] == tB.get(k) else 'DISTINTO'} ({len(tA[k])} caracteres)")
dB = docs / "Kenti Limnologia" / "Macroinvertebrados"; xB = sorted(dB.glob("*.xlsx"))
cA = celdas(dA / "export.xlsx"); cB = celdas(xB[0]); print("hojas:", list(cA) == list(cB), list(cA))
def canon(j):
    m = {x["id"]: x["code"] for x in j.get("sites", [])}; j = json.loads(json.dumps(j))
    for x in j.get("sites", []): x["id"] = m[x["id"]]
    for t in ((j.get("bio") or {}).get("tablas") or {}).values(): t.pop("cargada", None)   # fecha y hora de la carga
    for sp in j.get("species", []): sp["counts"] = {m.get(k, k): v for k, v in sp.get("counts", {}).items()}
    return j
jA = canon(json.load(open(dA / "datos.json"))); jB = canon(json.load(open(dB / "datos-macroinvertebrados.json")))
print("datos guardados idénticos:", jA == jB)
for k in sorted(set(jA) | set(jB)):
    if jA.get(k) != jB.get(k): print("  distinto:", k, repr(jA.get(k))[:150], "|", repr(jB.get(k))[:150])
difs = 0
for h in cA:
    for i, (ra, rb) in enumerate(zip(cA[h], cB.get(h, []))):
        for j, (a, b) in enumerate(zip(ra, rb)):
            if a != b and not (isinstance(a, str) and a.startswith("Exportado el")):
                difs += 1
                if difs <= 12: print("DIF", h, i + 1, j + 1, repr(a)[:80], "|", repr(b)[:80])
    if len(cA[h]) != len(cB.get(h, [])): print("filas distintas en", h); difs += 1
print("celdas distintas:", difs); shutil.rmtree(tmp, ignore_errors=True)
