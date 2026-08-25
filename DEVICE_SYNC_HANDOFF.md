# Cross-device work handoff

This repository is currently being used to move active work between devices. Both source CSVs are intentionally tracked with **Git LFS** during this interim period because each is about 123 MB and exceeds GitHub’s regular Git file limit.

## On a new device

1. Install Git LFS if needed: `git lfs install`.
2. Clone or pull `main`, then run `git lfs pull` to download `rokt_data.csv` and `raw_data/[AU] Rokt/rokt_hKllMfFFdA.csv`.
3. Work normally and commit/push the notebook, docs and data changes needed for the analysis.
4. Do not change the LFS/data-tracking policy until the owner explicitly asks for final portfolio/public cleanup.

## Final publishing warning

Adding an entry to `.gitignore` does **not** remove a file already committed or an existing LFS object. At final cleanup, use `git rm --cached <file>`, add the ignore rule, commit, and push. If the data is confidential, plan a separate history/LFS cleanup before making the repository public.

This note was added on 2026-08-25 to document the temporary device-sync policy for future AI assistance.
