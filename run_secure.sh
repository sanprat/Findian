#!/bin/bash
# Secure wrapper script to run the application
# Loads environment variables from secure location

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔒 Secure Application Launcher${NC}"
echo ""

# Check if .env exists in current directory
if [ -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file found in project directory${NC}"
    echo -e "${YELLOW}   File permissions: $(ls -la .env | awk '{print $1}')${NC}"
    
    # Check if permissions are secure
    if [ "$(stat -f %A .env 2>/dev/null || stat -c %a .env 2>/dev/null)" != "600" ]; then
        echo -e "${RED}❌ Insecure permissions detected!${NC}"
        echo -e "${GREEN}🔧 Fixing permissions...${NC}"
        chmod 600 .env
        echo -e "${GREEN}✓ Permissions fixed${NC}"
    fi
fi

# Function to validate environment
validate_env() {
    local missing=()
    
    # List of required environment variables
    required_vars=(
        "TELEGRAM_BOT_TOKEN"
        "API_SECRET_KEY"
        "DB_PASSWORD"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            missing+=("$var")
        fi
    done
    
    if [ ${#missing[@]} -ne 0 ]; then
        echo -e "${RED}❌ Missing required environment variables:${NC}"
        printf '  - %s\n' "${missing[@]}"
        return 1
    fi
    
    return 0
}

# Main execution
echo -e "${GREEN}✓ Environment security checks passed${NC}"
echo ""

# Determine what to run
case "${1:-backend}" in
    backend|api)
        echo -e "${GREEN}🚀 Starting Backend API...${NC}"
        cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        ;;
    bot|telegram)
        echo -e "${GREEN}🚀 Starting Telegram Bot...${NC}"
        cd bot && python main.py
        ;;
    *)
        echo "Usage: $0 [backend|bot]"
        echo ""
        echo "Examples:"
        echo "  $0 backend    # Start the backend API"
        echo "  $0 bot        # Start the Telegram bot"
        exit 1
        ;;
esac