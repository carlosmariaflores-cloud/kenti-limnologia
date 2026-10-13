#!/usr/bin/env python3
"""Peces en ES/EN/PT: la misma comunidad cargada con encabezados, valores y formato numérico propios de cada idioma debe dar celdas numéricas idénticas en el Excel.
Uso: val_peces_lang.py <n> <semilla>"""
import sys, os, glob, time, tempfile, subprocess, shutil, json, importlib.util
import numpy as np, openpyxl
NSC, SEED = int(sys.argv[1]), int(sys.argv[2])
sys.argv = ["x", "1", "1"]
spec = importlib.util.spec_from_file_location("vp", "./val_peces.py"); vp = importlib.util.module_from_spec(spec); spec.loader.exec_module(vp)
from playwright.sync_api import sync_playwright
T = {
 "es": dict(tax="Taxón", ind="Sitio\tEspecie\tLongitud (cm)\tPeso (g)\tSexo\tAnomalías", ras="Especie\tOrigen\tTolerancia\tGremio trófico\tHábitat", dec=",", th="", sex={"M": "M", "H": "H", "J": "J"}, yes="Sí", no="No",
            v={"nativa": "Nativa", "exotica": "Exótica", "intolerante": "Intolerante", "intermedia": "Intermedia", "tolerante": "Tolerante", "omnivoro": "Omnívoro", "insectivoro": "Insectívoro", "piscivoro": "Piscívoro", "herbivoro": "Herbívoro", "bentonica": "Bentónica", "columna": "Columna de agua"}),
 "en": dict(tax="Taxon", ind="Site\tSpecies\tLength (cm)\tWeight (g)\tSex\tAnomalies", ras="Species\tOrigin\tTolerance\tTrophic guild\tHabitat", dec=".", th=",", sex={"M": "Male", "H": "Female", "J": "Juvenile"}, yes="Yes", no="None",
            v={"nativa": "Native", "exotica": "Exotic", "intolerante": "Intolerant", "intermedia": "Intermediate", "tolerante": "Tolerant", "omnivoro": "Omnivore", "insectivoro": "Insectivore", "piscivoro": "Piscivore", "herbivoro": "Herbivore", "bentonica": "Benthic", "columna": "Water column"}),
 "pt": dict(tax="Táxon", ind="Sítio\tEspécie\tComprimento (cm)\tPeso (g)\tSexo\tAnomalias", ras="Espécie\tOrigem\tTolerância\tGuilda trófica\tHábitat", dec=",", th="", sex={"M": "Macho", "H": "Fêmea", "J": "Juvenil"}, yes="Sim", no="Não",
            v={"nativa": "Nativa", "exotica": "Exótica", "intolerante": "Intolerante", "intermedia": "Intermediária", "tolerante": "Tolerante", "omnivoro": "Onívoro", "insectivoro": "Insetívoro", "piscivoro": "Piscívoro", "herbivoro": "Herbívoro", "bentonica": "Bentônica", "columna": "Coluna d'água"}),
}
def num(x, L, nd):
    s = f"{x:.{nd}f}"; ent, _, dec = s.partition(".")
    if L["th"] and len(ent) > 3: ent = f"{int(ent):,}".replace(",", L["th"])
    return ent + (L["dec"] + dec if dec else "")
def exportar(lang, C, esf, tr, ind):
    L = T[lang]; ns, nsp = C.shape[1], C.shape[0]
    sit = [f"S{j+1}" for j in range(ns)]; spn = [f"Pez {chr(97+i)}{i}" for i in range(nsp)]
    tsv = L["tax"] + "\t" + "\t".join(sit) + "\n" + "\n".join(spn[i] + "\t" + "\t".join(str(int(x)) for x in C[i]) for i in range(nsp))
    itsv = L["ind"] + "\n" + "\n".join(f"{sit[j]}\t{spn[i]}\t{num(Lc, L, 2)}\t{num(W, L, 4)}\t{L['sex'][s]}\t{L['yes'] if a else L['no']}" for j, i, Lc, W, s, a in ind)
    rtsv = L["ras"] + "\n" + "\n".join(spn[i] + "\t" + "\t".join(L["v"].get(tr[i].get(k, ""), "") for k in ("origen", "tol", "gremio", "hab")) for i in range(nsp))
    etsv = "\n".join(f"{sit[j]}\t{num(esf[j], L, 2)}" for j in range(ns))
    docs = tempfile.mkdtemp(prefix="kpl-"); env = dict(os.environ, KENTI_DOCS=docs, KENTI_NO_BROWSER="1")
    srv = subprocess.Popen([vp.EXE], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1.8)
    os.makedirs(docs + "/Kenti Limnologia", exist_ok=True); open(docs + "/Kenti Limnologia/idioma.txt", "w").write(lang + "\n"); errs = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1400, "height": 900}, locale={"es": "es-AR", "en": "en-US", "pt": "pt-BR"}[lang])
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto("http://127.0.0.1:47860/g/peces/"); pg.wait_for_timeout(1500)
            paste = """([id,txt])=>{const el=document.getElementById(id);el.focus();const dt=new DataTransfer();dt.setData('text/plain',txt);el.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true}));}"""
            pg.evaluate(paste, ["g-0-0", tsv]); pg.wait_for_timeout(1200)
            pg.click("#tab-datos"); pg.wait_for_timeout(300); pg.fill("#esf-unit", "net-hours"); pg.wait_for_timeout(300)
            pg.evaluate(paste, ["e-0", etsv]); pg.wait_for_timeout(900)
            for tgt, txt in (("ind", itsv), ("rasgos", rtsv)):
                pg.evaluate("t=>window.openLoadDialog(t)", tgt); pg.wait_for_timeout(300); pg.fill("#load-area", txt); pg.click("#load-ok"); pg.wait_for_timeout(1200)
            pg.click("#tab-ind"); pg.wait_for_timeout(800); pg.click("#tab-ibi"); pg.wait_for_timeout(800); pg.click("#ibi-propose"); pg.wait_for_timeout(1000)
            pg.click("#tab-datos"); pg.wait_for_timeout(1200); pg.click("#btn-export"); pg.wait_for_timeout(5000); b.close()
        f = glob.glob(docs + "/**/*.xlsx", recursive=True)
        wb = openpyxl.load_workbook(f[0], data_only=True)
        out = []
        for w in wb.worksheets:
            for r in w.iter_rows(values_only=True):
                for c in r:
                    if isinstance(c, (int, float)) and not isinstance(c, bool): out.append(float(c))
        return out, [w.title for w in wb.worksheets], errs
    finally:
        srv.terminate(); time.sleep(0.3); shutil.rmtree(docs, ignore_errors=True)
if __name__ == "__main__":
    rng = np.random.default_rng(SEED); res = []
    for k in range(NSC):
        C, esf, tr, ind, mm = vp.simular(rng, 0)
        base, tit, e0 = exportar("es", C, esf, tr, ind); r = dict(k=k, n_num=len(base), ind=len(ind), errs=e0, idiomas={})
        for lang in ("en", "pt"):
            v, t, e = exportar(lang, C, esf, tr, ind)
            if len(v) != len(base): r["idiomas"][lang] = dict(ok=False, motivo=f"{len(v)} celdas numéricas vs {len(base)}", errs=e)
            else:
                d = max((abs(a - b) / max(1, abs(a)) for a, b in zip(base, v)), default=0.0)
                r["idiomas"][lang] = dict(ok=d < 1e-9, max_dif_rel=d, errs=e, hojas=t)
        res.append(r); print(json.dumps(r, ensure_ascii=False), flush=True)
    json.dump(res, open(f"./res_peces_lang_{SEED}.json", "w"), ensure_ascii=False)
