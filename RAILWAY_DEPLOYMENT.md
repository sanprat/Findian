# Railway Deployment Guide for Pystock Bot

## Overview

This guide explains how to deploy Pystock Bot on Railway without Finvasia dependency (yfinance only).

## Railway Service Architecture

You need 3 services on Railway:

1. **MySQL Plugin** - Database
2. **Backend Service** - FastAPI API
3. **Bot Service** - Telegram Bot

---

## Step 1: Create Railway Project

1. Go to [railway.app](https://railway.app)
2. Create new project → "Deploy from GitHub repo"
3. Select your Pystock repository

---

## Step 2: Add MySQL Database

### 2.1 Add Database Plugin

1. In your Railway project, click **"New Service"**
2. Select **"Provision MySQL"**
3. This will create a MySQL database service

### 2.2 Get Database Variables

Once MySQL is provisioned:

1. Click on the MySQL service
2. Go to **Variables** tab
3. Copy the `DATABASE_URL` - it will look like:

```
mysql://root:CJidEZNkhwPMnUiCyaWZAiYXhamlDqMD@mysql.railway.internal:3306/railway
```

---

## Step 3: Configure Backend Service

### 3.1 Add Backend Service

1. Click **"New Service"** → **"Deploy from GitHub repo"**
2. Select same repository
3. Configure settings:

**Dockerfile Path:** `backend/Dockerfile`

**Start Command:**
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### 3.2 Backend Environment Variables

Add these variables:

| Variable | Value | Description |
|----------|-------|-------------|
| `DATABASE_URL` | (from MySQL service) | From MySQL Variables tab |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection (optional if no Redis) |
| `CHUTES_API_TOKEN` | `your_chutes_api_token` | Chutes AI API key |
| `ADMIN_IDS` | `your_telegram_id` | Your admin Telegram ID |
| `TESTER_ACCESS_CODE` | `your_test_code` | Optional tester code |
| `ALLOWED_ORIGINS` | `*` | CORS origins (for Railway) |

**Important:** Do NOT add database individual variables (DB_HOST, DB_USER, etc.) when using `DATABASE_URL`.

---

## Step 4: Configure Bot Service

### 4.1 Add Bot Service

1. Click **"New Service"** → **"Deploy from GitHub repo"**
2. Select same repository
3. Configure settings:

**Dockerfile Path:** `bot/Dockerfile`

**Start Command:**
```
python main.py
```

### 4.2 Bot Environment Variables

Add these variables:

| Variable | Value | Description |
|----------|-------|-------------|
| `TELEGRAM_BOT_TOKEN` | `your_bot_token` | From @BotFather |
| `BACKEND_API_URL` | (your backend URL) | **See below** |
| `WEBHOOK_URL` | (leave empty) | For polling mode |
| `PORT` | `8000` | Optional, defaults to 8443 |

### 4.3 How to Find BACKEND_API_URL

This is the **public URL of your Railway backend service**:

1. Go to your Backend Service on Railway
2. Click on the **"Networking"** or **"Domains"** tab
3. You'll see a URL like:

```
https://your-backend-service-name.up.railway.app
```

**Example:**
```
BACKEND_API_URL=https://pystock-backend-production.up.railway.app
```

---

## Step 5: Configure Bot Scaling (CRITICAL)

### 5.1 Limit Bot to 1 Replica

This prevents Telegram bot conflicts:

1. Go to your **Bot Service** on Railway
2. Click on **"Settings"**
3. Find the **"Scale"** or **"Replicas"** section
4. Set **Instances** to **1**

**Why?** Telegram allows only one bot instance to poll for updates simultaneously. Multiple replicas cause the "409 Conflict" error.

---

## Step 6: Deploy

1. All services will auto-deploy on first push
2. Wait for deployed status (green checkmark)
3. Check logs for errors

---

## Step 7: Remove Old Environment Variables

You mentioned seeing these still set. **DELETE THEM**:

From BOTH Backend and Bot services, remove:
- ❌ `FINVASIA_USER_ID`
- ❌ `FINVASIA_PASSWORD`
- ❌ `FINVASIA_TOKEN`
- ❌ `FINVASIA_TOTP_KEY`
- ❌ `FINVASIA_VENDOR_CODE`
- ❌ `FINVASIA_IMEI`
- ❌ `DB_ROOT_PASSWORD`
- ❌ `DB_HOST`
- ❌ `DB_USER`
- ❌ `DB_PASSWORD`
- ❌ `DB_NAME`

Keep only:
- ✅ `DATABASE_URL` (from MySQL service)
- ✅ `TELEGRAM_BOT_TOKEN`
- ✅ `BACKEND_API_URL` (bot only)

---

## Troubleshooting

### Bot Conflict Error (409)

**Error:** `Conflict: terminated by other getUpdates request`

**Solution:**
- Go to Bot Service → Settings → Scale
- Set replicas to **1**
- Redeploy service

### Database Connection Error

**Error:** `Could not connect to database`

**Solution:**
- Verify `DATABASE_URL` is set in Backend service
- Check MySQL service is running
- Make sure no individual DB variables are set (only `DATABASE_URL`)

### Bot Not Responding

**Check:**
1. `BACKEND_API_URL` is correct (use your Railway backend URL)
2. Bot replicas = 1
3. Review Bot Service logs

---

## Environment Variables Summary

### Backend Service Only:
```
DATABASE_URL=(from MySQL plugin)
REDIS_URL=redis://redis:6379/0
CHUTES_API_TOKEN=your_token
ADMIN_IDS=your_telegram_id
TESTER_ACCESS_CODE=your_code
ALLOWED_ORIGINS=*
```

### Bot Service Only:
```
TELEGRAM_BOT_TOKEN=your_token
BACKEND_API_URL=https://your-backend.up.railway.app
WEBHOOK_URL=
PORT=8000
```

### Both Services (Optional):
```
TELEGRAM_BOT_TOKEN=your_token
```

---

## Verification

1. **Backend Health:** Visit `https://your-backend.up.railway.app/health`
2. **Bot Test:** Send `/start` on Telegram to your bot
3. **Logs:** Check Railway logs for any errors

---

**Complete!** Your Pystock bot should now be running on Railway with yfinance data only, no Finvasia dependency.