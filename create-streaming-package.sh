#!/bin/bash
# Create streaming fix package with all necessary files

set -e

echo "=========================================="
echo "Creating STREAMING FIX PACKAGE"
echo "=========================================="
echo

PROJECT_ROOT="/media/juan/DATA/projects/GEMINI-CLI-2/qwen-dev-cli"
PACKAGE_NAME="streaming-fix-package.tar.gz"

cd "$PROJECT_ROOT"

echo "📦 Packaging files..."

# Create package with all necessary files
tar -czf "$PACKAGE_NAME" \
  --transform 's,^,streaming-fix/,' \
  STREAMING_AUDIT_REPORT.md \
  STREAMING_FIX_PACKAGE.md \
  maestro_v10_integrated.py \
  qwen_dev_cli/agents/executor_nextgen.py \
  qwen_dev_cli/agents/planner.py \
  qwen_dev_cli/agents/explorer.py \
  qwen_dev_cli/agents/reviewer.py \
  qwen_dev_cli/agents/refactorer.py \
  qwen_dev_cli/agents/base.py \
  qwen_dev_cli/core/llm.py \
  qwen_dev_cli/core/mcp.py \
  qwen_dev_cli/core/file_tracker.py \
  qwen_dev_cli/tui/components/maestro_shell_ui.py

echo "✅ Package created: $PACKAGE_NAME"
echo

# Show package contents
echo "📋 Package contents:"
tar -tzf "$PACKAGE_NAME" | head -20
echo

# Show package size
SIZE=$(du -h "$PACKAGE_NAME" | cut -f1)
echo "📊 Package size: $SIZE"
echo

echo "=========================================="
echo "✅ PACKAGE READY!"
echo "=========================================="
echo
echo "📦 File: $PROJECT_ROOT/$PACKAGE_NAME"
echo
echo "🚀 To extract:"
echo "   tar -xzf $PACKAGE_NAME"
echo
echo "📖 Start by reading:"
echo "   streaming-fix/STREAMING_AUDIT_REPORT.md"
echo
