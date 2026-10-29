# Install guide

You need: a purchased USSA Vault Modular package, Python 3.9+, a modern browser (Chrome, Edge or Brave for the direct "Build to a folder" option; any browser for the zip), and about as much free disk space as the package (roughly 23 GB, see below).

## 1. Get the code
```
git clone https://github.com/DigitalRoadi3s/VaultBox.git
cd VaultBox
```

## 2. Create the `parts/` folder
`parts/` is not in the repository. It must be a copy of the package's STL tree with the **same folder and file names**, because the catalog is built from those paths.

```
mkdir parts
```

Your source package should look like this (the folder name may carry a date prefix such as `261020_VAULT_USSA`):

```
<source package>/
  01. DRAWERS/        01. S Families, 02. M Families, 03. L Families, 04. L² Families,
                      05. XL Families, 06. XL² Families, 07. Universal
  02. SUSTAINERS/     01. S Families ... 04. XL Families, 05. Universal
  03. MODIFICATIONS/  Backbone, Base, Feet, Pegboard Attachment, Pull-out Handle,
                      Stationary Handle, Wall Mounts, Wheels
  01_Instructions Manual.pdf ... 05_Mounting Instructions.pdf   (not needed here)
```

Copy the three numbered folders into `parts/` so you end up with `parts/01. DRAWERS/`, `parts/02. SUSTAINERS/`, `parts/03. MODIFICATIONS/`.

**macOS / Linux (recommended, copies only the STLs, keeps the tree):**
```
SRC="/path/to/261020_VAULT_USSA"
rsync -a --include='*/' --include='*.stl' --exclude='*' "$SRC/" parts/
```
Add `--prune-empty-dirs` if you want to skip empty folders.

**Windows (PowerShell):**
```
$SRC = "C:\path\to\261020_VAULT_USSA"
robocopy $SRC parts *.stl /E
```

**Or by hand:** copy the folders `01. DRAWERS`, `02. SUSTAINERS` and `03. MODIFICATIONS` into `parts/` in your file manager. Do not rename, flatten or merge anything. Keep the `²` characters in `L² Families` and `XL² Families`.

Notes:
- Do not use symlinks if you plan to run the site from a synced folder; copy real files.
- Do not commit `parts/`. It is in `.gitignore`.
- The package is large (about 723 STLs, ~23 GB). If disk space is tight, you can symlink `parts` to the package location instead: `ln -s "/path/to/261020_VAULT_USSA" parts` (macOS/Linux). The folder names inside must match the layout above.

Check the copy:
```
find parts -name '*.stl' | wc -l      # expect 723 for the 261020 package
ls parts
```
A different package version may have a different count. If the counts differ, run step 3 and read any "MISSING referenced files" lines.

## 3. Generate the catalog
```
python3 tools/build_catalog.py
```
Expect `variants: 50 -> .../data/catalog.json`. Any `MISSING referenced files` lines mean a file name differs from what the rules expect; fix the copy or adjust `tools/build_catalog.py`.

## 4. Generate thumbnails (recommended)
```
python3 -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 tools/render_thumbs.py
```
This writes `assets/thumbs/` (one PNG per STL, takes a minute or two on 8 cores). It skips existing files, so it is safe to rerun. Without thumbnails the part cards show blank images.

## 5. Optional: manual images
`assets/manual/` can hold images cropped from the manual's pages (names such as `use_mounted.png`, `roof_table.png`, `interior_flat_sustainer.png`, `size_S.png`, `type_drawers.png`). They are used on the option cards and the side panel, and they come from the paid manual, so they are not shipped. If a file is missing, the site falls back to the STL render. Create them yourself from your own PDFs if you want them.

## 6. Run
```
./serve.sh
```
Open <http://localhost:8765/>. Opening `index.html` directly does not work because the page has to fetch the STL files over HTTP. On Windows, run `python -m http.server 8765 --bind 127.0.0.1` in the repository folder.

## 7. Build a project
Pick vaults, add them to the project, open **Project**, enter a name and press **Build**. You get `<name>.zip` containing a folder with the STLs (prefixed `01_`, `02_` per module), `BOM.txt` and `Hardware.txt`. Chromium browsers also offer **Build to a folder...**, which writes straight to a folder you pick (use `~/Downloads`) and adds a numeric suffix if the name is taken.

## Troubleshooting
| Symptom | Cause / fix |
| --- | --- |
| "Could not load data/catalog.json" | Run step 3, and serve over HTTP (step 6) |
| Empty or grey part cards | Run step 4 |
| Build fails with `fetch failed (404)` | A file in `parts/` is missing or renamed; recopy it exactly |
| Zip build error about 4 GB | Use "Build to a folder..." |
| `MISSING referenced files` in step 3 | Package version differs; compare names to the layout above |
