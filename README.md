# Findian

Findian: AI-Powered Market Assistant 📈🤖
Findian is a conversational fintech platform that allows users to interact with the stock market using natural language via a Telegram Bot. It bridges professional-grade data with a simple, chat-based interface.

Core Capabilities:

🗣️ Natural Language Interface: Users can type command-free queries like "Price of Reliance" or "Alert me when TCS crosses 3500" which are interpreted by an AI engine to trigger actions.
⚡ Hybrid Data Engine: Uses a robust dual-source architecture:
Primary: Connects to Finvasia (Shoonya) for real-time, tick-by-tick data during market hours.
Fallback: Automatically switches to Yahoo Finance on weekends/holidays to ensure 100% uptime for charts and historical data.
🔔 Intelligent Alerts: A Redis-backed monitoring system that tracks price targets and technical indicators in real-time, pushing instant notifications to the user.
🔍 Auto-Screener: A background service that continuously scans Nifty 50 stocks for technical signals (RSI, breakouts, volume spikes) and provides "Custom AI Scans" (e.g., "Show me stocks with RSI < 30").
🐳 Microservices Architecture: Built with FastAPI (Backend), Python-Telegram-Bot (Frontend), Redis (Caching/PubSub), and MySQL, fully containerized with Docker.
Goal: To democratize algorithmic trading tools (Screeners, Alerts, Live Data) into a friendly, always-on chat assistant.