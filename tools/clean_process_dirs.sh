#!/bin/bash

# Script to clean up intermediate processing directories to free disk space
# These directories contain temporary files from Siril/stacking that can be regenerated

set -e

TARGETS_DIR="/home/dlwiii/astro/targets"
DRY_RUN=false

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}DRY RUN MODE - No files will be deleted${NC}"
    echo ""
fi

# Find all process directories
echo "Scanning for process directories..."
echo ""

PROCESS_DIRS=$(find "$TARGETS_DIR" -type d -name "process" 2>/dev/null | sort)

if [ -z "$PROCESS_DIRS" ]; then
    echo -e "${GREEN}No process directories found. Already clean!${NC}"
    exit 0
fi

# Count and calculate size
DIR_COUNT=$(echo "$PROCESS_DIRS" | wc -l)
echo -e "${YELLOW}Found $DIR_COUNT process directories:${NC}"
echo ""

# Show each directory with its size
while IFS= read -r dir; do
    size=$(du -sh "$dir" 2>/dev/null | cut -f1)
    rel_path=${dir#$TARGETS_DIR/}
    echo "  [$size] $rel_path"
done <<< "$PROCESS_DIRS"

echo ""

# Calculate total size
TOTAL_SIZE=$(find "$TARGETS_DIR" -type d -name "process" -exec du -sb {} \; 2>/dev/null | awk '{sum+=$1} END {printf "%.2f", sum/1024/1024/1024}')
echo -e "${YELLOW}Total space to be freed: ${TOTAL_SIZE} GB${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${GREEN}Dry run complete. Use without --dry-run to actually delete.${NC}"
    exit 0
fi

# Confirmation prompt
read -p "Delete all process directories? This cannot be undone! (yes/no): " confirm

if [[ "$confirm" != "yes" ]]; then
    echo -e "${RED}Cancelled.${NC}"
    exit 1
fi

# Delete directories
echo ""
echo -e "${GREEN}Deleting process directories...${NC}"

deleted=0
while IFS= read -r dir; do
    rel_path=${dir#$TARGETS_DIR/}
    echo "  Deleting: $rel_path"
    rm -rf "$dir"
    ((deleted++))
done <<< "$PROCESS_DIRS"

echo ""
echo -e "${GREEN}✓ Deleted $deleted process directories${NC}"
echo -e "${GREEN}✓ Freed approximately ${TOTAL_SIZE} GB of disk space${NC}"
echo ""
echo "Run 'df -h' to see updated disk usage."
