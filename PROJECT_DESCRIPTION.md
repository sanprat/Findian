# Findian: AI-Powered Market Assistant 📈🤖

## Overview
Findian is a conversational fintech platform that allows users to interact with the stock market using natural language via a Telegram Bot. It bridges professional-grade data with a simple, chat-based interface.

## Core Capabilities

### 🗣️ Natural Language Interface
- Users can type command-free queries
- Examples: "Price of Reliance", "Alert me when TCS crosses 3500"
- AI engine interprets natural language to trigger actions
- No complex commands or syntax required

### ⚡ Hybrid Data Engine
Robust dual-source architecture ensuring 100% uptime:

**Primary Data Source (Market Hours):**
- Connects to Finvasia (Shoonya) for real-time data
- Provides tick-by-tick live market data
- Professional-grade trading data feed

**Fallback Data Source:**
- Automatically switches to Yahoo Finance
- Active on weekends, holidays, and downtime
- Ensures continuous chart and historical data access

### 🔔 Intelligent Alerts System
- Redis-backed monitoring for high performance
- Tracks price targets and technical indicators
- Real-time notifications pushed to users
- Custom alert conditions supported

### 🔍 Auto-Screener Service
Background scanning capabilities:
- Continuously scans Nifty 50 stocks
- Identifies technical signals (RSI, breakouts, volume spikes)
- Supports "Custom AI Scans" (e.g., "Show me stocks with RSI < 30")
- AI-powered pattern recognition

### 🐳 Microservices Architecture
- **Backend**: FastAPI for RESTful APIs
- **Frontend**: Python-Telegram-Bot for chat interface
- **Caching/PubSub**: Redis for real-time data and alerts
- **Database**: MySQL for persistent storage
- **Containerization**: Fully containerized with Docker

## Key Features

1. **Always-On Availability**: Hybrid data ensures 24/7 functionality
2. **Professional Data**: Real-time tick data from Shoonya during market hours
3. **Smart AI**: Natural language processing for intuitive interactions
4. **Instant Alerts**: Real-time notifications for price movements
5. **Automated Scanning**: Continuous market monitoring for opportunities
6. **User-Friendly**: Simple chat interface, no technical knowledge needed

## Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Python-Telegram-Bot
- **Real-time Data**: Finvasia (Shoonya) API
- **Fallback Data**: Yahoo Finance (yfinance)
- **Caching**: Redis
- **Database**: MySQL
- **Container**: Docker & Docker Compose
- **AI**: Natural Language Processing Engine

## Project Goal

To democratize algorithmic trading tools (Screeners, Alerts, Live Data) into a friendly, always-on chat assistant, making sophisticated trading features accessible to everyone through natural conversation.

## Memory System Integration

Findian includes an innovative Agent Memory System that enables AI agents to:
- Learn from user interactions and market patterns
- Remember successful alert configurations
- Share knowledge across different AI agents (Claude, Gemini, GPT)
- Maintain continuity of service
- Build on previous successful strategies

## Repository Structure

```
Findian/
├── backend/                    # FastAPI backend services
│   ├── app/
│   │   ├── core/              # Core trading logic
│   │   │   ├── ai.py          # AI and NLP processing
│   │   │   ├── market_data.py # Data integration (Finvasia/Yahoo)
│   │   │   ├── scanner.py     # Auto-screener logic
│   │   │   └── scheduler.py   # Background task scheduler
│   │   ├── db/                # Database models
│   │   └── main.py            # FastAPI application entry
├── bot/                       # Telegram bot frontend
│   └── main.py                # Bot logic and handlers
├── agent_memory.sh            # Memory system for AI agents
├── universal_agent_hooks.py   # Multi-agent integration
├── docker-compose.yml         # Container orchestration
└── MEMORY_SYSTEM.md           # Memory system documentation
```

## Agent Guidelines

AI agents working on Findian must follow the memory system rules in GEMINI.md/CLAUDE.md:
- Initialize memory before starting tasks
- Update memory after completing work
- Store decisions about trading logic
- Document alert configurations
- Learn from user feedback patterns

---

**Findian**: Making algorithmic trading as simple as sending a message 🚀