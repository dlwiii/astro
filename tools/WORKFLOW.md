# Astro Workflow

## Directory Structure (Hybrid Archive System)

```
~/astro/
├── sessions/                 # Raw data organized by date (local)
│   ├── 2026-01-19/
│   │   ├── m1/
│   │   │   ├── m1/          # Stacked files from telescope
│   │   │   └── m1_sub/      # Individual light frames
│   └── 2026-02-04/
│       └── c5/
│           ├── c5/
│           └── c5_sub/
├── targets/                  # Working view + final outputs
│   ├── galaxies/
│   │   └── c5/
│   │       ├── 2026-02-04 -> ../../../sessions/2026-02-04/c5  (symlink)
│   │       ├── c5_2026-02-04.png         # Final processed output
│   │       └── C_5_316x10sec_*.fit       # Custom stacks
│   ├── nebulae/
│   ├── clusters/
│   ├── solar_system/         # planets, Moon, Sun (added 2026-10-03)
│   └── stars/                # single/double stars, asterisms (M40, M73)
├── gallery/                  # Published website (git repo)
│   ├── index.html
│   ├── all_targets.html
│   └── targets/              # Final images (symlinks)
├── seestar_s30/
│   └── raw/                  # Temporary import staging (keep empty)
└── scripts/
    ├── import_sessions.py  # Import from Seestar device
    ├── archive_session.sh          # Archive old sessions to durin.local
    └── reorganize_to_hybrid.py     # One-time reorganization (done)

Remote Archive (durin.local):
~/durin/astro_archive/
└── sessions/                 # Archived old sessions
    ├── 2025-12-25/
    └── 2025-12-26/
```

## Image Naming Convention

The build script automatically finds the best image for each object:

**Priority 1 (Final processed images):**
- Format: `M##_YYYY-MM-DD.png`
- Example: `M31_2026-01-30.png`
- If multiple dates exist, uses the most recent

**Priority 2 (Fallback - auto-stacked images):**
- Format: `Stacked_###_M ##_*.jpg`
- Example: `Stacked_166_M 1_10.0s_LP_20260119-211436.jpg`
- Uses the image with the highest stack count

## Workflow

### 1. Capture and Process Images
Work in `~/astro/targets/` as usual with SIRIL, etc.

Save your final processed images as: `M##_YYYY-MM-DD.png`

### 2. Build and Update Gallery
When you have new images to publish:

```bash
cd ~/astro
python3 build_and_publish.py
```

This will:
- Generate HTML files in `gallery/`
- Copy only displayed images to `gallery/targets/`

### 3. Publish to GitHub
```bash
cd ~/astro/gallery
git add .
git commit -m "Add new Messier objects"
git push
```

Site will update at: https://dlwiii.github.io/astro/

## What Gets Published

**Published (in git):**
- `gallery/` directory only
- HTML files
- Final processed images referenced in HTML
- README.md

**NOT published (working files):**
- Everything else in `~/astro/`
- Raw light frames, darks, flats
- SIRIL processing files
- Seestar downloads
- Build scripts (they stay local)

## Notes
- Work freely in `~/astro` - only `gallery/` is published
- The build script automatically finds and copies used images
- No need to manually manage what goes to the website
- Your raw data stays private and local

---

## Importing from Seestar

### Mount Seestar Device
```bash
# Device auto-mounts at: /media/dlwiii/Seestar/MyWorks
```

### List Available Targets
```bash
cd ~/astro
python3 scripts/import_sessions.py
```
Shows all targets on Seestar with session dates and file counts.

### Import a Target
```bash
python3 scripts/import_sessions.py "M 31"
```

**What happens:**
1. Copies raw files directly to `sessions/YYYY-MM-DD/[target]/` (one folder per session date)
2. Creates hard links in `targets/[category]/[target]/YYYY-MM-DD/`
3. Space-efficient: files aren't duplicated

---

## Archiving to durin.local

### Mount durin.local
```bash
# One-time setup (if not already done)
sudo apt install sshfs
mkdir -p ~/durin
sshfs dlwiii@durin.local:/mnt/media2 ~/durin

# Auto-mount on boot (optional)
echo "dlwiii@durin.local:/mnt/media2 /home/dlwiii/durin fuse.sshfs defaults,_netdev 0 0" | \
  sudo tee -a /etc/fstab
```

**durin.local storage:**
- `/mnt/media` - 916G (178G used, 692G free)
- `/mnt/media2` - 916G (nearly empty) ← **archive location**

### Archive Old Sessions

**List available sessions:**
```bash
cd ~/astro
./scripts/archive_session.sh
```

**Archive one or more sessions:**
```bash
# Archive single session
./scripts/archive_session.sh 2025-12-25

# Archive multiple sessions
./scripts/archive_session.sh 2025-12-25 2025-12-26 2025-12-27
```

**What happens:**
1. Copies session to `~/durin/astro_archive/sessions/YYYY-MM-DD/`
2. Verifies transfer completion
3. Removes local copy from `sessions/`
4. Removes broken symlinks from `targets/`
5. **Keeps final outputs** (PNGs, processed stacks) in `targets/`

**Strategy:**
- Keep recent sessions local (last 30-60 days) for active processing
- Archive old sessions to durin.local
- Final processed images always stay local

### Manual Archive with rsync (faster)
For better performance, use direct rsync:

```bash
# Via SSHFS mount (works but slower)
rsync -avh --info=progress2 \
  ~/astro/sessions/2025-12-25/ \
  ~/durin/astro_archive/sessions/2025-12-25/

# Direct SSH (fastest - requires SSH key setup)
rsync -avzh --progress \
  ~/astro/sessions/2025-12-25/ \
  dlwiii@durin.local:/mnt/media2/astro_archive/sessions/2025-12-25/
```

### Restore Archived Session
If you need to process archived data:

```bash
# Copy session back from durin
rsync -avh ~/durin/astro_archive/sessions/2025-12-25/ \
  ~/astro/sessions/2025-12-25/

# Recreate symlinks
cd ~/astro/targets/[category]/[target]
ln -s ../../../sessions/2025-12-25/[target] 2025-12-25
```

---

## Data Management Summary

**Workflow:**
1. **Capture** → Seestar device
2. **Import** → directly into `sessions/YYYY-MM-DD/` + hard links in `targets/`
3. **Process** → Work with sessions via symlinks in `targets/`
4. **Final outputs** → Save as `[target]_YYYY-MM-DD.png` in `targets/[category]/[target]/`
5. **Archive** → Move old sessions to `durin.local`
6. **Publish** → Gallery shows final outputs only

**Space Management:**
- Delete intermediate processing folders (`process/` dirs) regularly
- Archive sessions older than 30-60 days
- Keep all final outputs locally
- Current setup: ~25GB sessions, ~44GB targets, ~240GB free
