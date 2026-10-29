# VaultBox

A dark, responsive web configurator for the **USSA Vault Modular** 3D-printable storage system. Pick a vault (50 variants), pick how it will be used, choose interiors, roofs, facades, locks and mounting options, add more vaults to build a stack, name the project and press **Build**. You get a folder of just the STL files you need plus a `BOM.txt` and a `Hardware.txt` (for example `x4 M4 14 mm bolt`).

> **This repository contains no STL files.** The STL models are a paid product and cannot be shared. You need your own purchased copy. See [INSTALL.md](INSTALL.md) to set up the `parts/` folder from your package. This project is unofficial and is not affiliated with or endorsed by USSA Design.

## What it covers
- Drawers: S, M, L, L², XL, XL² families, depths 3 to 7
- Sustainers: S, M, L, XL families, depths 3 to 7
- Usage modes: mounted, stationary, mobile, portable, under table (only options that fit the chosen size and mode are shown)
- Interiors, roof types, facades, key locks, springs, latch, runner slides and guides, geared rails, facade and key caps, bases, backbones, wall mounts, pegboard attachments, feet, handles, wheel kits
- Hardware list from the manual's counts; anything the manual does not quantify is shown as `qty not in manual`

## Quick start (Docker)
1. Install Docker (see [INSTALL.md](INSTALL.md) for Linux, macOS and Windows).
2. Put your purchased STL folders in a `parts/` folder (or point `PARTS_DIR` at them).
3. `docker compose up -d --build`, then open <http://localhost:8765/>.
4. Build downloads `<Project name>.zip`. In Chromium browsers "Build to a folder..." writes the folder straight to a directory you choose, such as `~/Downloads`.

The image contains only the site. Your STLs are mounted read-only at runtime and never copied into the image.

## Repository layout
| Path | Purpose | In git |
| --- | --- | --- |
| `index.html`, `app.js`, `style.css` | The web app (vanilla JS, no dependencies) | yes |
| `tools/build_catalog.py` | (maintainers, needs Python 3) Builds `data/catalog.json` from `parts/`; all option rules live here | yes |
| `tools/render_thumbs.py` | (maintainers, needs Python 3 + numpy/Pillow) Renders a preview PNG for every STL | yes |
| `Dockerfile`, `docker-compose.yml`, `docker-entrypoint.sh`, `.env.example` | Container setup (site only, no STLs) | yes |
| `parts/` | Your STL files from the purchased package | **no** (gitignored) |
| `assets/thumbs/` | Preview renders of the parts (`tools/render_thumbs.py`) | yes |
| `assets/manual/` | Images cropped from the manual, plus assembly page images | yes |
| `data/catalog.json` | Generated catalog (`tools/build_catalog.py`) | yes |

## Notes and limits
- Quantities come only from the manual's hardware list and assembly pages. Check them against your copy.
- L² and XL² families ship modules only; their box, roof and baseplate are taken from the same letter and depth family and flagged in the UI. Verify fit.
- The zip is store-only without Zip64, so a build over 4 GB must use "Build to a folder...".
- Some manual crops (usage modes, sizes, roof types) were located automatically and are not all verified; the interior crops are the reliable ones. If a card shows the wrong picture, replace the file in `assets/manual/`.
