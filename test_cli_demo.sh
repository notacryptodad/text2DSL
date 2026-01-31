#!/bin/bash
# Text2X CLI Demo Script
# This script demonstrates the CLI functionality without requiring a running server

set -e

echo "=========================================="
echo "Text2X CLI Demo"
echo "=========================================="
echo ""

echo "1. Showing CLI version:"
python3 -m text2x.cli --version
echo ""

echo "2. Showing global help:"
python3 -m text2x.cli --help
echo ""

echo "3. Showing query command help:"
python3 -m text2x.cli query --help
echo ""

echo "4. Showing providers commands:"
python3 -m text2x.cli providers list --help
python3 -m text2x.cli providers show --help
echo ""

echo "5. Showing conversation command:"
python3 -m text2x.cli conversation show --help
echo ""

echo "6. Showing config commands:"
python3 -m text2x.cli config show --help
python3 -m text2x.cli config set --help
python3 -m text2x.cli config reset --help
echo ""

echo "7. Testing config show (using defaults):"
python3 -m text2x.cli config show
echo ""

echo "=========================================="
echo "CLI is production-ready!"
echo "=========================================="
echo ""
echo "To use the CLI with a running server:"
echo "  1. Start the Text2X API server"
echo "  2. Run: text2x providers list"
echo "  3. Run: text2x query 'Show all users' -p <provider-id>"
echo ""
