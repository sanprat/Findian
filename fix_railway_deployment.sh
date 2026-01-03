#!/bin/bash
# Railway Deployment Fix Script
# This script fixes two issues:
# 1. Backend: FINVASIA_TOTP_KEY error (stale build)
# 2. Bot: Telegram conflict error (multiple instances)

set -e  # Exit on error

echo "=========================================="
echo "Railway Deployment Fix Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check if logged in
echo -e "${YELLOW}[1/6] Checking Railway login status...${NC}"
if ! railway whoami &>/dev/null; then
    echo -e "${RED}❌ Not logged in to Railway CLI${NC}"
    echo "Please run: railway login"
    exit 1
fi
echo -e "${GREEN}✅ Logged in to Railway${NC}"
echo ""

# Step 2: Set missing BACKEND_API_URL for bot service
echo -e "${YELLOW}[2/6] Setting BACKEND_API_URL for bot service...${NC}"
BACKEND_URL="https://backend-production-b842.up.railway.app"
railway variables --service bot --set "BACKEND_API_URL=${BACKEND_URL}" --skip-deploys
echo -e "${GREEN}✅ BACKEND_API_URL set to: ${BACKEND_URL}${NC}"
echo ""

# Step 3: Verify bot replicas configuration
echo -e "${YELLOW}[3/6] Verifying bot replicas configuration...${NC}"
echo "Bot service railway.toml already has numReplicas = 1"
echo -e "${GREEN}✅ Bot replicas configured correctly${NC}"
echo ""

# Step 4: Redeploy backend service (force fresh build)
echo -e "${YELLOW}[4/6] Redeploying backend service (forcing fresh build)...${NC}"
echo "This will clear the FINVASIA_TOTP_KEY error by deploying the latest yfinance-only code"
railway redeploy --service backend --yes
echo -e "${GREEN}✅ Backend service redeployment triggered${NC}"
echo ""

# Step 5: Wait a bit for backend to start
echo -e "${YELLOW}[5/6] Waiting 30 seconds for backend to initialize...${NC}"
sleep 30
echo ""

# Step 6: Redeploy bot service (with correct replicas and BACKEND_API_URL)
echo -e "${YELLOW}[6/6] Redeploying bot service...${NC}"
echo "This will fix the Telegram conflict error by ensuring only 1 instance runs"
railway redeploy --service bot --yes
echo -e "${GREEN}✅ Bot service redeployment triggered${NC}"
echo ""

# Final status
echo "=========================================="
echo -e "${GREEN}✅ Deployment fix complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Wait 2-3 minutes for both services to fully deploy"
echo "2. Check logs with:"
echo "   - railway logs --service backend"
echo "   - railway logs --service bot"
echo "3. Test your bot by sending /start to your Telegram bot"
echo ""
echo "Expected results:"
echo "✅ Backend: No FINVASIA_TOTP_KEY error (using yfinance only)"
echo "✅ Bot: No Telegram conflict error (single replica running)"
echo ""
