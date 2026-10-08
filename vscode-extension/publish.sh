#!/usr/bin/env bash
# ============================================================================
#  Rewind VS Code Extension Publisher
#  Publishes rewind-guard to Visual Studio Marketplace and/or Open VSX
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}${BOLD}  📦  Publish Rewind Guard Extension to Marketplace${NC}"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 1. Package the VSIX cleanly
echo -e "  ${BOLD}[1/3] Building & Packaging VSIX...${NC}"
npm run package
npx @vscode/vsce package --no-git-tag-version
echo -e "  ${GREEN}✔ Package created: rewind-guard-0.1.0.vsix${NC}"
echo ""

# 2. Check for token
VSCE_PAT="${1:-${VSCE_PAT:-}}"

if [[ -z "$VSCE_PAT" ]]; then
  echo -e "  ${YELLOW}No Personal Access Token (PAT) provided.${NC}"
  echo -e "  To publish to Visual Studio Marketplace:"
  echo -e "    1. Create a token at ${BOLD}https://dev.azure.com${NC} (Scope: Marketplace > Manage)"
  echo -e "    2. Ensure publisher ${BOLD}abhinav29102005${NC} exists at ${BOLD}https://marketplace.visualstudio.com/manage${NC}"
  echo ""
  read -rp "  Enter your Azure DevOps PAT (or press Enter to skip VS Marketplace): " VSCE_PAT
fi

if [[ -n "$VSCE_PAT" ]]; then
  echo ""
  echo -e "  ${BOLD}[2/3] Publishing to Visual Studio Marketplace...${NC}"
  npx @vscode/vsce publish -p "$VSCE_PAT"
  echo -e "  ${GREEN}✔ Successfully published to Visual Studio Marketplace!${NC}"
else
  echo -e "  ${YELLOW}Skipping Visual Studio Marketplace upload.${NC}"
  echo -e "  You can also manually drag & drop ${BOLD}rewind-guard-0.1.0.vsix${NC} at:"
  echo -e "  ${CYAN}https://marketplace.visualstudio.com/manage/publishers/abhinav29102005${NC}"
fi

# 3. Open VSX option
echo ""
OVSX_PAT="${OVSX_PAT:-}"
if [[ -z "$OVSX_PAT" ]]; then
  read -rp "  Enter Open VSX token (or press Enter to skip Open-VSX): " OVSX_PAT
fi

if [[ -n "$OVSX_PAT" ]]; then
  echo -e "  ${BOLD}[3/3] Publishing to Open VSX Registry...${NC}"
  npx ovsx publish rewind-guard-0.1.0.vsix -p "$OVSX_PAT"
  echo -e "  ${GREEN}✔ Successfully published to Open VSX!${NC}"
else
  echo -e "  ${YELLOW}Skipping Open VSX upload.${NC}"
fi

echo ""
echo -e "  ${GREEN}${BOLD}✔ Done!${NC}"
echo ""
