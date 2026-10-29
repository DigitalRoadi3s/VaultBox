# VaultBox

A dark, responsive web configurator for the **USSA Vault Modular** 3D-printable storage system. Pick a vault (50 variants), pick how it will be used, choose interiors, roofs, facades, locks and mounting options, add more vaults to build a stack, name the project and press **Build**. You get a folder of just the STL files you need plus a `BOM.txt` and a `Hardware.txt` (for example `x4 M4 14 mm bolt`).

> **This repository contains no USSA files.** The STL models, manual pages and images are a paid product and cannot be shared. You need your own purchased copy. See [INSTALL.md](INSTALL.md) to set up the `parts/` folder from your package. This project is unofficial and is not affiliated with or endorsed by USSA Design.

## What it covers
- Drawers: S, M, L, L², XL, XL² families, depths 3 to 7
- Sustainers: S, M, L, XL families, depths 3 to 7
- Usage modes: mounted, stationary, mobile, portable, under table (only options that fit the chosen size and mode are shown)
- Interiors, roof types, facades, key locks, springs, latch, runner slides and guides, geared rails, facade and key caps, bases, backbones, wall mounts, pegboard attachments, feet, handles, wheel kits
- Hardware list from the manual's counts; anything the manual does not quantify is shown as `qty not in manual`

## Quick start
1. Follow [INSTALL.md](INSTALL.md) (creates `parts/`, generates the catalog and thumbnails).
2. `./serve.sh` and open <http://localhost:8765/>.
3. Build downloads `<Project name>.zip`. In Chromium browsers "Build to a folder..." writes the folder straight to a directory you choose, such as `~/Downloads`.

## Repository layout
| Path | Purpose | In git |
| --- | --- | --- |
| `index.html`, `app.js`, `style.css` | The web app (vanilla JS, no dependencies) | yes |
| `tools/build_catalog.py` | Builds `data/catalog.json` from `parts/`; all option rules live here | yes |
| `tools/render_thumbs.py` | Renders a preview PNG for every STL | yes |
| `serve.sh` | Local web server on port 8765 | yes |
| `parts/` | Your STL files from the purchased package | **no** (gitignored) |
| `assets/thumbs/` | Renders generated from your STLs | **no** |
| `assets/manual/` | Optional images cropped from the manual | **no** |
| `data/catalog.json` | Generated catalog | **no** |

## Notes and limits
- Quantities come only from the manual's hardware list and assembly pages. Check them against your copy.
- L² and XL² families ship modules only; their box, roof and baseplate are taken from the same letter and depth family and flagged in the UI. Verify fit.
- The zip is store-only without Zip64, so a build over 4 GB must use "Build to a folder...".
- Without `assets/manual/` the site falls back to STL renders; the usage-mode cards show a plain icon.
