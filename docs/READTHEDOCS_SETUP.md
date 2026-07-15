# Read the Docs — one-time setup

AgentGuard ships Sphinx config (`.readthedocs.yaml`, `docs/source/`). The site is **not live** until you import the repo on Read the Docs.

**Target URL:** https://inter-agent-guard.readthedocs.io/

---

## Prerequisites (already done in repo)

- [x] `.readthedocs.yaml` at repository root
- [x] `docs/requirements.txt` (Sphinx + theme + myst-parser)
- [x] `docs/source/` (`index.rst`, `quickstart.md`, `latency.md`, `api.rst`, `conf.py`)
- [x] Local build verified: `sphinx-build -b html docs/source docs/_build/html`

---

## Step 1 — Import on Read the Docs (~5 minutes)

1. Open **https://readthedocs.org/dashboard/import/**
2. Sign in with **GitHub** (account that can access `nizba06/agentguard`).
3. Click **Import a Project** → select **`nizba06/agentguard`**.
4. On the project settings page, set:
   - **Name / slug:** `inter-agent-guard`  
     (URL becomes `https://inter-agent-guard.readthedocs.io/`)
   - **Default branch:** `master` (or `main` if that is your default)
5. Under **Advanced settings** (optional but recommended):
   - **Documentation type:** Sphinx
   - **Configuration file:** `.readthedocs.yaml` (RTD should auto-detect)
6. Save → **Build version** → wait for a **green** build (first build may take 5–10 minutes while pip installs `inter-agent-guard` for autodoc).

### If the slug is wrong

- Admin → **Settings** → change slug to `inter-agent-guard`
- Or delete the project and re-import with the correct slug

### If the build fails

Common fixes:

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: agentguard` | Ensure `.readthedocs.yaml` has `python.install` with `path: .` |
| Sphinx warnings as errors | `fail_on_warning: false` is already set in `.readthedocs.yaml` |
| Missing theme | `docs/requirements.txt` includes `sphinx-rtd-theme` |

Reproduce locally before retrying:

```powershell
py -3.12 -m pip install -r docs/requirements.txt .
py -3.12 -m sphinx -b html docs/source docs/_build/html
```

---

## Step 2 — Verify the site is live

Open these (should return **200**, not 404):

- https://inter-agent-guard.readthedocs.io/
- https://inter-agent-guard.readthedocs.io/en/latest/quickstart.html
- https://inter-agent-guard.readthedocs.io/en/latest/api.html

---

## Step 3 — Repo already points here

After import, these files use the RTD URL as the canonical docs home:

- `pyproject.toml` → `documentation = "https://inter-agent-guard.readthedocs.io/"`
- `README.md`, `docs/BLOG_POST.md`, `docs/source/quickstart.md`

No further URL churn needed unless you change the RTD slug.

---

## Links to use in social posts

### After RTD is live (preferred)

| Resource | URL |
|----------|-----|
| **Docs home** | https://inter-agent-guard.readthedocs.io/ |
| **Quick start** | https://inter-agent-guard.readthedocs.io/en/latest/quickstart.html |
| **Latency guide** | https://inter-agent-guard.readthedocs.io/en/latest/latency.html |
| **API reference** | https://inter-agent-guard.readthedocs.io/en/latest/api.html |
| **PyPI** | https://pypi.org/project/inter-agent-guard/ |
| **Demo** | https://github.com/nizba06/inter-agent-guard-demo |
| **GitHub** | https://github.com/nizba06/agentguard |
| **Dataset** | https://huggingface.co/datasets/Nizba/agentguard-benchmark-v1 |

### Until RTD is live (fallback)

| Resource | URL |
|----------|-----|
| Quick start (GitHub) | https://github.com/nizba06/agentguard/blob/master/docs/source/quickstart.md |
| Blog | https://github.com/nizba06/agentguard/blob/master/docs/BLOG_POST.md |
| PyPI | https://pypi.org/project/inter-agent-guard/ |
| Demo | https://github.com/nizba06/inter-agent-guard-demo |

---

## Step 4 — Optional: PyPI metadata refresh

`pyproject.toml` already lists the RTD URL. To refresh PyPI project links after RTD is live, publish a patch (e.g. `1.0.1`) or use the PyPI web UI **Manage project → Project links** if you prefer not to cut a release.

---

## Webhook (automatic rebuilds)

RTD usually adds a GitHub webhook on import. Confirm:

- GitHub repo → **Settings** → **Webhooks** → Read the Docs webhook present
- Each push to `master` triggers a new docs build
