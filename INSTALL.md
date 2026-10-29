# Install guide (Docker)

VaultBox runs in a container that serves the site. The paid USSA STL files are **not** in the image or the repository: you mount your own copy at runtime. You need a purchased USSA Vault Modular package, Docker with Compose v2, and disk space for the package (about 23 GB).

## 1. Install Docker

**Linux:** install Docker Engine and the Compose plugin from <https://docs.docker.com/engine/install/> (Ubuntu/Debian: package `docker-ce` plus `docker-compose-plugin`). Optional: `sudo usermod -aG docker $USER` and log in again, otherwise prefix commands with `sudo`. Check with `docker compose version`.

**macOS:** install Docker Desktop <https://docs.docker.com/desktop/setup/install/mac-install/> (or Colima + `brew install docker docker-compose`). Start it. Your home folder is shared with containers by default.

**Windows 10/11:** install Docker Desktop <https://docs.docker.com/desktop/setup/install/windows-install/> with the WSL 2 backend, and start it. Use PowerShell for the commands below. Install Git from <https://git-scm.com/download/win> or download the repository as a zip.

## 2. Get the code
```
git clone https://github.com/DigitalRoadi3s/VaultBox.git
cd VaultBox
```

## 3. Create the parts folder
The STL tree must keep the **same folder and file names** as the package, because the catalog refers to those paths. After copying you should have:
```
parts/
  01. DRAWERS/        01. S Families ... 07. Universal   (keep the ² in "L² Families" and "XL² Families")
  02. SUSTAINERS/     01. S Families ... 05. Universal
  03. MODIFICATIONS/  Backbone, Base, Feet, Pegboard Attachment, Pull-out Handle,
                      Stationary Handle, Wall Mounts, Wheels
```
The package's PDFs are not needed. Copy only the three numbered folders (STL files only is fine). Do not rename, flatten or merge anything.

**Linux / macOS**
```
mkdir parts
SRC="/path/to/261020_VAULT_USSA"
rsync -a --include='*/' --include='*.stl' --exclude='*' --prune-empty-dirs "$SRC/" parts/
```
**Windows (PowerShell)**
```
mkdir parts
$SRC = "C:\path\to\261020_VAULT_USSA"
robocopy $SRC parts *.stl /E
```
Or copy the three folders in your file manager.

Check (expect 723 for the 261020 package):
```
find parts -name '*.stl' | wc -l                                   # Linux / macOS
(Get-ChildItem parts -Recurse -Filter *.stl).Count                 # Windows PowerShell
```

**Short on disk space?** Skip the copy and point at the package where it already is, using `PARTS_DIR` in step 4. The folder you point at must directly contain `01. DRAWERS`, `02. SUSTAINERS` and `03. MODIFICATIONS`.

## 4. Configure (optional)
```
cp .env.example .env            # Windows: copy .env.example .env
```
Edit `.env`:
```
PARTS_DIR=./parts               # or an absolute path, e.g. /data/ussa  or  C:/Users/me/ussa
PORT=8765
```
On Windows use forward slashes in `PARTS_DIR`. The drive must be shared with Docker Desktop (Settings > Resources > File sharing, if not using WSL 2).

## 5. Start
```
docker compose up -d --build
```
Open <http://localhost:8765/>. Useful commands:
```
docker compose logs -f          # shows a WARNING if no .stl files were found in parts
docker compose ps               # STATUS should become "healthy"
docker compose down             # stop
git pull && docker compose up -d --build     # update
```

## 6. Build a project
Pick vaults, add them to the project, open **Project**, enter a name and press **Build**. You get `<name>.zip` with a folder of the STLs (prefixed `01_`, `02_` per module), `BOM.txt` and `Hardware.txt`. Chromium browsers also offer **Build to a folder...**, which writes straight to a folder you pick and adds a numeric suffix if the name is taken. Use **New project** to start over.

## Platform notes
| Platform | Note |
| --- | --- |
| Linux | If the container cannot read `parts`, make it world-readable: `chmod -R a+rX parts` (the container runs as UID 10001). On SELinux hosts (Fedora, RHEL) change the volume in `docker-compose.yml` to `...:/app/parts:ro,z`. |
| macOS | Folders outside your home need adding under Docker Desktop > Settings > Resources > File sharing. Bind-mounted reads can be slow with the older gRPC FUSE option; use VirtioFS. |
| Windows | Keep `parts` on the same drive as the repo or on a shared drive. Line endings: if the container fails with `exec ... no such file`, run `git config core.autocrlf false`, re-clone, and rebuild. |
| Remote host | The site is plain HTTP with no login. Do not expose the port to the internet; reach it over LAN/VPN. |

## Troubleshooting
| Symptom | Cause / fix |
| --- | --- |
| Page loads, Build fails with `fetch failed (404)` | `parts` is empty, mis-pointed or a file was renamed. Check `docker compose logs`. |
| Part cards show "no preview" | Thumbnails ship with the repo; rebuild the image (`--build`) after `git pull`. |
| Port already in use | Set `PORT=` in `.env`. |
| Zip build error about 4 GB | Use "Build to a folder...". |
| Changes not showing | Hard refresh (Ctrl/Cmd+Shift+R). |

## Maintainers: regenerating the catalog or thumbnails
Needs Python 3 on the host, not Docker: `python3 tools/build_catalog.py` (reads `parts/`), and `pip install -r requirements.txt && python3 tools/render_thumbs.py`. Then rebuild the image.
