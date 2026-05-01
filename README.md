# TradeIQ — AI-Powered Personal Trade Assistant

A free AI-powered trade assistant for retail investors trading on the ASX and US markets.

## What it does
Enter a stock ticker, your entry price, and your target price. 
Optionally upload a price chart screenshot. TradeIQ will:

- Fetch live fundamentals (P/E, EPS, market cap, 52-week range)
- Show full dividend history and yield
- Analyse your uploaded chart for technical patterns
- Give you a plain-English AI verdict — Buy, Hold, or Sell

Built for both beginner traders who want guidance and experienced 
traders who want a fast, unbiased second opinion.

## How to use
**ASX stocks** — add .AX suffix e.g. `CBA.AX`, `BHP.AX`, `WES.AX`  
**US stocks** — ticker only e.g. `AAPL`, `TSLA`, `NVDA`

## Tech stack
- Python + Streamlit (frontend)
- yfinance (live market data)
- Anthropic Claude API (AI analysis)

## Setup
1. Clone this repo
2. Install dependencies: `pip install streamlit yfinance anthropic pillow`
3. Set your API key: `export ANTHROPIC_API_KEY="your-key-here"`
4. Run: `streamlit run streamlit_app.py`

## Disclaimer
This tool is for educational purposes only. 
Not financial advice. Always do your own research before trading.