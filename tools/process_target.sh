#!/bin/bash
# Automated SIRIL processing for Seestar data
# Usage: process_target.sh <target> <type> [session_date]
# Example: process_target.sh m13 cluster 2026-05-15
#          process_target.sh m83 galaxy

set -e

TARGET="$1"
TYPE="$2"
SESSION="$3"

ASTRO_DIR="/mnt/media2/astro"
TARGETS_DIR="$ASTRO_DIR/targets"
PROCESSING_DIR="$ASTRO_DIR/processing"

# Validate arguments
if [ -z "$TARGET" ] || [ -z "$TYPE" ]; then
    echo "Usage: $0 <target> <type> [session_date]"
    echo "  target: m13, m83, m51, etc."
    echo "  type: cluster, galaxy, nebula"
    echo "  session_date: optional, defaults to most recent"
    exit 1
fi

# Normalize target name (lowercase)
TARGET=$(echo "$TARGET" | tr '[:upper:]' '[:lower:]')

# Map type to category directory
case "$TYPE" in
    cluster|clusters) CATEGORY="clusters" ;;
    galaxy|galaxies) CATEGORY="galaxies" ;;
    nebula|nebulae) CATEGORY="nebulae" ;;
    *) echo "Error: type must be cluster, galaxy, or nebula"; exit 1 ;;
esac

# Find target directory
TARGET_PATH="$TARGETS_DIR/$CATEGORY/$TARGET"
if [ ! -d "$TARGET_PATH" ]; then
    echo "Error: Target not found at $TARGET_PATH"
    exit 1
fi

# Find session (most recent if not specified)
if [ -z "$SESSION" ]; then
    SESSION=$(ls -d "$TARGET_PATH"/20* 2>/dev/null | sort -r | head -1 | xargs basename)
    if [ -z "$SESSION" ]; then
        echo "Error: No session directories found in $TARGET_PATH"
        exit 1
    fi
fi

SESSION_PATH="$TARGET_PATH/$SESSION"
if [ ! -d "$SESSION_PATH" ]; then
    echo "Error: Session not found at $SESSION_PATH"
    exit 1
fi

# Find subs directory
SUBS_DIR=$(find "$SESSION_PATH" -type d -name "*_sub" | head -1)
if [ -z "$SUBS_DIR" ]; then
    echo "Error: No subs directory found in $SESSION_PATH"
    exit 1
fi

SUB_COUNT=$(ls "$SUBS_DIR"/*.fit 2>/dev/null | wc -l)
echo "Found $SUB_COUNT subs in $SUBS_DIR"

# Create processing directory
PROC_DIR="$PROCESSING_DIR/$TARGET/$SESSION"
mkdir -p "$PROC_DIR/light" "$PROC_DIR/result"

# Copy subs with spaces replaced by underscores
echo "Copying subs to processing directory..."
for f in "$SUBS_DIR"/*.fit; do
    newname=$(basename "$f" | tr ' ' '_')
    cp "$f" "$PROC_DIR/light/$newname"
done

# Set processing parameters based on type
case "$TYPE" in
    cluster|clusters)
        STRETCH_B="-2.8"
        STRETCH_S="0.25"
        SATURATION=""
        BG_EXTRACT=""
        ;;
    galaxy|galaxies)
        STRETCH_B="-2.5"
        STRETCH_S="0.20"
        SATURATION="satu 1.2"
        BG_EXTRACT="subsky 1 -rbf"
        ;;
    nebula|nebulae)
        STRETCH_B="-2.2"
        STRETCH_S="0.15"
        SATURATION="satu 1.5"
        BG_EXTRACT="subsky 1 -rbf"
        ;;
esac

TODAY=$(date +%Y-%m-%d)

# Generate SIRIL script
cat > "$PROC_DIR/process.ssf" << EOF
requires 1.2.0

# SIRIL auto-processing script
# Target: $TARGET ($TYPE)
# Session: $SESSION
# Generated: $(date)

# Convert lights
cd $PROC_DIR/light
convert Light -out=../ -fitseq

cd $PROC_DIR

# Debayer CFA to RGB
preprocess Light -debayer

# Register frames
register pp_Light -minpairs=4

# Stack with rejection
stack r_pp_Light rej 3 3 -norm=addscale -output_norm -out=${TARGET}_stacked

# Load and process
load ${TARGET}_stacked

# Background extraction (galaxies/nebulae only)
$BG_EXTRACT

# Autostretch with type-specific parameters
autostretch $STRETCH_B $STRETCH_S

# Color saturation boost (galaxies/nebulae only)
$SATURATION

# Save results
save result/${TARGET}_processed
savejpg result/${TARGET}_${TODAY} 100
EOF

echo "Processing $TARGET ($TYPE) from session $SESSION..."
echo "Output will be in: $PROC_DIR/result/"

# Run SIRIL
siril-cli -d "$PROC_DIR" -s "$PROC_DIR/process.ssf" 2>&1 | grep -E "^log:|^progress:|Script execution"

# Check result
if [ -f "$PROC_DIR/result/${TARGET}_${TODAY}.jpg" ]; then
    echo ""
    echo "✅ Processing complete!"
    echo "   Result: $PROC_DIR/result/${TARGET}_${TODAY}.jpg"
    echo ""
    echo "To publish to gallery:"
    echo "   cp $PROC_DIR/result/${TARGET}_${TODAY}.jpg $TARGET_PATH/"
    echo "   cd $ASTRO_DIR && python3 build_and_publish.py"
else
    echo "❌ Processing failed - check logs above"
    exit 1
fi
