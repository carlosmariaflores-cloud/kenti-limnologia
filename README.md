# Kenti Limnología

Free, open-source program for the routine analysis of freshwater community data, in Spanish, English and Portuguese. It runs on your own computer (no installation, no internet, no account) and covers phytoplankton, periphyton, zooplankton, macroinvertebrates and fish: alpha and beta diversity, UPGMA, correlation and PCA, Nygaard quotients, BMWP′/ASPT′/ABI, CPUE, length–weight relationships, condition factors and a Karr-type index of biotic integrity. Results are exported to Excel.

Programa gratuito y de código abierto para el análisis rutinario de datos de comunidades de agua dulce, en español, inglés y portugués. Funciona en tu computadora, sin instalar nada y sin internet.

- DOI: [10.5281/zenodo.23349591](https://doi.org/10.5281/zenodo.23349591)
- Version: 0.6.1 · Licence: MIT · Author: Carlos María Flores (Atoj S.A.S., Tucumán, Argentina)
- Download the Windows executable from the *Releases* page (or build it yourself, below).
- Cite: see `CITATION.cff` and the article *Kenti Limnología: free, offline and trilingual software for the analysis of freshwater community data, with validation against independent implementations* (submitted).

## Build

Requires Go ≥ 1.21, Python 3 and Pillow.

```
./build.sh        # writes out/Kenti Limnología/{Kenti Limnologia.exe, kenti-linux}
```

Layout: `src/` module configurations and common template, `base/` pages of the modules with their own page, `i18n/` Spanish–English/Portuguese dictionaries, `launcher/` the Go program (standard library only), `prep.py` and `scripts/` assembly of the pages.

## Validation

`validation/` holds the scripts used in the article: each one opens the real program in Chromium (Playwright), pastes simulated data, exports the Excel workbook and compares every value with an independent NumPy/SciPy implementation, with fixed random seeds. Requires Python with `playwright`, `numpy`, `scipy`, `openpyxl`, `matplotlib`.

```
cd validation
export KENTI_EXE="../out/Kenti Limnología/kenti-linux"
python3 val_core.py zooplancton 24 41        # module, number of datasets, seed
python3 val_peces.py 30 4343
python3 val_nyg.py 30 7011 es
python3 val_lang.py zooplancton 12 8201 en
python3 val_peces_lang.py 1 101
python3 aggregate.py
```

Seeds used in the article are listed in its Table 2. `validation/results/` contains the raw logs and `summary.json`.

## Notes

The page template contains code for diatom indices that needs a user-supplied reference table; it is inactive in this distribution. The Portuguese texts were produced with machine assistance and have not been reviewed by a native speaker; corrections are welcome as issues or pull requests.
