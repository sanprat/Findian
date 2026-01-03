# Railway CLI Fix Guide

This guide shows you how to fix both deployment issues using Railway CLI.

## Issues to Fix

1. **Backend Error**: `FINVASIA_TOTP_KEY is missing!` (stale build with old code)
2. **Bot Error**: `telegram.error.Conflict: terminated by other getUpdates request` (multiple instances)

---

## Option 1: Automated Script (Recommended)

We've created a script that fixes everything automatically:

```bash
./fix_railway_deployment.sh
```

This script will:
- ✅ Set the missing `BACKEND_API_URL` variable for the bot
- ✅ Redeploy backend with fresh build (fixes FINVASIA error)
- ✅ Redeploy bot with correct configuration (fixes conflict error)

---

## Option 2: Manual CLI Commands

If you prefer to run commands manually:

### Step 1: Set Backend URL for Bot
```bash
railway variables --service bot --set "BACKEND_API_URL=https://backend-production-b842.up.railway.app" --skip-deploys
```

### Step 2: Redeploy Backend (Force Fresh Build)
```bash
railway redeploy --service backend --yes
```

**What this does**: Rebuilds backend from latest code (no FINVASIA dependencies)

### Step 3: Wait for Backend
```bash
# Wait 30-60 seconds for backend to start
sleep 30
```

### Step 4: Redeploy Bot (Single Instance)
```bash
railway redeploy --service bot --yes
```

**What this does**: Restarts bot with the numReplicas=1 setting from railway.toml

---

## Verify Deployment

### Check Backend Logs
```bash
railway logs --service backend
```

**Expected**: No "FINVASIA_TOTP_KEY" errors, only yfinance messages

### Check Bot Logs
```bash
railway logs --service bot
```

**Expected**: No "Conflict: terminated by other getUpdates" errors

### Test Bot
Send `/start` to your Telegram bot

---

## Additional Useful Commands

### View All Variables
```bash
# Backend variables
railway variables --service backend --json

# Bot variables
railway variables --service bot --json
```

### Monitor Deployment Status
```bash
railway service status
```

### View Real-time Logs
```bash
# Backend logs (follow mode)
railway logs --service backend -f

# Bot logs (follow mode)
railway logs --service bot -f
```

### Check Project Status
```bash
railway status
```

---

## Troubleshooting

### If Backend Still Shows FINVASIA Error

The code has been updated to use yfinance only. This error means Railway is using a cached build. Try:

```bash
# Force complete rebuild by triggering from specific directory
cd backend
railway up --service backend
cd ..
```

### If Bot Still Shows Conflict Error

Verify replicas setting:
```bash
cat bot/railway.toml | grep numReplicas
```

Should show: `numReplicas = 1`

If missing, add it manually and redeploy:
```bash
railway redeploy --service bot --yes
```

### If Backend URL is Wrong

Get the correct URL:
```bash
railway domain --service backend
```

Then update bot variable:
```bash
railway variables --service bot --set "BACKEND_API_URL=YOUR_BACKEND_URL"
```

---

## What Changed in the Code

✅ **Removed**: All Finvasia dependencies (ShooinyaApiPy, TOTP keys, etc.)  
✅ **Added**: Pure yfinance implementation in `market_data.py`  
✅ **Fixed**: Bot railway.toml includes `numReplicas = 1`  

The current codebase is ready - this is purely a deployment configuration issue.

---

## Environment Variables Summary

### Backend Service
```
DATABASE_URL=mysql://... (from Railway MySQL plugin)
REDIS_URL=redis://...
CHUTES_API_TOKEN=your_token
ADMIN_IDS=your_telegram_id
TESTER_ACCESS_CODE=your_code
```

### Bot Service
```
TELEGRAM_BOT_TOKEN=your_bot_token
BACKEND_API_URL=https://backend-production-b842.up.railway.app
```

**Note**: No FINVASIA_* variables should exist in either service.
