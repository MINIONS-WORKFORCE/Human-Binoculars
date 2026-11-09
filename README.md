# spaceapps-training

Training repo for **NASA Space Apps 2026: SPHEREx Sky Viewer** (3–13/11).

Daily assignments are tracked in [GitHub Issues](https://github.com/MINIONS-WORKFORCE/Human-Binoculars/issues).
Read the [team collaboration guide](docs/team/README.md) for the Issue-to-PR
workflow, module handoffs and the current API sources.

> This is the **training** repo. The competition repo is created fresh at hour 0 on 14/11; do not copy code from here into it.

## Layout

```
members/<name>/      your own experiments, notebooks, scripts (one folder per person)
shared/              things others depend on: API contract, targets, data layout
templates/vite-react starter for React + Vite pages (copy into your member folder)
scripts/check_env.py checks that your machine is ready
data/                local only, gitignored: fixture packs from the drive go here
docs/team/           collaboration workflow and handoff guides
```

| Folder | Person | Role |
| --- | --- | --- |
| `members/thach` | Thạch | Frontend B + UI/UX + coordination |
| `members/duy-hoang` | Duy Hoàng | Frontend A + DevOps + testing (repo owner) |
| `members/dong` | Đông | Backend API + cache |
| `members/khoi` | Khôi | IRSA data + database |
| `members/huu-hoang` | Hữu Hoàng | Image processing |
| `members/nguyen` | Nguyên | Science + spectra |

## Setup (about 15 minutes)

You need: **Python 3.12**, **Node 24 LTS** (22.12+ also works), **Git**.

- Python 3.11 will NOT work: current numpy, scipy and photutils require 3.12+.
- Node 20 will NOT work: Vite 8 / Vitest 5 need 22.12+.

```bash
git clone https://github.com/MINIONS-WORKFORCE/Human-Binoculars.git
cd Human-Binoculars

# 1. Python virtual environment
py -3.12 -m venv .venv            # macOS/Linux: python3.12 -m venv .venv
.venv\Scripts\Activate.ps1        # Git Bash: source .venv/Scripts/activate
                                  # macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# 2. Strip notebook outputs automatically on commit (run once per clone)
nbstripout --install

# 3. Local config
cp .env.example .env              # PowerShell: Copy-Item .env.example .env

# 4. Frontend packages
npm install

# 5. Check everything
python scripts/check_env.py --online
npm run dev:starter               # opens the starter page at http://localhost:5173
```

**Done when** `check_env.py --online` prints `READY: environment OK`. Post that line in the team chat.

## Daily workflow

1. Read the assigned GitHub Issue, its acceptance criteria and current API wiki.
2. Check `git status`. From a clean worktree, run `git switch main` and `git pull --ff-only origin main`.
3. Create `<your-folder>/<task>`, e.g. `dong/issue-14-api-contract-fixture`.
4. Work inside `members/<you>/`. Code someone else imports goes to `shared/`.
5. Open a small PR using the template and link the Issue. Duy Hoàng merges; `main` must always run.
6. Hand off by the Issue's deadline, and before 22:30 for the daily handoff, with a link and reproducible instructions.

Blocked for more than 30 minutes: open a **Blocked** issue (template provided),
link the original task and switch to another assigned Issue or available backlog item.

## Rules

- **Never commit** `.fits`, cutouts, `.db`/`.sqlite`, or `.env`. `.gitignore` blocks them; fixture packs live on the team drive.
- Adding a Python or npm package = a PR that changes `requirements.txt` or `package.json` + `package-lock.json`. Use `npm install <pkg>` so the lockfile updates.
- Notebook outputs are stripped on commit by `nbstripout`. If you need to share a plot, save it as a PNG and attach it to the PR.

## Editor

Any editor works; formatting is enforced by `.editorconfig`, Ruff (Python) and Prettier (JS). **VS Code is recommended**: opening the folder prompts you to install the extensions in `.vscode/extensions.json` (Python, Jupyter, Ruff, Prettier), and format-on-save is already configured.

```bash
ruff check . && ruff format .     # Python
npm run format                    # JS/JSX
npm test                          # Vitest
```

## Data notes

- SIA2 collections: `spherex_qr3`, `spherex_qr3_deep`, `spherex_qr2`, `spherex_qr2_deep`. The name is read from `.env`.
- As of 3/11, `spherex_qr3` returns **0** images at WISE 0855 while `spherex_qr2` returns 256 (MJD 60800–61174, about May 2025 to May 2026). Query both collections, not QR3 alone.
- Always use cutouts (`access_url` + `?center=ra,dec&size=deg`), never full files (hundreds of MB each).

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `Activate.ps1 cannot be loaded because running scripts is disabled` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then retry |
| `py -3.12` not found | Install Python 3.12 from python.org and tick "Add to PATH" |
| `pip install` fails building a package | Check `python --version` inside the venv is 3.12; delete `.venv` and recreate |
| `npm install` engine warning | Upgrade Node to 24 LTS (`nvm install 24` / `nvm use 24`) |
| `check_env.py --online` IRSA FAIL | Network/firewall or IRSA down; retry later or on 4G, the library check is what matters today |
