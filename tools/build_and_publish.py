#!/usr/bin/env python3
"""
Build Messier galleries and copy to publishing directory.
Reads from ~/astro/targets and outputs to ~/astro/gallery

Usage:
  build_and_publish.py              build, but refuse to write if objects would be lost
  build_and_publish.py --check      dry run: report what would change, write nothing
  build_and_publish.py --allow-removals   build even if objects disappear (use deliberately)
"""
import io
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, unquote

from PIL import Image

# Paths
WORK_DIR = Path('/home/dlwiii/astro')
GALLERY_DIR = WORK_DIR / 'gallery'
TARGETS_DIR = WORK_DIR / 'targets'

HTML_FILES = ['messier_catalog.html', 'messier_ra_chart.html', 'all_targets.html',
              'caldwell_catalog.html']

# Derivative images. The grid pages load one image per object, so pointing them at
# the full-size file meant a single page pulled the entire ~140 MB of the gallery.
# Every <img src> now gets a small thumbnail; click-to-zoom still opens the
# full-size image. Source files under targets/ are never modified.
THUMB_SUFFIX = '.thumb.webp'      # written next to the full-size file in gallery/
THUMB_MAX_EDGE = 500             # px, long edge
THUMB_QUALITY = 80

# PNGs are re-encoded to JPEG for publishing only, and only when that actually
# pays: the JPEG has to come in at or under this fraction of the PNG, otherwise
# the PNG is published as-is. Repo size is what pushed the Pages build into its
# 10-minute timeout (see the .nojekyll note in the repo history).
WEB_JPEG_MAX_RATIO = 0.8
WEB_JPEG_QUALITY = 95

# The generator scripts resolve Path('targets') relative to the current directory,
# so pin it. Without this, running from anywhere but WORK_DIR silently produces
# galleries with objects missing.
os.chdir(WORK_DIR)

# Import the existing build functions
sys.path.insert(0, str(GALLERY_DIR))

from build_messier_gallery import generate_html as generate_catalog_html
from build_messier_ra_chart import generate_ra_chart_html
from build_all_targets_gallery import generate_html as generate_all_targets_html
from build_caldwell_gallery import generate_html as generate_caldwell_html


IMAGE_REF_RE = re.compile(
    r"""(?:src="|openModal\(')(targets/[^"']+\.(?:jpg|png|webp))""",
    re.IGNORECASE,
)


def extract_image_refs(content):
    """Return the set of targets/... image paths referenced by an HTML string.

    Matches both the <img src> and the click-to-zoom openModal() path, because
    after publish those two differ: src points at a thumbnail, openModal at the
    full-size image. Thumbnails are derivatives rather than content, so they are
    excluded - otherwise a published thumbnail would look to the removal check
    like a distinct image for the object.
    """
    refs = set()
    for match in IMAGE_REF_RE.findall(content):
        if match.lower().endswith(THUMB_SUFFIX):
            continue
        refs.add(unquote(match))
    return refs


def object_dirs(refs):
    """Collapse image paths to their object directory, e.g. targets/clusters/m19.

    Comparing at this level means superseding an image with a newer capture of the
    same object is not treated as a removal, but an object losing its only image is.
    """
    return {str(Path(ref).parent) for ref in refs}


def rank(ref):
    """Sort key describing how good an image is: (date, suffix).

    Mirrors the generators' preference order, where a later date wins and a
    suffixed hand-processed version (m108_2026-04-18b.jpg) beats the plain one
    for the same date. Used to detect silent downgrades.
    """
    name = Path(ref).name
    match = re.search(r'_(\d{4}-\d{2}-\d{2})([a-z]?)\.', name, re.IGNORECASE)
    if not match:
        return ('', '')
    return (match.group(1), match.group(2).lower())


def best_per_object(refs):
    """Map object directory -> its highest-ranked referenced image."""
    best = {}
    for ref in refs:
        key = str(Path(ref).parent)
        if key not in best or rank(ref) > rank(best[key]):
            best[key] = ref
    return best


def baseline_refs():
    """Image refs from the last committed gallery, which is the published state.

    Falls back to the on-disk HTML if git can't tell us (no repo, no commits).
    Returns None if no baseline is available, so callers can skip the comparison
    rather than treating "unknown" as "nothing was there".
    """
    refs = set()
    found_any = False
    for html_file in HTML_FILES:
        content = None
        try:
            content = subprocess.run(
                ['git', '-C', str(GALLERY_DIR), 'show', f'HEAD:{html_file}'],
                capture_output=True, text=True, check=True,
            ).stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            path = GALLERY_DIR / html_file
            if path.exists():
                content = path.read_text()
        if content is not None:
            found_any = True
            refs |= extract_image_refs(content)
    return refs if found_any else None


def check_build(generated):
    """Compare generated HTML against the baseline.

    Returns (lost, broken, downgraded, added).
    """
    new_refs = set()
    for content in generated.values():
        new_refs |= extract_image_refs(content)

    # Every reference must resolve to a real file in the source tree, or the
    # gallery will ship with broken images.
    broken = sorted(
        ref for ref in new_refs
        if not (TARGETS_DIR / ref.replace('targets/', '', 1)).exists()
    )

    old = baseline_refs()
    if old is None:
        print("  ! no baseline found (new repo?) - skipping removal check")
        return [], broken, [], sorted(object_dirs(new_refs))

    lost = sorted(object_dirs(old) - object_dirs(new_refs))

    # An object can survive while quietly regressing to an older or less-processed
    # image, which the presence check above would not notice.
    old_best, new_best = best_per_object(old), best_per_object(new_refs)
    downgraded = sorted(
        (key, old_best[key], new_best[key])
        for key in old_best.keys() & new_best.keys()
        if rank(new_best[key]) < rank(old_best[key])
    )

    added = sorted(object_dirs(new_refs) - object_dirs(old))
    return lost, broken, downgraded, added


def report(lost, broken, downgraded, added, total):
    print(f"\n  objects rendered: {total}")
    if added:
        print(f"  + {len(added)} new: {', '.join(Path(d).name for d in added)}")
    if downgraded:
        print(f"\n  ✗ {len(downgraded)} object(s) would REGRESS to an older/less-processed image:")
        for key, old_ref, new_ref in downgraded:
            print(f"      {Path(key).name}: {Path(old_ref).name} -> {Path(new_ref).name}")
        print("\n    The better image is published but missing from the source tree.")
        print(f"    Copy it from {GALLERY_DIR}/targets/ into {TARGETS_DIR}/.")
    if lost:
        print(f"\n  ✗ {len(lost)} object(s) would DISAPPEAR from the gallery:")
        for d in lost:
            print(f"      {d}")
        print("\n    These are referenced by the published gallery but the build no")
        print("    longer finds an image for them. Usually this means the image exists")
        print(f"    only under {GALLERY_DIR}/targets/ and is missing from {TARGETS_DIR}/.")
        print("    Copy it into the source tree, then rebuild.")
    if broken:
        print(f"\n  ✗ {len(broken)} reference(s) point at files missing from the source tree:")
        for ref in broken:
            print(f"      {ref}")
    if not lost and not broken and not downgraded:
        print("  ✓ no objects lost or regressed, all references resolve")


def thumb_ref(ref):
    """Gallery path of the thumbnail for `ref`, kept beside the full-size image."""
    return ref + THUMB_SUFFIX


def _stale(dst, src):
    return not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime


def _flatten(im):
    """Drop alpha onto black so the image can be saved as JPEG."""
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA')
        base = Image.new('RGB', im.size, (0, 0, 0))
        base.paste(im, mask=im.split()[-1])
        return base
    return im.convert('RGB')


def _jpeg_bytes(src):
    """Encode `src` as a publishing-quality JPEG and return the bytes.

    subsampling=0 keeps 4:4:4 chroma. Star fields are per-pixel colour detail,
    which 4:2:0 smears badly - 5 dB of PSNR on the M33 frame.
    """
    buf = io.BytesIO()
    with Image.open(src) as im:
        _flatten(im).save(buf, 'JPEG', quality=WEB_JPEG_QUALITY,
                          subsampling=0, optimize=True, progressive=True)
    return buf.getvalue()


def publishable_full(ref, src):
    """Decide what full-size file to publish for `ref`, writing it if needed.

    Returns (gallery path, 1 if a JPEG was just encoded else 0). PNGs become
    JPEG only when that saves real space; the source under targets/ is never
    touched either way.
    """
    if src.suffix.lower() != '.png':
        return ref, 0

    as_jpeg = str(Path(ref).with_suffix('.jpg'))
    dst = GALLERY_DIR / as_jpeg
    if dst.exists() and not _stale(dst, src):
        return as_jpeg, 0

    data = _jpeg_bytes(src)
    if len(data) > src.stat().st_size * WEB_JPEG_MAX_RATIO:
        return ref, 0

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    return as_jpeg, 1


def build_derivatives(refs):
    """Write thumbnails, and JPEG versions of PNGs where smaller, into the gallery.

    Returns (mapping, thumbs_made, webs_made) where mapping is
    ref -> (full-size gallery path, thumbnail gallery path).
    """
    mapping = {}
    thumbs_made = webs_made = 0

    for ref in sorted(refs):
        src = TARGETS_DIR / ref.replace('targets/', '', 1)
        if not src.exists():
            continue

        thumb = thumb_ref(ref)
        full, made = publishable_full(ref, src)
        webs_made += made
        (GALLERY_DIR / full).parent.mkdir(parents=True, exist_ok=True)
        dst_thumb = GALLERY_DIR / thumb

        if _stale(dst_thumb, src):
            with Image.open(src) as im:
                im.thumbnail((THUMB_MAX_EDGE, THUMB_MAX_EDGE), Image.LANCZOS)
                if im.mode not in ('RGB', 'RGBA'):
                    im = im.convert('RGB')
                im.save(dst_thumb, 'WEBP', quality=THUMB_QUALITY, method=6)
            thumbs_made += 1

        mapping[ref] = (full, thumb)

    return mapping, thumbs_made, webs_made


def rewrite_for_thumbnails(content, mapping):
    """Point every <img src> at a thumbnail, leaving click-to-zoom on full size."""
    def sub_src(match):
        entry = mapping.get(unquote(match.group(1)))
        if not entry:
            return match.group(0)
        return f'src="{quote(entry[1])}" loading="lazy"'

    def sub_modal(match):
        entry = mapping.get(unquote(match.group(1)))
        if not entry:
            return match.group(0)
        return f"openModal('{quote(entry[0])}')"

    content = re.sub(r'src="(targets/[^"]+)"', sub_src, content)
    content = re.sub(r"openModal\('(targets/[^']+)'\)", sub_modal, content)
    return content


def prune_superseded(mapping):
    """Delete published originals that a re-encoded version has replaced."""
    removed = 0
    for ref, (full, _thumb) in mapping.items():
        if full == ref:
            continue
        stale_path = GALLERY_DIR / ref
        if stale_path.exists():
            stale_path.unlink()
            removed += 1
    return removed


def copy_displayed_images(image_paths, mapping):
    """Copy the displayed full-size images to gallery.

    Images published as a re-encoded derivative are already written by
    build_derivatives, so they are skipped here.
    """
    image_paths = {ref for ref in image_paths if mapping.get(ref, (ref,))[0] == ref}

    print(f"\nCopying {len(image_paths)} displayed images to gallery...")

    copied = missing = 0
    for img_path in sorted(image_paths):
        src = TARGETS_DIR / img_path.replace('targets/', '', 1)
        dst = GALLERY_DIR / img_path

        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not (dst.exists() and os.path.samefile(src, dst)):
                shutil.copy2(src, dst)
            copied += 1
        else:
            print(f"  ✗ {img_path} (not found)")
            missing += 1

    print(f"  ✓ {copied} copied" + (f", ✗ {missing} missing" if missing else ""))


def main():
    check_only = '--check' in sys.argv
    allow_removals = '--allow-removals' in sys.argv

    print("Building Messier galleries..." if not check_only else "Checking gallery build (dry run)...")
    print(f"Work directory: {WORK_DIR}")
    print(f"Gallery directory: {GALLERY_DIR}")

    # Generate everything in memory first so a failed check writes nothing.
    print("\n1. Generating HTML...")
    generated = {
        'messier_catalog.html': generate_catalog_html(),
        'messier_ra_chart.html': generate_ra_chart_html(),
        'all_targets.html': generate_all_targets_html(),
        'caldwell_catalog.html': generate_caldwell_html(),
    }

    print("\n2. Checking against published gallery...")
    lost, broken, downgraded, added = check_build(generated)
    total = len(object_dirs(extract_image_refs(''.join(generated.values()))))
    report(lost, broken, downgraded, added, total)

    problems = bool(lost or broken or downgraded)

    if check_only:
        print("\n(dry run - nothing written)")
        return 1 if problems else 0

    if problems and not allow_removals:
        print("\n❌ Aborted before writing. Nothing was modified.")
        print("   Fix the above, or rerun with --allow-removals if the loss is intended.")
        return 1

    if problems:
        print("\n  ! proceeding despite problems (--allow-removals)")

    refs = set()
    for content in generated.values():
        refs |= extract_image_refs(content)

    print("\n3. Building thumbnails...")
    mapping, thumbs_made, webs_made = build_derivatives(refs)
    print(f"  ✓ {len(mapping)} thumbnails ({thumbs_made} rebuilt)")
    if webs_made:
        print(f"  ✓ {webs_made} PNG(s) re-encoded to JPEG for publishing")
    removed = prune_superseded(mapping)
    if removed:
        print(f"  ✓ {removed} superseded original(s) removed from the gallery")

    generated = {name: rewrite_for_thumbnails(content, mapping)
                 for name, content in generated.items()}

    print("\n4. Writing HTML...")
    for name, content in generated.items():
        (GALLERY_DIR / name).write_text(content)
        print(f"  ✓ {name}")

    print("\n5. Copying images...")
    copy_displayed_images(refs, mapping)

    print("\n✅ Build complete!")
    print(f"\nTo publish updates:")
    print(f"  cd {GALLERY_DIR}")
    print(f"  git add .")
    print(f"  git commit -m 'Update gallery'")
    print(f"  git push")
    return 0


if __name__ == '__main__':
    sys.exit(main())
