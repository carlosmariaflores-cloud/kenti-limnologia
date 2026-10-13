#!/usr/bin/env python3
"""Arma launcher/web/ del Kenti Limnología a partir de las interfaces de cada módulo.

Uso: python3 prep.py <carpeta con las páginas base>
Cada módulo se declara en MODS (id, archivo, nombre, descripción). La página se
reescribe para vivir bajo /g/<id>/ (sus /api/ pasan a ser relativos) y se le
agrega una barra para volver al inicio.
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from plantilla_lib import render, inject_i18n   # módulos hechos con la plantilla común (config .json en src/)
SRC = Path(sys.argv[1])
OUT = Path(__file__).parent / "launcher" / "web"
MODS = {  # id: (archivo, nombre, descripción); un archivo .json es la configuración de un módulo de la plantilla común
 "macro": ("grupo_macro.json", "Macroinvertebrados",
   "Taxones por sitio con la familia completada sola, diversidad alfa y beta, PCA e índices bióticos (BMWP', ASPT' y ABI)."),
 "fitoplancton": ("grupo_fitoplancton.json", "Fitoplancton",
   "Taxones por sitio con diversidad alfa y beta, correlación y PCA, y cocientes de Nygaard."),
 "fitobentos": ("grupo_fitobentos.json", "Fitobentos",
   "Diatomeas y otras algas del bentos por sitio: diversidad alfa y beta, correlación y PCA."),
 "zooplancton": ("grupo_zooplancton.json", "Zooplancton",
   "Abundancia o densidad por taxón y sitio: diversidad alfa y beta, correlación con fisicoquímicos y PCA."),
 "peces": ("ictio-v0.2-index.html", "Peces",
   "Captura, CPUE o biomasa por especie y sitio: diversidad, tallas y condición, rasgos por especie e IBI."),
}
# Textos de la pantalla de inicio en inglés y portugués (clave: el texto en español)
HOME_T = {
 "en": {
  "Kenti Limnología": "Kenti Limnology",
  "Datos ecológicos de ambientes acuáticos en un solo lugar. Elegí con qué especialidad querés trabajar; cada una guarda sus datos por separado.": "Ecological data from aquatic environments in one place. Choose the specialty you want to work with; each one keeps its data separately.",
  "Especialidades": "Specialties", "Datos en": "Data in", "Abrir carpeta de datos": "Open data folder",
  "Datos guardados": "Data saved", "Sin datos todavía": "No data yet",
  "Macroinvertebrados": "Macroinvertebrates", "Fitoplancton": "Phytoplankton", "Fitobentos": "Phytobenthos", "Zooplancton": "Zooplankton", "Peces": "Fish",
  "Taxones por sitio con la familia completada sola, diversidad alfa y beta, PCA e índices bióticos (BMWP', ASPT' y ABI).": "Taxa per site with the family filled in automatically, alpha and beta diversity, PCA and biotic indices (BMWP', ASPT' and ABI).",
  "Taxones por sitio con diversidad alfa y beta, correlación y PCA, y cocientes de Nygaard.": "Taxa per site with alpha and beta diversity, correlation and PCA, and Nygaard quotients.",
  "Diatomeas y otras algas del bentos por sitio: diversidad alfa y beta, correlación y PCA.": "Diatoms and other benthic algae per site: alpha and beta diversity, correlation and PCA.",
  "Abundancia o densidad por taxón y sitio: diversidad alfa y beta, correlación con fisicoquímicos y PCA.": "Abundance or density per taxon and site: alpha and beta diversity, correlation with physicochemical variables and PCA.",
  "Captura, CPUE o biomasa por especie y sitio: diversidad, tallas y condición, rasgos por especie e IBI.": "Catch, CPUE or biomass per species and site: diversity, sizes and condition, traits per species and IBI.",
 },
 "pt": {
  "Kenti Limnología": "Kenti Limnologia",
  "Datos ecológicos de ambientes acuáticos en un solo lugar. Elegí con qué especialidad querés trabajar; cada una guarda sus datos por separado.": "Dados ecológicos de ambientes aquáticos em um só lugar. Escolha com qual especialidade quer trabalhar; cada uma guarda seus dados separadamente.",
  "Especialidades": "Especialidades", "Datos en": "Dados em", "Abrir carpeta de datos": "Abrir pasta de dados",
  "Datos guardados": "Dados salvos", "Sin datos todavía": "Ainda sem dados",
  "Fitoplancton": "Fitoplâncton", "Zooplancton": "Zooplâncton", "Peces": "Peixes",
  "Taxones por sitio con la familia completada sola, diversidad alfa y beta, PCA e índices bióticos (BMWP', ASPT' y ABI).": "Táxons por sítio com a família preenchida automaticamente, diversidade alfa e beta, PCA e índices bióticos (BMWP', ASPT' e ABI).",
  "Taxones por sitio con diversidad alfa y beta, correlación y PCA, y cocientes de Nygaard.": "Táxons por sítio com diversidade alfa e beta, correlação e PCA, e quocientes de Nygaard.",
  "Diatomeas y otras algas del bentos por sitio: diversidad alfa y beta, correlación y PCA.": "Diatomáceas e outras algas do bentos por sítio: diversidade alfa e beta, correlação e PCA.",
  "Abundancia o densidad por taxón y sitio: diversidad alfa y beta, correlación con fisicoquímicos y PCA.": "Abundância ou densidade por táxon e sítio: diversidade alfa e beta, correlação com variáveis fisicoquímicas e PCA.",
  "Captura, CPUE o biomasa por especie y sitio: diversidad, tallas y condición, rasgos por especie e IBI.": "Captura, CPUE ou biomassa por espécie e sítio: diversidade, tamanhos e condição, atributos por espécie e IBI.",
 },
}
TITULO = "Kenti Limnología"
FACES = """<style>
@font-face{font-family:"Public Sans";src:url(/fuentes/PublicSans-Regular.woff2) format("woff2");font-weight:400;font-display:swap}
@font-face{font-family:"Public Sans";src:url(/fuentes/PublicSans-Medium.woff2) format("woff2");font-weight:500;font-display:swap}
@font-face{font-family:"Public Sans";src:url(/fuentes/PublicSans-SemiBold.woff2) format("woff2");font-weight:600;font-display:swap}
@font-face{font-family:"Public Sans";src:url(/fuentes/PublicSans-Bold.woff2) format("woff2");font-weight:700;font-display:swap}
@font-face{font-family:"Source Serif 4";src:url(/fuentes/SourceSerif4-Roman.ttf) format("truetype");font-weight:200 900;font-style:normal;font-display:swap}
@font-face{font-family:"Source Serif 4";src:url(/fuentes/SourceSerif4-Italic.ttf) format("truetype");font-weight:200 900;font-style:italic;font-display:swap}
@font-face{font-family:"IBM Plex Mono";src:url(/fuentes/IBMPlexMono-Regular.woff2) format("woff2");font-weight:400;font-display:swap}
@font-face{font-family:"IBM Plex Mono";src:url(/fuentes/IBMPlexMono-Medium.woff2) format("woff2");font-weight:500;font-display:swap}
</style>
"""
BAR = """<div id="kt-bar" style="display:flex;align-items:center;gap:12px;padding:6px 16px;background:var(--surface-2,#eaeee5);border-bottom:1px solid var(--line,#dde2d6);font:500 13px/1.2 var(--sans,system-ui,sans-serif);color:var(--ink-2,#465040)"><a href="/" onclick="event.preventDefault();setTimeout(function(){location.href='/'},700)" style="color:var(--accent,#3d6b1c);text-decoration:none;font-weight:600">&larr; __TITULO__</a><span style="opacity:.6">/</span><span>%s</span></div>
"""
BAR = BAR.replace("__TITULO__", TITULO)
(OUT / "g").mkdir(parents=True, exist_ok=True)
for gid, (f, nombre, _d) in MODS.items():
    s = render(f) if f.endswith(".json") else inject_i18n((SRC / f).read_text(encoding="utf-8"), extra=("ictio",))
    n_api = len(re.findall(r'"/api/', s))
    s = s.replace('"/api/', '"api/')                       # relativo a /g/<id>/
    assert '/api/' not in s.replace('"api/', ''), gid
    s = s.replace("url(fuentes/", "url(/fuentes/").replace('href="icono.png"', 'href="/icono.png"')
    # fuentes que se incrustan al exportar figuras: ruta absoluta (relativa daría /g/<id>/fuentes/ → 404)
    s = s.replace("fetch(`fuentes/", "fetch(`/fuentes/")
    if "@font-face" not in s:
        s = s.replace("</head>", FACES + "</head>", 1)
    s, k = re.subn(r"<body[^>]*>", lambda m: m.group(0) + "\n" + BAR % nombre, s, count=1)
    assert k == 1, gid
    (OUT / "g" / f"{gid}.html").write_text(s, encoding="utf-8")
    print(gid, len(s), "api:", n_api)

cards = "\n".join(
  f'    <a class="card" data-g="{gid}" href="/g/{gid}/"><b>{n}</b><span class="d">{d}</span><span class="s" data-s="{gid}"><i></i>…</span></a>'
  for gid, (_f, n, d) in MODS.items())
# logo: el de la barra de Terrestre (mismo que usa el resto de Kenti)
logo = (Path(__file__).parent / "base" / "logo.txt").read_text().strip()
home = (Path(__file__).parent / "home.html").read_text(encoding="utf-8")
(OUT / "index.html").write_text(home.replace("__CARDS__", cards).replace("__LOGO__", logo).replace("__I18N__", json.dumps(HOME_T, ensure_ascii=False)), encoding="utf-8")
print("home ok")
