#!/bin/bash
# =============================================================================
# Juan-Dev-Code Hackathon Deploy Script
# =============================================================================
#
# Deploys to all hackathon targets:
# - Modal (Serverless Gradio UI)
# - Blaxel (AI Agent Platform)
#
# Prizes:
# - 🏆 Google Gemini — $30,000 em API Credits
# - 💰 Modal Innovation Award — $2,500 Cash
# - 💰 Blaxel Choice Award — $2,500 Cash
#
# Usage:
#   ./deploy.sh         # Deploy all
#   ./deploy.sh modal   # Deploy only Modal
#   ./deploy.sh blaxel  # Deploy only Blaxel
#   ./deploy.sh local   # Run local Gradio
#
# Author: JuanCS Dev
# Date: 2025-11-27
# =============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Banner
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           🚀 Juan-Dev-Code Hackathon Deploy                  ║"
echo "║                                                              ║"
echo "║  Targets:                                                    ║"
echo "║    📦 Modal   - Serverless Gradio UI                        ║"
echo "║    🤖 Blaxel  - AI Agent Platform                           ║"
echo "║                                                              ║"
echo "║  Prizes:                                                     ║"
echo "║    🏆 Gemini  - \$30,000 API Credits                         ║"
echo "║    💰 Modal   - \$2,500 Cash                                 ║"
echo "║    💰 Blaxel  - \$2,500 Cash                                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check prerequisites
check_prerequisites() {
    echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

    # Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Python 3 found${NC}"

    # pip
    if ! command -v pip &> /dev/null; then
        echo -e "${RED}❌ pip not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ pip found${NC}"

    # Check API key
    if [ -z "$GOOGLE_API_KEY" ] && [ -z "$GEMINI_API_KEY" ]; then
        echo -e "${YELLOW}⚠️  GOOGLE_API_KEY or GEMINI_API_KEY not set${NC}"
        echo -e "${YELLOW}   Set one of these for Gemini API access${NC}"
    else
        echo -e "${GREEN}✓ API key configured${NC}"
    fi
}

# Deploy to Modal
deploy_modal() {
    echo ""
    echo -e "${BLUE}📦 Deploying to Modal...${NC}"

    # Check modal CLI
    if ! command -v modal &> /dev/null; then
        echo -e "${YELLOW}Installing Modal CLI...${NC}"
        pip install modal
    fi

    # Check if logged in
    if ! modal token status &> /dev/null; then
        echo -e "${YELLOW}Please authenticate with Modal:${NC}"
        modal token new
    fi

    # Create secret if not exists
    echo -e "${CYAN}Checking Modal secrets...${NC}"
    if ! modal secret list 2>/dev/null | grep -q "gemini-api-key"; then
        if [ -n "$GOOGLE_API_KEY" ]; then
            echo -e "${YELLOW}Creating gemini-api-key secret...${NC}"
            modal secret create gemini-api-key GOOGLE_API_KEY="$GOOGLE_API_KEY"
        elif [ -n "$GEMINI_API_KEY" ]; then
            echo -e "${YELLOW}Creating gemini-api-key secret...${NC}"
            modal secret create gemini-api-key GOOGLE_API_KEY="$GEMINI_API_KEY"
        else
            echo -e "${RED}❌ No API key available for Modal secret${NC}"
            echo -e "${YELLOW}   Run: modal secret create gemini-api-key GOOGLE_API_KEY=<your-key>${NC}"
            return 1
        fi
    fi

    # Deploy
    echo -e "${CYAN}Deploying Modal app...${NC}"
    modal deploy modal_app.py

    # Get URL
    MODAL_URL=$(modal app url juan-dev-code-hackathon 2>/dev/null || echo "")

    if [ -n "$MODAL_URL" ]; then
        echo -e "${GREEN}✅ Modal deployed successfully!${NC}"
        echo -e "${GREEN}   URL: ${MODAL_URL}${NC}"
    else
        echo -e "${GREEN}✅ Modal deployed!${NC}"
        echo -e "${CYAN}   Check: modal app list${NC}"
    fi
}

# Deploy to Blaxel
deploy_blaxel() {
    echo ""
    echo -e "${BLUE}🤖 Deploying to Blaxel...${NC}"

    # Check bl CLI
    if ! command -v bl &> /dev/null; then
        echo -e "${YELLOW}⚠️  Blaxel CLI (bl) not found${NC}"
        echo -e "${YELLOW}   Install from: https://docs.blaxel.ai/cli${NC}"
        echo -e "${CYAN}   Skipping Blaxel deployment...${NC}"
        return 0
    fi

    # Check if logged in
    if ! bl whoami &> /dev/null; then
        echo -e "${YELLOW}Please authenticate with Blaxel:${NC}"
        bl login
    fi

    # Deploy
    echo -e "${CYAN}Deploying Blaxel agent...${NC}"
    bl deploy --name juan-dev-agent

    # Get info
    BLAXEL_INFO=$(bl info juan-dev-agent 2>/dev/null || echo "")

    if [ -n "$BLAXEL_INFO" ]; then
        echo -e "${GREEN}✅ Blaxel agent deployed!${NC}"
        echo "$BLAXEL_INFO"
    else
        echo -e "${GREEN}✅ Blaxel deployment initiated!${NC}"
        echo -e "${CYAN}   Check: bl list${NC}"
    fi
}

# Run local Gradio
run_local() {
    echo ""
    echo -e "${BLUE}🖥️  Starting local Gradio UI...${NC}"

    # Install dependencies if needed
    if ! python3 -c "import gradio" 2>/dev/null; then
        echo -e "${YELLOW}Installing Gradio...${NC}"
        pip install gradio
    fi

    # Set port
    PORT=${GRADIO_SERVER_PORT:-7860}

    echo -e "${CYAN}Starting on port ${PORT}...${NC}"
    echo -e "${GREEN}Access at: http://localhost:${PORT}${NC}"
    echo ""

    # Run
    python3 -m gradio_ui.app
}

# Show summary
show_summary() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗"
    echo -e "║                    📊 Deployment Summary                      ║"
    echo -e "╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ -n "$MODAL_URL" ]; then
        echo -e "${GREEN}📦 Modal:  ${MODAL_URL}${NC}"
    fi

    if [ -n "$BLAXEL_INFO" ]; then
        echo -e "${GREEN}🤖 Blaxel: Deployed${NC}"
    fi

    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Test the deployed endpoints"
    echo "2. Submit to hackathon judges"
    echo "3. Prepare demo video"
    echo ""
    echo -e "${CYAN}Good luck with the hackathon! 🏆${NC}"
}

# Main
main() {
    check_prerequisites

    case "${1:-all}" in
        modal)
            deploy_modal
            ;;
        blaxel)
            deploy_blaxel
            ;;
        local)
            run_local
            ;;
        all)
            deploy_modal
            deploy_blaxel
            show_summary
            ;;
        *)
            echo "Usage: $0 {modal|blaxel|local|all}"
            echo ""
            echo "  modal   - Deploy to Modal (serverless)"
            echo "  blaxel  - Deploy to Blaxel (agent platform)"
            echo "  local   - Run local Gradio UI"
            echo "  all     - Deploy to all platforms (default)"
            exit 1
            ;;
    esac
}

main "$@"
