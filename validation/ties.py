import sys, json, numpy as np
sys.argv = ["x", sys.argv[1], "0", sys.argv[2]] + sys.argv[3:]
KS = [int(a) for a in sys.argv[4:]]
import importlib.util
spec = importlib.util.spec_from_file_location("vc", "./val_core.py"); vc = importlib.util.module_from_spec(spec); spec.loader.exec_module(vc)
MOD, SEED = sys.argv[1], int(sys.argv[3])
def upgma_posibles(S, tries=400, seed=0):
    rg = np.random.default_rng(seed); vals = set()
    n = S.shape[0]; D0 = 1 - S
    for t in range(tries):
        D = {}; size = {i: 1 for i in range(n)}; mem = {i: [i] for i in range(n)}; act = list(range(n))
        d = {(i, j): D0[i, j] for i in range(n) for j in range(i + 1, n)}; coph = np.zeros((n, n)); nxt = n
        while len(act) > 1:
            pairs = [(d[(min(a, b), max(a, b))], a, b) for ii, a in enumerate(act) for b in act[ii + 1:]]
            m = min(p[0] for p in pairs); c = [p for p in pairs if abs(p[0] - m) < 1e-12]
            _, a, b = c[rg.integers(len(c))] if t else c[0]
            for x in mem[a]:
                for y in mem[b]: coph[x, y] = coph[y, x] = m
            for o in act:
                if o in (a, b): continue
                da = d[(min(a, o), max(a, o))]; db = d[(min(b, o), max(b, o))]
                d[(min(nxt, o), max(nxt, o))] = (size[a] * da + size[b] * db) / (size[a] + size[b])
            size[nxt] = size[a] + size[b]; mem[nxt] = mem[a] + mem[b]; act = [o for o in act if o not in (a, b)] + [nxt]; nxt += 1
        iu = np.triu_indices(n, 1); x = (1 - S)[iu]; y = coph[iu]
        vals.add(round(float(np.corrcoef(x, y)[0, 1]), 10))
    return sorted(vals)
rng = np.random.default_rng(SEED); 
for k in range(max(KS) + 1):
    M = vc.simular(rng, k); tsv, sit, g = vc.tsv_de(M, rng)
    if k in KS:
        path, errs, fito, docs = vc.correr_una(tsv, k); x = vc.leer(path, len(sit))
        print("escenario", k, "sitios", len(sit), "taxones", M.shape[0])
        for key, f in (("Jaccard", vc.jac), ("Morisita-Horn", vc.mh), ("Bray-Curtis", vc.bc)):
            Sm = vc.matriz(M, f); app = x["beta"][key + "_cof"]; ref = vc.cofen(Sm)
            d = (1 - Sm)[np.triu_indices(len(sit), 1)]; emp = len(d) - len(set(np.round(d, 12)))
            pos = upgma_posibles(Sm)
            print(f"  {key}: app={app!r} scipy={ref:.10f} difiere={abs(app-ref):.2e} distancias repetidas={emp} valores posibles según desempate={len(pos)} app∈posibles={any(abs(app-q)<1e-8 for q in pos)}")
