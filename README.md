# Findian: AI-Powered Market Assistant 📈🤖

[![Implementation Status](https://img.shields.io/badge/Status-85%25%20Complete-green)](http://localhost:8443/sanprat/Findian)
[![License](https://img.shields.io/badge/License-AGPL%203.0-blue.svg)](LICENSE)

A conversational fintech platform that allows users to interact with the stock market using natural language via Telegram Bot. Findian bridges professional-grade data with a simple, chat-based interface.

## 🚀 Current Status: **85% Complete**

### ✅ **Completed Features (MVP)**

1. **Core Architecture**
   - ✅ Microservices: FastAPI Backend + Telegram Bot Frontend
   - ✅ Database: MySQL (Relational) + Redis (Real-time PubSub)
   - ✅ AI Engine: Chutes AI (Llama 3.3) for Intent Parsing & Smart Clarification

2. **Market Data Engine**
   - ✅ Hybrid Feed: Intelligent switching (Finvasia Live ↔ Yahoo Finance Fallback)
   - ✅ Hyper-Precision: 1-minute Price + Daily Volume/High/Low accuracy
   - ✅ Resilience: Mock Data simulation during API blackouts

3. **Telegram Interface**
   - ✅ Conversational UI: Natural language commands ("Price of Reliance", "Alert if TCS > 3000")
   - ✅ Financial Formatting: Consistent ₹1,234.50 format
   - ✅ Interactive Menus: Screener, Portfolio, Disclaimer inline buttons

4. **Core Features**
   - ✅ Smart Alerts: Redis-backed instant monitoring
   - ✅ AI Screener: Custom scans ("RSI < 30") + Pre-built strategies
   - ✅ Basic Portfolio: Add/View holdings with real-time P&L

### ⏳ **In Progress (Next 15%)**

1. **Portfolio Management** *(Critical)*
   - ⏳ Sell Logic & Position Exit
   - ⏳ Tax & Fees Calculation
   - ⏳ Daily Portfolio Reports (5:00 PM cron)

2. **Monetization & Security**
   - ⏳ User Tiers (Free vs Premium limits)
   - ⏳ Access Control for Pro features
   - ⏳ API Key Encryption

3. **Cloud Deployment**
   - ⏳ Webhooks for <100ms latency
   - ⏳ Production Server (AWS/DigitalOcean)

## Core Capabilities

### 🗣️ Natural Language Interface
Users can type command-free queries like:
- "Price of Reliance"
- "Alert me when TCS crosses 3500"
- "Show me stocks with RSI < 30"

### ⚡ Hybrid Data Engine
- **Primary**: Finvasia (Shoonya) for real-time, tick-by-tick data during market hours
- **Fallback**: Yahoo Finance on weekends/holidays for 100% uptime

### 🔔 Intelligent Alerts
- Redis-backed monitoring system
- Real-time price target and technical indicator tracking
- Instant notifications to users

### 🔍 Auto-Screener
- Continuous Nifty 50 scanning
- Technical signals (RSI, breakouts, volume spikes)
- Custom AI Scans based on natural language

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | Python-Telegram-Bot |
| **Backend** | FastAPI |
| **AI Engine** | Chutes AI (Llama 3.3) |
| **Database** | MySQL + Redis |
| **Data Feeds** | Finvasia (Shoonya) + Yahoo Finance |
| **Container** | Docker |
| **Memory System** | Agent Memory for AI persistence |

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone http://localhost:8443/sanprat/Findian.git
   cd Findian
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Run with Docker**
   ```bash
   docker-compose up -d
   ```

4. **Start the bot**
   ```bash
   python bot/main.py
   ```

5. **Try commands on Telegram**
   - `/start` - Begin your journey
   - "Price of Reliance" - Get current price
   - "Alert me when TCS crosses 3500" - Set price alert
   - "Show me stocks with RSI < 30" - AI screener

## 📋 Agent Memory System

Findian includes an innovative **Agent Memory System** that enables AI agents to:
- Learn from user interactions
- Remember successful strategies
- Share knowledge across sessions
- Maintain project continuity

**All AI agents must follow memory guidelines in `GEMINI.md`**

## 📁 Project Structure

```
Findian/
├── backend/                    # FastAPI backend services
│   ├── app/
│   │   ├── core/              # Core trading logic
│   │   │   ├── ai.py          # AI and NLP processing
│   │   │   ├── market_data.py # Data integration
│   │   │   ├── scanner.py     # Auto-screener logic
│   │   │   └── scheduler.py   # Task scheduler
│   │   ├── db/                # Database models
│   │   └── main.py            # FastAPI entry
├── bot/                       # Telegram bot frontend
│   └── main.py                # Bot logic
├── agent_memory.sh            # Memory system
├── universal_agent_hooks.py   # Multi-agent integration
└── docker-compose.yml         # Container orchestration
```

## 🔮 Roadmap

- [ ] Portfolio sell functionality
- [ ] Tax calculation engine
- [ ] Daily portfolio reports
- [ ] Premium subscription tiers
- [ ] Cloud webhook deployment
- [ ] Mobile app companion

## 📊 Usage Examples

### Natural Language Commands
```
User: "What's the price of Infosys?"
Bot: "₹1,456.30 ▲ +12.50 (+0.86%)"

User: "Alert me if Reliance goes above 2500"
Bot: "✅ Alert set: Notify when RELIANCE > ₹2,500"

User: "Show me oversold stocks"
Bot: "🔍 Found 5 stocks with RSI < 30: [List]"
```

## 🤝 Contributing

This project uses AI agent collaboration with memory persistence. All agents follow guidelines in `GEMINI.md` for consistent development.

---

**Findian**: Democratizing algorithmic trading through conversation 💬📈

## 📜 License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.