# Railway Deployment Guide for Pystock

Railway.app is an excellent choice for this project due to its ease of use and generous resource limits.

## 1. Prerequisites
- A [Railway.app](https://railway.app) account.
- **Railway CLI** installed on your Mac (`brew install railway`).
- Your Pystock code local on your Mac.

## 2. Deployment Steps (via CLI)

### A. Login and Initialize
1. Open terminal on your Mac in the Pystock folder.
2. Run `railway login` (it will open a browser window).
3. Run `railway init` and choose **"Create New Project"**.

### B. Add Services
Inside the Railway web dashboard:
1. Click **New** -> **Database** -> **MySQL**.
2. Click **New** -> **Database** -> **Redis**.

### C. Configure Service Variables (Dashboard is Recommended)
1. Go to your [Railway Project Dashboard](https://railway.com/project/02bf1ab7-1cb9-4159-9ce4-1c4f3e85b1c7).
2. Click on the **Backend** service (when it appears after deployment) or add variables to the project scope.
3. **CRITICAL**: For secrets like `TELEGRAM_BOT_TOKEN`, `FINVASIA_PASSWORD`, and `CHUTES_API_TOKEN`, use the Railway UI to paste them. This keeps them out of your shell history.

**Mapping for Database & Redis:**
Railway will provide variables automatically. You should map them like this:
- `DATABASE_URL`: `${{MySQL.MYSQL_URL}}`
- `REDIS_URL`: `${{Redis.REDIS_URL}}`

### D. Deploy Code
Back in your terminal:
1. Run `railway up`. 
2. Railway will process your `docker-compose.yml`, build the `backend` and `bot` images, and link them to the provisioned DB/Redis.

### D. Networking
1. Go to the **Backend** service settings.
2. Under **Networking**, click **Generate Domain** to get a public URL for your API.

---

## 3. Why Railway?
- **8GB RAM**: Plenty of room for AI calculations and stock scans.
- **Automatic SSL**: Your API will have a secure `https://` domain automatically.
- **Auto-Scale**: Railway handles restarts and health checks for you.
- **Managed DB**: No more manual MySQL installation or swap files.
