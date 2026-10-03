# tools/

Scripts and reference data for the astro workflow. The live tree is `~/astro`
(`/mnt/media2/astro`); this repo is its `gallery/` subfolder, published by
GitHub Pages. `~/astro/scripts` is a symlink to this folder, and
`~/astro/targets/CATALOG.md`, `CALDWELL.md` and `caldwell.json` are symlinks
into `catalog/`.

Raw frames (`*.fit`) and processing output never go in the repo; see
`.gitignore`. See `WORKFLOW.md` for the capture → import → process → publish
flow and the Seestar import/cleanup commands.

| Script | Purpose |
|---|---|
| `import_sessions.py` | Import a target from the mounted Seestar into `sessions/` + `targets/` |
| `clean_seestar_device.sh` | Report and (on confirm) delete fully backed-up `_sub` folders from the Seestar |
| `build_and_publish.py` | Regenerate the gallery HTML and copy referenced images |
| `process_target.sh` | Siril processing pipeline for one target |
| `build_caldwell_mapping.py`, `fetch_caldwell_wikipedia_links.py` | Regenerate `catalog/caldwell.json` and `CALDWELL.md` |
| `archive_session.sh` | Archive old sessions to another host |

Scripts locate the astro root by walking up from their real path to the directory
holding `sessions/` and `targets/`; set `ASTRO_DIR` to override.
