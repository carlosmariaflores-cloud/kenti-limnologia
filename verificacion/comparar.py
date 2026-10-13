#!/usr/bin/env python3
"""Compara el módulo suelto con el integrado: mismos datos → mismo archivo de datos y mismo Excel.
Uso: comparar.py <modulo>   (por ahora: zooplancton)"""
import subprocess, time, os, sys, json, shutil, tempfile, signal
from pathlib import Path
from playwright.sync_api import sync_playwright
import openpyxl
R = Path(__file__).resolve().parent.parent
TSV = "\t".join(["Taxón","P1","P2","P3","P4"]) + "\n" + "\n".join("\t".join(map(str,r)) for r in [
 ["Brachionus calyciflorus",12,0,5,40],["Keratella cochlearis",30,22,8,3],["Daphnia pulex",0,4,19,7],
 ["Bosmina longirostris",6,6,0,11],["Cyclops sp.",25,14,9,2],["Nauplios",44,31,17,26],["Moina micrura",0,0,3,9],["Polyarthra vulgaris",8,1,0,0]])
TSV_PECES = "\t".join(["Especie","P1","P2","P3","P4"]) + "\n" + "\n".join("\t".join(map(str,r)) for r in [
 ["Astyanax lacustris",12,0,5,40],["Bryconamericus thomasi",30,22,8,3],["Trichomycterus alterus",0,4,19,7],
 ["Hoplias malabaricus",6,6,0,11],["Characidium sp.",25,14,9,2],["Cnesterodon decemmaculatus",44,31,17,26],["Oncorhynchus mykiss",0,0,3,9],["Jenynsia lineata",8,1,0,0]])
def correr(url, nombre, carpeta_xlsx):
    errs=[]
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(viewport={"width":1400,"height":900})
        pg.on("console", lambda m: errs.append(m.text) if m.type in ("error","warning") else None)
        pg.on("pageerror", lambda e: errs.append("pageerror: "+str(e)))
        pg.on("requestfailed", lambda r: errs.append("requestfailed: "+r.url))
        pg.on("response", lambda r: errs.append(f"HTTP {r.status}: {r.url}") if r.status>=400 and not r.url.endswith("/api/datos") else None)
        pg.goto(url); pg.wait_for_timeout(1200)
        TXT = TSV_PECES if os.environ.get("MOD") == "peces" else TSV
        pg.evaluate("""txt => { const el = document.getElementById('g-0-0'); el.focus();
            const dt = new DataTransfer(); dt.setData('text/plain', txt);
            el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true})); }""", TXT)
        pg.wait_for_timeout(1000)
        for t in ("tab-alfa","tab-beta","tab-pca") + (("tab-ind","tab-ibi") if os.environ.get("MOD") == "peces" else ()):
            try: pg.click("#"+t); pg.wait_for_timeout(500)
            except Exception as e: errs.append("tab "+t+": "+str(e)[:80])
        pg.click("#tab-datos"); pg.wait_for_timeout(2500)   # espera el guardado automático
        pg.click("#btn-export"); pg.wait_for_timeout(2500)
        textos = {t: pg.inner_text("#view-"+t.split("-")[1]) if pg.query_selector("#view-"+t.split("-")[1]) else None for t in ("tab-alfa","tab-beta","tab-pca")}
        b.close()
    return errs
def celdas(path):
    wb=openpyxl.load_workbook(path, data_only=False); out={}
    for ws in wb.worksheets:
        out[ws.title]=[[c.value for c in row] for row in ws.iter_rows()]
    return out
if __name__=="__main__":
    mod=sys.argv[1]; os.environ["MOD"]=mod
    cfg={"zooplancton":("base/zoo-v0.1-index.html","kenti-zooplancton","Zooplancton","datos-zooplancton.json"),
         "peces":("base/ictio-v0.2-index.html","kenti-ictiologico","Peces","datos-ictiologia.json")}[mod]
    page,app,sub,dname=cfg
    tmp=Path(tempfile.mkdtemp(prefix="kenti-cmp-"))
    # A: módulo suelto (página original + servidor imitado)
    dA=tmp/"suelto"; web=R/"launcher"/"web"
    sA=subprocess.Popen([sys.executable,"-I",str(R/"verificacion"/"servidor_suelto.py"),str(R/page),app,"47871",str(dA),str(web)])
    # B: integrado
    docs=tmp/"docs"; env=dict(os.environ,KENTI_DOCS=str(docs),KENTI_NO_BROWSER="1")
    sB=subprocess.Popen([str(R/"kenti-limnologia-linux")],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    try:
        eA=correr("http://127.0.0.1:47871/","suelto",dA)
        eB=correr(f"http://127.0.0.1:47860/g/{mod}/","integrado",None)
    finally:
        sA.terminate(); sB.terminate()
    print("errores consola suelto:",eA); print("errores consola integrado:",eB)
    dB=docs/"Kenti Limnologia"/sub
    def canon(j):
        # los id de sitio llevan la hora de creación: se cambian por el código del sitio
        m={x["id"]:x["code"] for x in j.get("sites",[])}
        j=json.loads(json.dumps(j))
        for x in j.get("sites",[]): x["id"]=m[x["id"]]
        for sp in j.get("species",[]): sp["counts"]={m.get(k,k):v for k,v in sp.get("counts",{}).items()}
        return j
    jA=canon(json.load(open(dA/"datos.json"))); jB=canon(json.load(open(dB/dname)))
    print("datos guardados idénticos:", jA==jB, "| claves:", sorted(jA)[:8])
    for k in sorted(set(jA)|set(jB)):
        if jA.get(k)!=jB.get(k): print("  distinto:",k,repr(jA.get(k))[:200],"|",repr(jB.get(k))[:200])
    xB=sorted(dB.glob("*.xlsx")); print("excel integrado:",[x.name for x in xB])
    cA=celdas(dA/"export.xlsx"); cB=celdas(xB[0])
    print("hojas:", list(cA)==list(cB), list(cA))
    difs=0
    for h in cA:
        for i,(ra,rb) in enumerate(zip(cA[h],cB[h])):
            for j,(a,b) in enumerate(zip(ra,rb)):
                if a!=b and not (isinstance(a,str) and a.startswith('Exportado el')): difs+=1; print("DIF",h,i+1,j+1,repr(a),repr(b)) if difs<=15 else None
        if len(cA[h])!=len(cB[h]): print("filas distintas en",h,len(cA[h]),len(cB[h])); difs+=1
    print("celdas distintas:",difs)
    shutil.rmtree(tmp,ignore_errors=True)
