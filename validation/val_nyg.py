#!/usr/bin/env python3
"""Validación de los cocientes de Nygaard del módulo de fitoplancton: Kenti (Chromium) vs. cálculo independiente. Uso: val_nyg.py <n> <semilla>"""
import sys, glob, openpyxl, os, subprocess, time, tempfile, json, shutil
import numpy as np
from playwright.sync_api import sync_playwright
EXE = os.environ.get("KENTI_EXE", "../out/Kenti Limnología/kenti-linux")
NSC, SEED = int(sys.argv[1]), int(sys.argv[2]); LANG = sys.argv[3] if len(sys.argv) > 3 else "es"
GL = {"es": ["Cianobacterias", "Chlorococcales", "Desmidiáceas", "Diatomeas centrales", "Diatomeas pennadas", "Euglenofitas", "Otro"],
      "en": ["Cyanobacteria", "Chlorococcales", "Desmids", "Centric diatoms", "Pennate diatoms", "Euglenophytes", "Other"],
      "pt": ["Cianobactérias", "Chlorococcales", "Desmídias", "Diatomáceas cêntricas", "Diatomáceas penadas", "Euglenófitas", "Outros"]}
G = GL[LANG]
def una(rng, k):
    ns, nt = int(rng.integers(3, 13)), int(rng.integers(12, 70))
    M = rng.poisson(rng.gamma(0.5, 5, size=(nt, ns))) * (rng.random((nt, ns)) < rng.uniform(0.3, 0.9))
    w = rng.dirichlet(np.ones(7) * (0.4 if k % 3 == 0 else 3)); g = rng.choice(len(G), nt, p=w)
    for j in range(ns):
        if M[:, j].sum() == 0: M[rng.integers(nt), j] = 1
    tsv = "Taxón\tGrupo\t" + "\t".join(f"S{j+1}" for j in range(ns)) + "\n" + "\n".join(f"T{i}\t{G[g[i]]}\t" + "\t".join(map(str, M[i])) for i in range(nt))
    return M, g, tsv
def correr(tsv):
    docs = tempfile.mkdtemp(); env = dict(os.environ, KENTI_DOCS=docs, KENTI_NO_BROWSER="1")
    srv = subprocess.Popen([EXE], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1.8)
    os.makedirs(docs + '/Kenti Limnologia', exist_ok=True); open(docs + '/Kenti Limnologia/idioma.txt', 'w').write(LANG + '\n')
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1400, "height": 900}, locale="es-AR"); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto("http://127.0.0.1:47860/g/fitoplancton/"); pg.wait_for_timeout(1400)
            pg.evaluate("""txt=>{const el=document.getElementById('g-0-0');el.focus();const dt=new DataTransfer();dt.setData('text/plain',txt);el.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true}));}""", tsv); pg.wait_for_timeout(1500)
            pg.click("#tab-fito"); pg.wait_for_timeout(800); pg.click("#tab-datos"); pg.wait_for_timeout(1200); pg.click("#btn-export"); pg.wait_for_timeout(3800); b.close()
        f = glob.glob(docs + "/**/*.xlsx", recursive=True)
        return (openpyxl.load_workbook(f[0], data_only=True) if f else None), errs
    finally:
        srv.terminate(); time.sleep(0.3); shutil.rmtree(docs, ignore_errors=True)
def ref(M, g):
    out = []
    for j in range(M.shape[1]):
        pres = M[:, j] > 0; c = {i: int(((g == i) & pres).sum()) for i in range(7)}
        cian, chlo, desm, cent, penn, eugl, otro = [c[i] for i in range(7)]
        div = lambda a, b: a / b if b > 0 else "s/c"
        out.append(dict(S=int(pres.sum()), cnt=[cian, chlo, desm, cent, penn, eugl, otro], Cianofíceo=div(cian, desm), Clorofíceo=div(chlo, desm), Diatomeas=div(cent, penn),
                        Euglenofíceo=div(eugl, cian + chlo), Compuesto=div(cian + chlo + cent + eugl, desm)))
    return out
if __name__ == "__main__":
    rng = np.random.default_rng(SEED); res = []
    for k in range(NSC):
        M, g, tsv = una(rng, k); wb, errs = correr(tsv)
        try:
            ws = [w for w in wb.worksheets if "Nygaard" in w.title][0]; R = [list(r) for r in ws.iter_rows(values_only=True)]
            h = next(i for i, r in enumerate(R) if r[0] in ("Sitio", "Site", "Sítio") and r[2] and "(S)" in str(r[2]))
            rf = ref(M, g); mx = 0.0; sc_ok = True; cnt_ok = True; ncomp = 0; clases_ok = True
            QN = ("Cianofíceo", "Clorofíceo", "Diatomeas", "Euglenofíceo")
            for j, r in enumerate(R[h + 1:h + 1 + M.shape[1]]):
                cnt_ok &= r[2] == rf[j]["S"] and [r[3 + q] for q in range(7)] == rf[j]["cnt"]
                for qi, q in enumerate(QN):
                    got, want = r[10 + qi], rf[j][q]
                    if want == "s/c": sc_ok &= isinstance(got, str)
                    else: mx = max(mx, abs(got - want)); sc_ok &= not isinstance(got, str)
                got, want = r[14], rf[j]["Compuesto"]; ncomp += 1
                if want == "s/c": sc_ok &= isinstance(got, str)
                else: mx = max(mx, abs(got - want)); clases_ok &= isinstance(r[15], str) and r[15] != ""
            r_ = dict(k=k, ns=M.shape[1], nt=M.shape[0], max_dif=mx, s_c_ok=bool(sc_ok), conteos_ok=bool(cnt_ok), compuesto=ncomp, clase_ok=bool(clases_ok), errs=errs, lang=LANG)
        except Exception as e:
            import traceback; traceback.print_exc(); r_ = dict(k=k, error=repr(e)[:200], errs=errs)
        res.append(r_); print(json.dumps(r_, ensure_ascii=False), flush=True)
    json.dump(res, open(f"./res_nyg_{SEED}.json", "w"), ensure_ascii=False)
