#!/bin/bash

# Script to clean backed-up files from Seestar device
# Checks if files on Seestar exist in local backup before removing

# Astro root: ASTRO_DIR env var wins; else walk up from this script's real
# location until we find the dir holding sessions/ and targets/ (works from
# ~/astro/scripts symlink and from the gallery repo's tools/ folder).
if [ -z "$ASTRO_DIR" ]; then
    d="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd -P)"
    while [ "$d" != "/" ]; do
        if [ -d "$d/sessions" ] && [ -d "$d/targets" ]; then ASTRO_DIR="$d"; break; fi
        d="$(dirname "$d")"
    done
    ASTRO_DIR="${ASTRO_DIR:-$HOME/astro}"
fi
LOCAL_RAW="$ASTRO_DIR/seestar_s30/raw"
LOCAL_TARGETS="$ASTRO_DIR/targets"
LOCAL_SESSIONS="$ASTRO_DIR/sessions"

# Seestar mount: SEESTAR_PATH env var wins; else look under the udisks mount
# roots for Arch/Omarchy (/run/media/$USER) and Debian/Mint (/media/$USER).
if [ -z "$SEESTAR_PATH" ]; then
    for base in "/run/media/$USER" "/media/$USER"; do
        for vol in "$base"/[Ss]eestar*; do
            if [ -d "$vol/MyWorks" ]; then SEESTAR_PATH="$vol/MyWorks"; break 2; fi
        done
    done
    SEESTAR_PATH="${SEESTAR_PATH:-/run/media/$USER/Seestar/MyWorks}"
fi

echo "======================================"
echo "Seestar Device Cleanup Script"
echo "======================================"
echo ""

if [ ! -d "$SEESTAR_PATH" ]; then
    echo "ERROR: Seestar not mounted at $SEESTAR_PATH"
    exit 1
fi

echo "Indexing local backup (sessions, targets, raw)..."
# One pass over local storage; -L follows the per-session symlinks in targets/.
declare -A LOCAL_FILES=()
while IFS= read -r f; do
    LOCAL_FILES["$f"]=1
done < <(find -L "$LOCAL_SESSIONS" "$LOCAL_TARGETS" "$LOCAL_RAW" -name "*.fit" -printf '%f\n' 2>/dev/null)
echo "  ${#LOCAL_FILES[@]} distinct .fit filenames found locally"
echo ""
echo "Scanning Seestar device for backed-up files..."
echo ""

# Arrays to track directories
declare -a SAFE_TO_DELETE=()
declare -a PARTIAL_BACKUP=()
declare -a NOT_BACKED_UP=()

# Process each _sub directory
while IFS= read -r dir; do
    dir_name=$(basename "$dir")
    total_fits=$(find "$dir" -name "*.fit" 2>/dev/null | wc -l)

    if [ "$total_fits" -eq 0 ]; then
        continue
    fi

    backed_up=0

    # Check each FIT file
    while IFS= read -r fit_file; do
        filename=$(basename "$fit_file")

        # Check if exists in local raw or targets
        if [ -n "${LOCAL_FILES[$filename]}" ]; then
            ((backed_up++))
        fi
    done < <(find "$dir" -name "*.fit" 2>/dev/null)

    size=$(du -sh "$dir" 2>/dev/null | cut -f1)
    backup_pct=$((backed_up * 100 / total_fits))

    if [ "$backed_up" -eq "$total_fits" ]; then
        SAFE_TO_DELETE+=("$dir|$size|$total_fits")
    elif [ "$backed_up" -gt 0 ]; then
        PARTIAL_BACKUP+=("$dir|$size|$backed_up/$total_fits ($backup_pct%)")
    else
        NOT_BACKED_UP+=("$dir|$size|$total_fits")
    fi

done < <(find "$SEESTAR_PATH" -maxdepth 1 -type d -name "*_sub" 2>/dev/null | sort)

echo "=== FULLY BACKED UP (Safe to Delete) ==="
echo ""
total_safe_size=0
if [ ${#SAFE_TO_DELETE[@]} -gt 0 ]; then
    for entry in "${SAFE_TO_DELETE[@]}"; do
        IFS='|' read -r dir size files <<< "$entry"
        printf "  %-40s %8s  (%s files)\n" "$(basename "$dir")" "$size" "$files"
    done
else
    echo "  None"
fi
echo ""

echo "=== PARTIALLY BACKED UP (Review Manually) ==="
echo ""
if [ ${#PARTIAL_BACKUP[@]} -gt 0 ]; then
    for entry in "${PARTIAL_BACKUP[@]}"; do
        IFS='|' read -r dir size files <<< "$entry"
        printf "  %-40s %8s  %s backed up\n" "$(basename "$dir")" "$size" "$files"
    done
else
    echo "  None"
fi
echo ""

echo "=== NOT BACKED UP (Do Not Delete) ==="
echo ""
if [ ${#NOT_BACKED_UP[@]} -gt 0 ]; then
    for entry in "${NOT_BACKED_UP[@]}"; do
        IFS='|' read -r dir size files <<< "$entry"
        printf "  %-40s %8s  (%s files)\n" "$(basename "$dir")" "$size" "$files"
    done
else
    echo "  None"
fi
echo ""

if [ ${#SAFE_TO_DELETE[@]} -eq 0 ]; then
    echo "No directories are safe to delete at this time."
    exit 0
fi

echo "======================================"
read -p "Delete FULLY BACKED UP directories? [y/N]: " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Deleting backed-up directories..."
    echo ""

    for entry in "${SAFE_TO_DELETE[@]}"; do
        IFS='|' read -r dir size files <<< "$entry"
        echo "  Deleting: $(basename "$dir") ($size)"
        rm -rf "$dir"
    done

    echo ""
    echo "✓ Cleanup complete!"
    echo ""
    df -h "$SEESTAR_PATH" | tail -1
else
    echo ""
    echo "Cleanup cancelled. No files were deleted."
fi
