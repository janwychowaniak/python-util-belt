#!/bin/bash
# copy_module.sh - Simple utility to copy modules from python-util-belt
#
# Usage:
#   ./copy_module.sh MODULE_NAME TARGET_DIR
#   ./copy_module.sh ncvz ./my_project/utils/
#
# Example:
#   cd ~/python-util-belt
#   ./scripts/copy_module.sh ncvz ~/my-project/utils/

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 MODULE_NAME TARGET_DIR"
    echo "Example: $0 ncvz ./my_project/utils/"
    exit 1
fi

MODULE="$1"
TARGET_DIR="$2"

# Get the script directory and find the modules directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BELT_ROOT="$(dirname "$SCRIPT_DIR")"
SOURCE_FILE="$BELT_ROOT/modules/${MODULE}.py"

# Check if module exists
if [ ! -f "$SOURCE_FILE" ]; then
    echo "Error: Module '${MODULE}' not found at $SOURCE_FILE"
    echo ""
    echo "Available modules:"
    ls -1 "$BELT_ROOT/modules/"*.py 2>/dev/null | xargs -n1 basename | sed 's/\.py$//' || echo "  (none)"
    exit 1
fi

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Copy the module
cp "$SOURCE_FILE" "$TARGET_DIR/"

echo "✓ Copied ${MODULE}.py to $TARGET_DIR/"
echo ""
echo "Usage in your project:"
echo "  from $(basename "$TARGET_DIR").${MODULE} import ${MODULE}"
echo ""
echo "Source: python-util-belt/modules/${MODULE}.py"
