# Step 0 — Rename Repo: `dqar-aidbox` → `dqar-aidbox-databricks-kit`

> **Run this block FIRST, before any other work in this instruction file.**
> It renames the repository folder and updates every reference in a single,
> history-preserving commit. Do not `mv` the folder by hand beforehand — this
> block owns the rename end-to-end so the reference updates stay in sync.

---

## Decision to confirm before you start

This block renames **two distinct things**. Confirm which scope applies:

| Thing | Old | New | Default |
|---|---|---|---|
| Repo / folder name | `dqar-aidbox` | `dqar-aidbox-databricks-kit` | **Rename** |
| Importable Python package | `dqar_aidbox` | `dqar_aidbox_databricks_kit` | **Keep short** (`dqar_aidbox`) unless told otherwise |

**Default behavior:** rename the repo/folder to the long name, but keep the
importable package short (`dqar_aidbox`) for ergonomics. If the package import
must also change, the user will say so explicitly — otherwise do NOT rename the
package directory or rewrite import statements.

---

## Pre-flight checks (abort if any fail)

```bash
# 1. Confirm you are in the repo root and it is the OLD name
basename "$PWD"          # expect: dqar-aidbox
test -f pyproject.toml   # expect: exists

# 2. Confirm clean git state — no uncommitted work to lose in the rename
git status --porcelain   # expect: empty output

# 3. Confirm you are on a fresh working branch, not main/master
git rev-parse --abbrev-ref HEAD   # expect: rename/aidbox-databricks-kit (create if needed)
```

If git status is not clean, STOP and report. Do not rename over uncommitted changes.

Create the branch if it does not exist:

```bash
git checkout -b rename/aidbox-databricks-kit
```

---

## Step 0.1 — Rename the folder with history preserved

From the **parent** directory of the repo:

```bash
cd ..
git -C dqar-aidbox mv -k . . 2>/dev/null || true   # no-op guard
# Folder-level rename (history preserved at the VCS level via the move commit):
mv dqar-aidbox dqar-aidbox-databricks-kit
cd dqar-aidbox-databricks-kit
```

> Note: a plain `mv` on the top-level folder is correct here because the folder
> itself is not tracked by its parent's git — the repo root is the boundary.
> History inside the repo is fully preserved. Use `git mv` only for tracked
> paths *inside* the repo (Step 0.3), never for the repo root folder itself.

---

## Step 0.2 — Inventory every reference to the old name

Before changing anything, capture the full reference list so nothing is missed:

```bash
grep -rIn --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv \
  -e 'dqar-aidbox' -e 'dqar_aidbox' . | tee /tmp/rename-references.txt
wc -l /tmp/rename-references.txt
```

Read `/tmp/rename-references.txt` and classify each hit:
- **Folder/repo-name references** (`dqar-aidbox`) → update to `dqar-aidbox-databricks-kit`
- **Package-import references** (`dqar_aidbox`) → **leave unchanged** under the default scope above

---

## Step 0.3 — Update repo-name references (NOT package imports)

Apply only to the hyphenated repo name. Do these explicitly; do not blanket-replace.

Files that almost always reference the repo name:

```
pyproject.toml          # [project] name = "dqar-aidbox" → "dqar-aidbox-databricks-kit"
README.md               # title, clone URL, badges, install snippet
.github/workflows/*.yml # any path or cache key containing dqar-aidbox
CHANGELOG.md            # header references
docs/*.md               # cross-references to the repo by name
```

Targeted replace (review each diff before staging):

```bash
# pyproject.toml — project name only
sed -i 's/^name = "dqar-aidbox"/name = "dqar-aidbox-databricks-kit"/' pyproject.toml

# README + docs + workflows — repo-name string only (hyphenated form)
grep -rIl --exclude-dir=.git 'dqar-aidbox' README.md docs .github 2>/dev/null \
  | xargs -r sed -i 's/dqar-aidbox\b/dqar-aidbox-databricks-kit/g'
```

> The `\b` word boundary prevents double-renaming a string that already reads
> `dqar-aidbox-databricks-kit`. Re-run the Step 0.2 grep after this to confirm no
> stray `dqar-aidbox` (without the suffix) remains except intentional ones.

---

## Step 0.4 — Update the `dqar-contracts` dependency pin (if present)

The dependency on the shared contracts package does not change name, but confirm
the pin is intact after the edits:

```bash
grep -n 'dqar-contracts' pyproject.toml
# expect: dqar-contracts>=1.0.0,<2.0.0  (unchanged)
```

---

## Step 0.5 — Update downstream cross-repo references

The other repos may reference this one by its old folder name (CI matrices,
integration-test paths, docs). Within this repo, fix any self-references; for the
sibling repos (`dqar-client-kit`, `dqar-contracts`), record what needs updating so
the user can run the corresponding instruction file there:

```bash
# Self-references inside this repo only:
grep -rIn --exclude-dir=.git 'dqar-aidbox\b' . | tee /tmp/rename-residual.txt
# Expect: empty after Step 0.3. If non-empty, fix or justify each line.
```

> Do NOT reach into sibling repo folders from this instruction file. If
> `/tmp/rename-residual.txt` reveals references that live in other repos, list
> them in the final report so the user runs the matching rename step there.

---

## Step 0.6 — Verify, then commit as a single rename commit

```bash
# Package still imports (default scope: package name unchanged)
python -c "import dqar_aidbox; print('import OK')" 2>&1 || \
  echo "Import check skipped or failed — confirm package scope decision"

# Project metadata reflects the new name
grep '^name = ' pyproject.toml   # expect: dqar-aidbox-databricks-kit

# No stray old-name references remain
test ! -s /tmp/rename-residual.txt && echo "No residual references ✓"

# Stage and commit everything as ONE atomic rename commit
git add -A
git commit -m "chore: rename repo dqar-aidbox → dqar-aidbox-databricks-kit

- Folder renamed (history preserved)
- Updated project name in pyproject.toml
- Updated README, docs, and CI workflow references
- Importable package name unchanged (dqar_aidbox)
- dqar-contracts dependency pin unchanged"
```

---

## Step 0.7 — Report before proceeding

Output a short summary and then continue to the rest of this instruction file:

```
RENAME COMPLETE
  Folder:    dqar-aidbox → dqar-aidbox-databricks-kit
  Package:   dqar_aidbox (unchanged)
  Files touched: <N>
  Residual cross-repo references to fix elsewhere: <list or "none">
```

Only after this report is clean do you proceed to the aidbox-databricks-kit
implementation phases below.
