#!/bin/bash
# Archive old sessions to durin.local
# Moves session data and removes broken symlinks

set -e

SESSIONS_LOCAL="/home/dlwiii/astro/sessions"
SESSIONS_ARCHIVE="/home/dlwiii/durin/astro_archive/sessions"
TARGETS_DIR="/home/dlwiii/astro/targets"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ $# -eq 0 ]; then
    echo -e "${BLUE}=== Archive Session to durin.local ===${NC}"
    echo ""
    echo "Usage: $0 <session-date> [session-date...]"
    echo ""
    echo "Available sessions:"
    ls -1 "$SESSIONS_LOCAL" | sort
    echo ""
    echo "Example: $0 2025-12-25"
    echo "         $0 2025-12-25 2025-12-26 2025-12-27"
    exit 0
fi

# Check if durin is mounted
if ! mountpoint -q /home/dlwiii/durin; then
    echo -e "${RED}Error: durin.local is not mounted${NC}"
    echo "Mount with: sshfs dlwiii@durin.local:/mnt/media2 /home/dlwiii/durin"
    exit 1
fi

echo -e "${BLUE}=== Archive Sessions to durin.local ===${NC}"
echo ""

for SESSION_DATE in "$@"; do
    SESSION_PATH="$SESSIONS_LOCAL/$SESSION_DATE"

    if [ ! -d "$SESSION_PATH" ]; then
        echo -e "${RED}✗ Session not found: $SESSION_DATE${NC}"
        continue
    fi

    # Calculate size
    SIZE=$(du -sh "$SESSION_PATH" | cut -f1)

    echo -e "${YELLOW}Session: $SESSION_DATE ($SIZE)${NC}"

    # Show targets in this session
    echo "  Targets:"
    ls -1 "$SESSION_PATH" | while read target; do
        echo "    - $target"
    done

    # Check if already archived
    if [ -d "$SESSIONS_ARCHIVE/$SESSION_DATE" ]; then
        echo -e "  ${YELLOW}⚠ Already archived (will skip)${NC}"
        echo ""
        continue
    fi

    echo ""
done

read -p "Proceed with archiving these sessions? (yes/no): " confirm

if [[ "$confirm" != "yes" ]]; then
    echo -e "${RED}Cancelled.${NC}"
    exit 1
fi

echo ""

# Archive each session
for SESSION_DATE in "$@"; do
    SESSION_PATH="$SESSIONS_LOCAL/$SESSION_DATE"

    if [ ! -d "$SESSION_PATH" ]; then
        continue
    fi

    if [ -d "$SESSIONS_ARCHIVE/$SESSION_DATE" ]; then
        echo -e "${YELLOW}Skipping $SESSION_DATE (already archived)${NC}"
        continue
    fi

    echo -e "${GREEN}Archiving $SESSION_DATE...${NC}"

    # Move to archive using rsync (safer than mv for network)
    rsync -avh --progress "$SESSION_PATH/" "$SESSIONS_ARCHIVE/$SESSION_DATE/"

    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✓ Copied to durin${NC}"

        # Remove local copy
        rm -rf "$SESSION_PATH"
        echo -e "  ${GREEN}✓ Removed local copy${NC}"

        # Find and remove broken symlinks to this session
        echo -e "  ${YELLOW}Removing broken symlinks...${NC}"

        SYMLINKS_REMOVED=0
        for category in galaxies clusters nebulae; do
            category_path="$TARGETS_DIR/$category"
            [ ! -d "$category_path" ] && continue

            for target_dir in "$category_path"/*; do
                [ ! -d "$target_dir" ] && continue

                link_path="$target_dir/$SESSION_DATE"
                if [ -L "$link_path" ] && [ ! -e "$link_path" ]; then
                    rm "$link_path"
                    echo -e "    Removed: $category/$(basename $target_dir)/$SESSION_DATE"
                    ((SYMLINKS_REMOVED++))
                fi
            done
        done

        echo -e "  ${GREEN}✓ Removed $SYMLINKS_REMOVED broken symlinks${NC}"
        echo ""
    else
        echo -e "  ${RED}✗ rsync failed${NC}"
        echo ""
    fi
done

echo -e "${GREEN}=== Archive Complete ===${NC}"
echo ""
echo "Archived sessions are at: $SESSIONS_ARCHIVE"
echo ""

# Show remaining local sessions
echo "Remaining local sessions:"
ls -1 "$SESSIONS_LOCAL" | wc -l
echo ""

# Show durin usage
df -h /home/dlwiii/durin | tail -1
