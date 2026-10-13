import json, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
P = "./"
def jl(f): return [json.loads(l) for l in open(P + f) if l.startswith("{")]
S = {}
core = {"Zooplankton": ["f_zoo.txt"], "Periphyton": ["f_fb.txt"], "Phytoplankton": ["f_fp.txt"], "Fish (shared engine)": ["f_pcore.txt"]}
QN = {"alfa": "Alpha indices (7)", "beta": "Similarity matrices (3)", "cof": "Cophenetic correlation", "pearson": "Pearson r, p, slope, intercept, R²", "pca_val": "PCA eigenvalues", "pca_carga": "PCA loadings", "pca_pt": "PCA site scores"}
rows = {}; nsc = {}; ncomp = {}
for mod, fs in core.items():
    r = [x for f in fs for x in jl(f)]; nsc[mod] = len(r)
    S.setdefault("core_errors", {})[mod] = [x for x in r if "error" in x or x.get("errs")]
    ok = [x for x in r if "alfa" in x]
    S.setdefault("core_sites", {})[mod] = int(sum(x["ns"] for x in ok)); S.setdefault("core_taxa_range", {})[mod] = [int(min(x["nt"] for x in ok)), int(max(x["nt"] for x in ok))]
    S.setdefault("core_sites_range", {})[mod] = [int(min(x["ns"] for x in ok)), int(max(x["ns"] for x in ok))]
    for q in QN:
        v = [x[q] for x in ok if x.get(q) is not None]; rows[(mod, q)] = v
    ties = [x["cof"] for x in ok if x["cof"] > 1e-9]
    S.setdefault("cof_ties", {})[mod] = ties
    S.setdefault("core_max", {})[mod] = {q: (max(v for v in rows[(mod, q)] if not (q == "cof" and v > 1e-9)) if rows[(mod, q)] else None) for q in QN}
S["core_n"] = nsc
# peces específico
pz = jl("f_peces.txt"); okp = [x for x in pz if "D" in x]
S["peces_n"] = len(pz); S["peces_errors"] = [x for x in pz if "error" in x or x.get("errs")]
S["peces_inds"] = int(sum(x["ninds"] for x in okp)); S["peces_sites"] = int(sum(x["ns"] for x in okp)); S["peces_species"] = int(sum(x["nsp"] for x in okp))
S["ibi_metric_values"] = [int(sum(int(x["D"]["ibi_metricas_validas"].split("/")[0]) for x in okp)), int(sum(int(x["D"]["ibi_metricas_validas"].split("/")[1]) for x in okp))]
def flag(k):
    v = [x["F"].get(k) for x in okp if k in x["F"]]; return [int(sum(1 for a in v if a is True)), len(v)]
S["ibi_flags"] = {k: flag(k) for k in ("ibi_limites_ok", "ibi_puntaje_ok", "ibi_suma_ok", "ibi_clase_ok")}
S["peces_max"] = {k: max(x["D"][k] for x in okp if k in x["D"]) for k in okp[0]["D"] if k not in ("ibi_metricas_validas",)}
# nygaard
ny = {}
for lang, f in (("es", "f_nyg_es.txt"), ("en", "f_nyg_en.txt"), ("pt", "f_nyg_pt.txt")):
    r = jl(f); ok = [x for x in r if "max_dif" in x]
    ny[lang] = dict(n=len(r), sites=int(sum(x["ns"] for x in ok)), maxdif=max(x["max_dif"] for x in ok), all_ok=all(x["s_c_ok"] and x["conteos_ok"] and x["clase_ok"] for x in ok), errors=len(r) - len(ok))
S["nygaard"] = ny
# idiomas
lg = {}
for name, f in (("Zooplankton EN", "f_zoo_en.txt"), ("Zooplankton PT", "f_zoo_pt.txt"), ("Phytoplankton EN", "f_fp_en.txt"), ("Periphyton PT", "f_fb_pt.txt")):
    r = jl(f); ok = [x for x in r if "alfa" in x]
    lg[name] = dict(n=len(r), errors=len(r) - len(ok), maxalfa=max(x["alfa"] for x in ok), maxbeta=max(x["beta"] for x in ok), maxcof=max(x["cof"] for x in ok), maxpearson=max(x["pearson"] for x in ok))
S["lang_core"] = lg
try:
    import glob; pl = jl("f_peces_lang.txt") + [x for f in sorted(glob.glob(P + "f_pl_*.txt")) for x in jl(f.split("/")[-1])]; S["peces_lang"] = dict(n=len(pl), ncells=int(sum(x["n_num"] for x in pl)), ok=all(v["ok"] for x in pl for v in x["idiomas"].values()), maxrel=max(v.get("max_dif_rel", 0) for x in pl for v in x["idiomas"].values()))
except Exception as e: S["peces_lang"] = str(e)
json.dump(S, open(P + "summary.json", "w"), indent=1, ensure_ascii=False, default=str)
# ---------- Figura 3
FLOOR = 1e-17
spec = [("Alpha indices", [("Zooplankton", "alfa"), ("Periphyton", "alfa"), ("Phytoplankton", "alfa"), ("Fish (shared engine)", "alfa")]),
        ("Similarity (Jaccard, Morisita–Horn, Bray–Curtis)", [(m, "beta") for m in core]), ("Cophenetic correlation (UPGMA)", [(m, "cof") for m in core]),
        ("Pearson / regression", [(m, "pearson") for m in core]), ("PCA eigenvalues", [(m, "pca_val") for m in core]), ("PCA loadings", [(m, "pca_carga") for m in core]), ("PCA scores", [(m, "pca_pt") for m in core])]
cols = {"Zooplankton": "#1f6f8b", "Periphyton": "#b0381d", "Phytoplankton": "#2f7d32", "Fish (shared engine)": "#8a5cc2"}
fig, axs = plt.subplots(1, 2, figsize=(6.3, 4.6), gridspec_kw=dict(width_ratios=[1.25, 1]), sharey=False)
ax = axs[0]; y = 0; yt = []; yl = []
for lab, items in spec:
    for mod, q in items:
        v = np.array(rows[(mod, q)], float); vv = np.where(v <= 0, FLOOR, v)
        jit = (np.random.default_rng(1).random(len(vv)) - 0.5) * 0.5
        tie = vv > 1e-9 if q == "cof" else np.zeros(len(vv), bool)
        ax.scatter(vv[~tie], (y + jit)[~tie], s=7, color=cols[mod], alpha=0.75, linewidths=0)
        if tie.any(): ax.scatter([7e-7] * int(tie.sum()), (y + jit)[tie], s=14, marker=">", facecolors="none", edgecolors=cols[mod], linewidths=0.8)
        y += 1
    yt.append(y - len(items) / 2 - 0.5); yl.append(lab); y += 0.8
ax.set_xscale("log"); ax.set_xlim(5e-18, 1e-6); ax.set_yticks(yt); ax.set_yticklabels(yl, fontsize=6.3); ax.invert_yaxis()
ax.set_xlabel("Max. absolute difference per dataset", fontsize=7); ax.tick_params(axis="x", labelsize=6.5); ax.axvline(FLOOR * 1.2, color="#999", lw=0.6, ls=":")
ax.text(1.4e-17, -0.9, "exact (0)", fontsize=5.8, color="#666", va="bottom")
ax.set_title("(a) Shared engine", loc="left", fontsize=7.5, fontweight="bold")
hs = [ax.scatter([], [], s=12, color=c, label=m) for m, c in cols.items()]
fig.legend(handles=hs, fontsize=6, loc="lower left", ncol=4, frameon=False, bbox_to_anchor=(0.02, 0.0))
ax = axs[1]; fk = [("lw_a", "L–W a"), ("lw_b", "L–W b"), ("lw_se", "SE of b"), ("lw_lo", "95% CI of b (lower)"), ("lw_hi", "95% CI of b (upper)"), ("lw_r2", "L–W r²"), ("lw_t", "t (b = 3)"), ("lw_p", "p (b = 3)"),
     ("K_media", "Fulton K (mean)"), ("K_sd", "Fulton K (SD)"), ("Kn_media", "Le Cren Kn"), ("cpue", "CPUE"), ("ibi_pct", "IBI (% of max.)")]
for i, (k, lab) in enumerate(fk):
    v = np.array([x["D"][k] for x in okp if k in x["D"]], float); vv = np.where(v <= 0, FLOOR, v)
    jit = (np.random.default_rng(2).random(len(vv)) - 0.5) * 0.5
    ax.scatter(vv, i + jit, s=7, color="#d08a1e", alpha=0.75, linewidths=0)
ax.set_xscale("log"); ax.set_xlim(5e-18, 1e-6); ax.set_yticks(range(len(fk))); ax.set_yticklabels([l for _, l in fk], fontsize=6.3); ax.invert_yaxis()
ax.set_xlabel("Max. relative difference per dataset", fontsize=7); ax.tick_params(axis="x", labelsize=6.5); ax.axvline(FLOOR * 1.2, color="#999", lw=0.6, ls=":")
ax.set_title("(b) Fish module", loc="left", fontsize=7.5, fontweight="bold")
plt.tight_layout(rect=(0, 0.05, 1, 1)); plt.savefig(P + "fig/Fig3_validation.png", dpi=300, facecolor="white"); plt.close()
print(json.dumps(S, ensure_ascii=False, default=str)[:3000])
