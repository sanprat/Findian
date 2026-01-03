# Findian: AI-Powered Market Assistant 📈🤖

## Overview
Findian is a conversational fintech platform that allows users to interact with the stock market using natural language via a Telegram Bot. It bridges professional-grade data with a simple, chat-based interface.

## Core Capabilities

### 🗣️ Natural Language Interface
- Users can type command-free queries
- Examples: "Price of Reliance", "Alert me when TCS crosses 3500"
- AI engine interprets natural language to trigger actions
- No complex commands or syntax required

### ⚡ Data Engine
Robust yfinance-powered architecture ensuring 100% uptime:

- **Primary Data Source:** Yahoo Finance (yfinance)
- **Coverage:** Live 1-minute data + historical charts
- **Reliability:** Active 24/7 with zero login/session requirements
- **Resilience:** Built-in mock data fallback during API blackouts

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

1. **Always-On Availability**: 24/7 functionality with zero login overhead
2. **Reliable Data**: Accurate price and volume data via Yahoo Finance
3. **Smart AI**: Natural language processing for intuitive interactions
4. **Instant Alerts**: Real-time notifications for price movements
5. **Automated Scanning**: Continuous market monitoring for opportunities
6. **User-Friendly**: Simple chat interface, no technical knowledge needed

## Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Python-Telegram-Bot
- **Main Data Source**: Yahoo Finance (yfinance)
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
│   │   │   ├── market_data.py # Data integration (Yahoo Finance)
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