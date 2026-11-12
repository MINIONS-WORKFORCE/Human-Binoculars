# Nguyên: Science + spectra

What goes here: 5-target table from SIMBAD, proper-motion propagation, expected-results table, spectrum extraction, light curves.

- Work on a branch named `nguyen/<task>` and open a small PR.
- Notebooks: clear outputs before committing (`nbstripout` does it automatically once installed).
- Never commit FITS files, cutouts or databases; put them in `data/` (gitignored) or on the team drive.
- Code that a teammate will import goes in `shared/`, not here.

## Issue #36 — 11/11/2026

Current delivery and exact acceptance limits: [ISSUE36_HANDOFF.md](ISSUE36_HANDOFF.md).
Use [ISSUE36_PR.md](ISSUE36_PR.md) when submitting after your own rebase.

```powershell
python -m pytest members/nguyen/tests -q
python members/nguyen/build_samples.py
python members/nguyen/issue36.py data/science_acceptance_mock/rdra-manifest.json --output data/issue36/rdra
python members/nguyen/issue36.py data/science_acceptance_mock/barnard-manifest.json --output data/issue36/barnard
```

Shared imports: `from shared.science import photometry, astrometry`.
Default dictionary-target calls return API 0.1 fields. `diagnostics=True` retains
quality/provenance metadata; pass that option when porting older science notebooks.
Mock/real tables are separate under `evidence/issue36/`. No FITS is committed.
