#!/usr/bin/env python3
"""Validación del motor común (fitoplancton, fitobentos, zooplancton): la página real de Kenti en Chromium vs. una implementación
independiente en Python (numpy/scipy). Uso: val_core.py <modulo> <n_escenarios> <semilla>"""
import subprocess, time, os, glob, sys, tempfile, json, shutil, re
import numpy as np, openpyxl
from scipy import stats
from scipy.cluster.hierarchy import linkage, cophenet
from scipy.spatial.distance import squareform
from playwright.sync_api import sync_playwright
EXE = os.environ.get("KENTI_EXE", "../out/Kenti Limnología/kenti-linux")
MOD, NSC, SEED = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); LANG = sys.argv[4]
GRUPOS = ["Diatomeas pennadas", "Diatomeas centrales", "Cianobacterias", "Chlorococcales", "Desmidiáceas", "Euglenofitas", "Otro"]

def simular(rng, k):
    """Comunidad simulada: abundancias log-normales por taxón x muestreo Poisson, con ceros estructurales."""
    ns, nt = int(rng.integers(3, 13)), int(rng.integers(6, 71))
    modo = k % 4
    base = rng.lognormal(mean=rng.uniform(0, 2), sigma=rng.uniform(0.5, 2.0), size=nt)
    pres = rng.random((nt, ns)) < rng.uniform(0.25, 0.9)             # presencia por taxón x sitio
    esc = rng.lognormal(0, 0.5, size=ns) * rng.uniform(10, 200)       # esfuerzo por sitio
    lam = base[:, None] * esc[None, :] * pres
    M = rng.poisson(lam)
    if modo == 1:   # sitio con un solo taxón y otro con N = 1
        M[:, 0] = 0; M[rng.integers(nt), 0] = int(rng.integers(2, 50))
        if ns > 2: M[:, 1] = 0; M[rng.integers(nt), 1] = 1
    if modo == 2:   # comunidades muy dispersas (muchos singletons)
        M = rng.poisson(lam * 0.02)
    if modo == 3:   # densidades con decimales
        M = np.round(M * rng.uniform(0.1, 3.0), 2)
    # evitar taxones totalmente vacíos y sitios vacíos (el programa los ignora de otro modo)
    for j in range(ns):
        if M[:, j].sum() == 0: M[rng.integers(nt), j] = 1
    M = M[M.sum(1) > 0]
    return M

def tsv_de(M, rng):
    nt, ns = M.shape
    sit = [f"S{j+1}" for j in range(ns)]
    taxa = [f"Taxon {i+1}" for i in range(nt)]
    if MOD == "fitoplancton":
        g = rng.choice(GRUPOS, size=nt)
        head = "Taxón\tGrupo\t" + "\t".join(sit)
        rows = [f"{t}\t{gg}\t" + "\t".join(fmt(x) for x in r) for t, gg, r in zip(taxa, g, M)]
    else:
        g = None
        head = "Taxón\t" + "\t".join(sit)
        rows = [f"{t}\t" + "\t".join(fmt(x) for x in r) for t, r in zip(taxa, M)]
    return head + "\n" + "\n".join(rows), sit, g

def fmt(x):
    if float(x).is_integer():
        n = int(x)
        return f"{n:,}".replace(",", "," if LANG == "en" else ".") if n >= 1000 else str(n)
    t = f"{x:,.2f}"                      # 1,234.50
    if LANG == "en": return t
    return t.replace(",", "§").replace(".", ",").replace("§", ".")

# ---------- implementación independiente ----------
def alfa(v):
    v = np.asarray(v, float); N = v.sum(); S = int((v > 0).sum())
    p = v[v > 0] / N; H = -(p * np.log(p)).sum(); D = (p ** 2).sum()
    return dict(S=S, N=N, H=H, Simp=1 - D, D=D, Mg=(S - 1) / np.log(N) if N > 1 else None, J=H / np.log(S) if S > 1 else None)
def jac(a, b):
    pa, pb = a > 0, b > 0; u = (pa | pb).sum(); return (pa & pb).sum() / u if u else None
def mh(a, b):
    Na, Nb = a.sum(), b.sum(); da = (a * a).sum() / Na ** 2; db = (b * b).sum() / Nb ** 2
    return 2 * (a * b).sum() / ((da + db) * Na * Nb)
def bc(a, b): return 2 * np.minimum(a, b).sum() / (a + b).sum()
def matriz(M, f): 
    ns = M.shape[1]; return np.array([[1.0 if i == j else f(M[:, i], M[:, j]) for j in range(ns)] for i in range(ns)])
def cofen(S):
    d = 1 - S; np.fill_diagonal(d, 0); Z = linkage(squareform(d, checks=False), "average"); return cophenet(Z, squareform(d, checks=False))[0]

# ---------- lectura del Excel exportado ----------
POS = ["S", "N", "H", "Simp", "D", "Mg", "J"]
def hoja(wb, pref):
    return [w for w in wb.worksheets if w.title.startswith(pref)][0]
def filas(ws): return [list(r) for r in ws.iter_rows(values_only=True)]
def leer(path, ns):
    wb = openpyxl.load_workbook(path, data_only=True); out = {}
    R = filas(hoja(wb, "2 "))
    h = next(i for i, r in enumerate(R) if r and r[0] in ("Sitio", "Site", "Sítio")); cols = R[h]
    A = {}
    for r in R[h + 1:h + 1 + ns + 1]:
        A[r[0]] = {POS[j - 2]: r[j] for j in range(2, 9)}
    out["alfa"] = A
    R = filas(hoja(wb, "4 ")); B = {}
    for i, r in enumerate(R):
        if isinstance(r[0], str) and any(r[0].startswith(n) for n in ("Jaccard", "Morisita", "Bray")):
            key = r[0].split(" ")[0]; blk = R[i + 2:i + 2 + ns]
            B[key] = np.array([[np.nan if x is None else x for x in b[1:1 + ns]] for b in blk], float)
            B[key + "_cof"] = next(([v for v in x[1:] if v is not None] or [None])[0] for x in R[i + 2 + ns:i + 6 + ns] if x[0] and re.search("ofen|ophen", str(x[0])))
    out["beta"] = B
    R = filas(hoja(wb, "5 ")); P = {}
    for i, r in enumerate(R):
        if r[3] == "n" and r[0]:
            P["rel"] = [x for x in R[i + 1:i + 3]]
        if r[0] == "Eje" and r[1] == "Autovalor":
            P["val"] = [x[1:4] for x in R[i + 1:i + 1 + 4]]
        if r[0] == "Sitio" and r[2] is None and False: pass
        if r[0] == "Puntajes de los sitios":
            P["scores"] = {x[0]: x[1:5] for x in R[i + 2:i + 2 + ns]}
        if r[0] == "Cargas: correlación de cada variable con el eje":
            P["cargas"] = {x[0]: x[1:5] for x in R[i + 2:i + 6]}
    out["pca"] = P
    return out

def correr_una(tsv, k):
    docs = tempfile.mkdtemp(prefix="kv-"); env = dict(os.environ, KENTI_DOCS=docs, KENTI_NO_BROWSER="1")
    srv = subprocess.Popen([EXE], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1.8)
    os.makedirs(docs + '/Kenti Limnologia', exist_ok=True); open(docs + '/Kenti Limnologia/idioma.txt', 'w').write(LANG + '\n')
    errs = []; fito = ""
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1400, "height": 900}, locale="es-AR")
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"http://127.0.0.1:47860/g/{MOD}/"); pg.wait_for_timeout(1300)
            pg.evaluate("""txt=>{const el=document.getElementById('g-0-0');el.focus();const dt=new DataTransfer();dt.setData('text/plain',txt);el.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true}));}""", tsv)
            pg.wait_for_timeout(1500)
            for t in ("tab-alfa", "tab-beta", "tab-pca") + (("tab-fito",) if MOD == "fitoplancton" else ()):
                try: pg.click("#" + t, timeout=3000); pg.wait_for_timeout(500)
                except Exception as e: errs.append("tab " + t + str(e)[:60])
            if MOD == "fitoplancton":
                try: fito = pg.inner_text("#p-fito")
                except Exception: pass
            pg.click("#tab-datos"); pg.wait_for_timeout(1200); pg.click("#btn-export"); pg.wait_for_timeout(3500)
            b.close()
        f = glob.glob(docs + "/**/*.xlsx", recursive=True)
        return (f[0] if f else None), errs, fito, docs
    finally:
        srv.terminate(); time.sleep(0.3)

def comparar(M, sit, x):
    ns = M.shape[1]; d = {}
    mx = lambda a, b: float(abs(a - b))
    mxs = {"alfa": 0.0, "beta": 0.0, "cof": 0.0, "pearson": 0.0, "pca_val": None, "pca_carga": None, "pca_pt": None}
    up = lambda k, v: mxs.__setitem__(k, v if mxs[k] is None else max(mxs[k], v))
    nulos_ok = True
    colmap = {k: k for k in POS}
    A = []
    for j, s in enumerate(sit):
        ref = alfa(M[:, j]); got = x["alfa"][s]
        for k, c in colmap.items():
            g, r = got[c], ref[k]
            if r is None: nulos_ok &= (g is None)
            else:
                if g is None: nulos_ok = False; continue
                mxs["alfa"] = max(mxs["alfa"], mx(g, r))
        A.append(ref)
    # gamma
    tot = M.sum(1); rg = alfa(tot); gg = list(x["alfa"].values())[ns]
    for k, c in colmap.items():
        if rg[k] is not None and gg[c] is not None: mxs["alfa"] = max(mxs["alfa"], mx(gg[c], rg[k]))
    for key, f in (("Jaccard", jac), ("Morisita-Horn", mh), ("Bray-Curtis", bc)):
        Sm = matriz(M, f); G = x["beta"][key.split("-")[0] if key != "Morisita-Horn" else "Morisita-Horn"] if False else None
    for key, f, kk in (("Jaccard", jac, "Jaccard"), ("Morisita-Horn", mh, "Morisita-Horn"), ("Bray-Curtis", bc, "Bray-Curtis")):
        Sm = matriz(M, f); got = next(v for n, v in x["beta"].items() if n.startswith(key.split("-")[0]) and not n.endswith("_cof"))
        mxs["beta"] = max(mxs["beta"], float(np.nanmax(abs(Sm - got))))
        cof = next(v for n, v in x["beta"].items() if n.startswith(key.split("-")[0]) and n.endswith("_cof"))
        if cof is None: mxs["cof_blank"] = mxs.get("cof_blank", 0) + 1; mxs["cof_blank_ref_nan"] = bool(np.isnan(Sm).any()) if False else None
        else: mxs["cof"] = max(mxs["cof"], mx(cof, cofen(Sm)))
    # Pearson S–H y N–H
    S_ = np.array([a["S"] for a in A], float); N_ = np.array([a["N"] for a in A], float); H_ = np.array([a["H"] for a in A], float)
    for row, xx in zip(x["pca"]["rel"], (S_, N_)):
        if ns >= 3:
            lr = stats.linregress(xx, H_)
            ref = [lr.rvalue, lr.pvalue, lr.slope, lr.intercept, lr.rvalue ** 2]
            got = row[4:9]
            if all(g is not None for g in got): mxs["pearson"] = max(mxs["pearson"], max(abs(a - b) for a, b in zip(ref, got)))
    # PCA sobre S, N, J, H (matriz de correlación)
    if all(a["J"] is not None for a in A) and ns >= 4 and "val" in x["pca"]:
        X = np.array([[a["S"], a["N"], a["J"], a["H"]] for a in A], float)
        Z = (X - X.mean(0)) / X.std(0, ddof=1); C = np.corrcoef(X.T)
        w, V = np.linalg.eigh(C); o = np.argsort(w)[::-1]; w, V = w[o], V[:, o]
        for i in range(4):
            if x["pca"]["val"][i][0] is not None: up("pca_val", mx(x["pca"]["val"][i][0], w[i]))
        sc = Z @ V
        for i, s in enumerate(sit):
            got = np.array([np.nan if q is None else q for q in x["pca"]["scores"][s]], float)
            for c in range(4):
                if abs(w[c]) > 1e-6 and not np.isnan(got[c]): up("pca_pt", min(abs(got[c] - sc[i, c]), abs(got[c] + sc[i, c])))
        load = V * np.sqrt(np.maximum(w, 0))
        names = list(x["pca"]["cargas"])
        for r_i, nm in enumerate(names[:4]):
            got = np.array([np.nan if q is None else q for q in x["pca"]["cargas"][nm]], float)
            for c in range(4):
                if abs(w[c]) > 1e-6 and not np.isnan(got[c]): up("pca_carga", min(abs(got[c] - load[r_i, c]), abs(got[c] + load[r_i, c])))
    mxs["nulos_ok"] = bool(nulos_ok); return mxs

if __name__ == "__main__":
    res = []; rng = np.random.default_rng(SEED)
    for k in range(NSC):
        M = simular(rng, k); tsv, sit, g = tsv_de(M, rng)
        path, errs, fito, docs = correr_una(tsv, k)
        try:
            if not path: res.append(dict(k=k, error="sin archivo", errs=errs)); continue
            r = comparar(M, sit, leer(path, len(sit))); r.update(k=k, ns=len(sit), nt=M.shape[0], errs=errs, modo=k % 4)
        except Exception as e:
            import traceback; traceback.print_exc(); r = dict(k=k, error=repr(e)[:200], errs=errs, ns=len(sit), nt=M.shape[0], modo=k % 4)
        res.append(r); print(json.dumps(r, ensure_ascii=False), flush=True)
        shutil.rmtree(docs, ignore_errors=True)
    json.dump(res, open(f"./res_{MOD}_{SEED}.json", "w"), ensure_ascii=False)
