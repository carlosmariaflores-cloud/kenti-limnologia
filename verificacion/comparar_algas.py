#!/usr/bin/env python3
"""Fitoplancton y Fitobentos: compara el módulo suelto v0.3 (vista elegida) con el módulo integrado. Mismos datos y mismas
referencias (diccionario Omnidia + perfiles del IBD, cargadas por el diálogo) → mismo archivo de datos y mismo Excel.
Uso: comparar_algas.py fitoplancton|fitobentos"""
import subprocess, time, os, sys, json, shutil, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
import openpyxl
R = Path(__file__).resolve().parent.parent
MOD = sys.argv[1]
SIT = ["P1", "P2", "P3", "P4"]
# código, nombre, grupo de Nygaard, conteos
TAXA = [("ADMI", "Achnanthidium minutissimum", "Diatomeas pennadas", [40, 22, 9, 60]), ("NINC", "Navicula incerta", "Diatomeas pennadas", [12, 0, 5, 31]),
        ("CMEN", "Cyclotella meneghiniana", "Diatomeas centrales", [0, 7, 19, 2]), ("GPAR", "Gomphonema parvulum", "Diatomeas pennadas", [25, 14, 0, 8]),
        ("", "Microcystis aeruginosa", "Cianobacterias", [6, 6, 6, 0]), ("", "Scenedesmus quadricauda", "Chlorococcales", [44, 31, 17, 26]),
        ("", "Cosmarium botrytis", "Desmidiáceas", [0, 0, 3, 9]), ("", "Euglena viridis", "Euglenofitas", [8, 1, 0, 0]),
        ("ENMI", "Encyonema minutum", "Diatomeas pennadas", [0, 0, 0, 21]), ("", "Ceratium hirundinella", "Otro", [3, 0, 2, 0]),
        ("AUGR", "Aulacoseira granulata", "Diatomeas centrales", [5, 9, 0, 4])]
if MOD == "fitoplancton":
    TSV = "Taxón\tGrupo\tCódigo Omnidia\t" + "\t".join(SIT) + "\n" + "\n".join(f"{n}\t{g}\t{c}\t" + "\t".join(map(str, v)) for c, n, g, v in TAXA)
else:
    TAXA = [t for t in TAXA if t[0]]
    TSV = "Taxón\tCódigo Omnidia\t" + "\t".join(SIT) + "\n" + "\n".join(f"{n}\t{c}\t" + "\t".join(map(str, v)) for c, n, g, v in TAXA)
DIC = "Código\tDenominación\n" + "\n".join(f"{c}\t{n}" for c, n, g, v in TAXA if c)
PERF = [("ADMI", [0.0, 0.1, 0.3, 0.4, 0.2, 0.0, 0.0], 1), ("NINC", [0, 0, 0.1, 0.2, 0.4, 0.3, 0], 2), ("CMEN", [0, 0, 0, 0.1, 0.3, 0.4, 0.2], 2), ("GPAR", [0, 0, 0, 0, 0.2, 0.5, 0.3], 1),
        ("ENMI", [0.1, 0.4, 0.4, 0.1, 0, 0, 0], 3), ("AUGR", [0, 0.2, 0.5, 0.3, 0, 0, 0], 2)]
IBD = "Código\tDenominación\tP1\tP2\tP3\tP4\tP5\tP6\tP7\tV\n" + "\n".join(f"{c}\t{dict((t[0],t[1]) for t in TAXA).get(c,c)}\t" + "\t".join(str(x).replace(".", ",") for x in p) + f"\t{v}" for c, p, v in PERF)
def correr(url, vista):
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1400, "height": 900}, locale="es-AR")
        pg.on("console", lambda m: errs.append(m.text) if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
        pg.on("response", lambda r: errs.append(f"HTTP {r.status}: {r.url}") if r.status >= 400 and not r.url.endswith("/api/datos") else None)
        pg.goto(url); pg.wait_for_timeout(1500)
        if vista: pg.click("#view-" + vista); pg.wait_for_timeout(500)
        # referencias: diccionario y perfiles, por el diálogo de carga
        for ref in (DIC, IBD):
            pg.evaluate("t => window.openLoadDialog('ref')", None); pg.wait_for_timeout(200)
            pg.fill("#load-area", ref); pg.click("#load-ok"); pg.wait_for_timeout(700)
        pg.evaluate("""txt => { const el = document.getElementById('g-0-0'); el.focus(); const dt = new DataTransfer(); dt.setData('text/plain', txt);
            el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true})); }""", TSV)
        pg.wait_for_timeout(1200)
        for t in ("tab-alfa", "tab-beta", "tab-pca", "tab-fito", "tab-diat"):
            try: pg.click("#" + t, timeout=3000); pg.wait_for_timeout(700)
            except Exception as e: errs.append("tab " + t + ": " + str(e)[:80])
        txt = pg.inner_text("#p-diat") if pg.is_visible("#p-diat") else ""
        pg.click("#tab-fito"); pg.wait_for_timeout(600); fito_txt = pg.inner_text("#p-fito")
        pg.click("#tab-datos"); pg.wait_for_timeout(2500)
        pg.click("#btn-export"); pg.wait_for_timeout(3000)
        b.close()
    return errs, fito_txt
def celdas(path):
    wb = openpyxl.load_workbook(path, data_only=False)
    return {ws.title: [[c.value for c in row] for row in ws.iter_rows()] for ws in wb.worksheets}
tmp = Path(tempfile.mkdtemp(prefix="kenti-alg-"))
dA = tmp / "suelto"; web = R / "launcher" / "web"
sA = subprocess.Popen([sys.executable, "-I", str(R / "verificacion" / "servidor_suelto.py"), str(R / "base" / "fito-v0.3-index.html"), "kenti-fitoplancton-fitobentos", "47871", str(dA), str(web)])
docs = tmp / "docs"; env = dict(os.environ, KENTI_DOCS=str(docs), KENTI_NO_BROWSER="1")
sB = subprocess.Popen([str(R / "kenti-limnologia-linux")], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1.5)
try:
    time.sleep(1.0); eA, tA = correr("http://127.0.0.1:47871/", MOD)
    eB, tB = correr(f"http://127.0.0.1:47860/g/{MOD}/", None)
finally:
    sA.terminate(); sB.terminate()
print("errores consola suelto:", eA); print("errores consola integrado:", eB)
print("texto de la pestaña de índices idéntico:", tA == tB, f"({len(tA)} / {len(tB)} caracteres)")
if tA != tB:
    import difflib
    for l in list(difflib.unified_diff(tA.split("\n"), tB.split("\n"), lineterm="", n=0))[:20]: print("   ", l)
dB = docs / "Kenti Limnologia" / MOD.capitalize()
xB = sorted(dB.glob("*.xlsx")); xA = dA / "export.xlsx"
print("excel integrado:", [x.name for x in xB], "| referencias en la carpeta:", sorted(p.name for p in (docs / "Kenti Limnologia").glob("referencia-*.json")))
cA = celdas(xA); cB = celdas(xB[0]); print("hojas suelto:", list(cA)); print("hojas integrado:", list(cB))
difs = 0
for h in cA:
    if h not in cB: print("falta la hoja", h); difs += 1; continue
    for i, (ra, rb) in enumerate(zip(cA[h], cB[h])):
        for j, (a, b) in enumerate(zip(ra, rb)):
            if a != b and not (isinstance(a, str) and a.startswith("Exportado el")):
                difs += 1
                if difs <= 15: print("DIF", h, i + 1, j + 1, repr(a)[:90], "|", repr(b)[:90])
    if len(cA[h]) != len(cB[h]): print("filas distintas en", h, len(cA[h]), len(cB[h])); difs += 1
print("celdas distintas:", difs)
for h in cB:
    if "IBD" in h or "Nygaard" in h: print(h, [[c for c in r if c is not None][:6] for r in cB[h] if any(c is not None for c in r)][5:9])
shutil.rmtree(tmp, ignore_errors=True)
