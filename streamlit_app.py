"""
TradeIQ — AI-Powered Personal Trade Assistant
Streamlit Frontend
"""

import os
import base64
import math
import streamlit as st
from PIL import Image
from io import BytesIO
import yfinance as yf
import anthropic

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TradeIQ — Personal Trade Assistant",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.4rem;
        font-weight: 700;
        color: #1f4e79;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #1f4e79;
        margin-bottom: 0.8rem;
    }
    .verdict-buy {
        background: #d4edda;
        border: 2px solid #28a745;
        border-radius: 10px;
        padding: 1.2rem;
        font-size: 1.1rem;
    }
    .verdict-sell {
        background: #f8d7da;
        border: 2px solid #dc3545;
        border-radius: 10px;
        padding: 1.2rem;
        font-size: 1.1rem;
    }
    .verdict-hold {
        background: #fff3cd;
        border: 2px solid #ffc107;
        border-radius: 10px;
        padding: 1.2rem;
        font-size: 1.1rem;
    }
    .disclaimer {
        background: #f1f3f4;
        border-radius: 8px;
        padding: 0.8rem;
        font-size: 0.8rem;
        color: #888;
        margin-top: 1rem;
    }
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1f4e79;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 0.3rem;
        margin-bottom: 0.8rem;
    }
    .upside-positive { color: #28a745; font-weight: 700; font-size: 1.3rem; }
    .upside-negative { color: #dc3545; font-weight: 700; font-size: 1.3rem; }
    div[data-testid="stExpander"] { border: 1px solid #e0e0e0; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


# ── HELPERS ──────────────────────────────────────────────────────────────────
def fmt_currency(val, currency="USD"):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    sym = "$"
    if val >= 1_000_000_000:
        return f"{sym}{val/1_000_000_000:.2f}B"
    elif val >= 1_000_000:
        return f"{sym}{val/1_000_000:.2f}M"
    else:
        return f"{sym}{val:,.2f}"

def fmt_pct(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    return f"{val*100:.2f}%"

def fmt_float(val, decimals=2):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    return f"{val:.{decimals}f}"

def safe(val):
    if val is None:
        return "N/A"
    try:
        if math.isnan(float(val)):
            return "N/A"
    except (TypeError, ValueError):
        pass
    return val


# ── DATA FETCH ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_fundamentals(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    info  = stock.info

    name     = info.get("longName") or info.get("shortName") or ticker.upper()
    currency = info.get("currency", "USD")

    # Dividend history
    try:
        div_history = stock.dividends
        if div_history is not None and len(div_history) > 0:
            recent = div_history.tail(8)
            div_history_str = "\n".join(
                [f"  {d.strftime('%b %Y')}: ${v:.3f}" for d, v in recent.items()]
            )
            pays_dividends = True
        else:
            div_history_str = "No dividend history"
            pays_dividends = False
    except Exception:
        div_history_str = "Could not retrieve"
        pays_dividends = info.get("dividendYield") is not None

    return {
        "ticker":          ticker.upper(),
        "name":            name,
        "sector":          info.get("sector", "N/A"),
        "industry":        info.get("industry", "N/A"),
        "country":         info.get("country", "N/A"),
        "exchange":        info.get("exchange", "N/A"),
        "currency":        currency,
        "current_price":   info.get("currentPrice") or info.get("regularMarketPrice"),
        "prev_close":      info.get("previousClose"),
        "week52_high":     info.get("fiftyTwoWeekHigh"),
        "week52_low":      info.get("fiftyTwoWeekLow"),
        "market_cap":      info.get("marketCap"),
        "pe_ratio":        info.get("trailingPE"),
        "forward_pe":      info.get("forwardPE"),
        "eps":             info.get("trailingEps"),
        "price_to_book":   info.get("priceToBook"),
        "beta":            info.get("beta"),
        "pays_dividends":  pays_dividends,
        "div_yield":       info.get("dividendYield"),
        "div_rate":        info.get("dividendRate"),
        "payout_ratio":    info.get("payoutRatio"),
        "div_history":     div_history_str,
        "total_revenue":   info.get("totalRevenue"),
        "gross_margins":   info.get("grossMargins"),
        "profit_margins":  info.get("profitMargins"),
        "revenue_growth":  info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "debt_to_equity":  info.get("debtToEquity"),
        "current_ratio":   info.get("currentRatio"),
        "roe":             info.get("returnOnEquity"),
        "target_mean":     info.get("targetMeanPrice"),
        "target_high":     info.get("targetHighPrice"),
        "target_low":      info.get("targetLowPrice"),
        "analyst_rating":  (info.get("recommendationKey") or "N/A").upper(),
        "analyst_count":   info.get("numberOfAnalystOpinions", 0),
    }


# ── IMAGE ENCODE ─────────────────────────────────────────────────────────────
def encode_image(uploaded_file) -> tuple:
    try:
        img = Image.open(uploaded_file)
        max_dim = 1568
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
        return b64, "image/png"
    except Exception as e:
        st.warning(f"Could not process image: {e}")
        return None, None


# ── CLAUDE PROMPT ─────────────────────────────────────────────────────────────
def build_prompt(data: dict, current_price: float, target_price: float, has_chart: bool) -> str:
    upside = ((target_price - current_price) / current_price) * 100 if current_price else 0
    cur    = data["currency"]

    return f"""You are TradeIQ, an AI-powered personal trade assistant.
Analyse this stock and provide a structured trade assessment.

=== TRADE DETAILS ===
Ticker: {data['ticker']} | Company: {data['name']}
Exchange: {data['exchange']} ({data['country']}) | Sector: {data['sector']}
Entry price: {current_price:.2f} {cur} | Target price: {target_price:.2f} {cur}
Implied move: {upside:+.2f}%

=== MARKET DATA ===
Current price: {fmt_float(data['current_price'])} | Prev close: {fmt_float(data['prev_close'])}
52-week high: {fmt_float(data['week52_high'])} | 52-week low: {fmt_float(data['week52_low'])}
Market cap: {fmt_currency(data['market_cap'], cur)} | Beta: {fmt_float(data['beta'])}

=== VALUATION ===
P/E: {fmt_float(data['pe_ratio'])} | Forward P/E: {fmt_float(data['forward_pe'])}
EPS: {fmt_float(data['eps'])} | P/Book: {fmt_float(data['price_to_book'])}

=== DIVIDENDS ===
Pays dividends: {'Yes' if data['pays_dividends'] else 'No'}
Yield: {fmt_pct(data['div_yield'])} | Annual rate: {fmt_float(data['div_rate'])} {cur}
Payout ratio: {fmt_pct(data['payout_ratio'])}
Recent history:
{data['div_history']}

=== FINANCIALS ===
Revenue: {fmt_currency(data['total_revenue'], cur)} | Gross margin: {fmt_pct(data['gross_margins'])}
Profit margin: {fmt_pct(data['profit_margins'])} | Revenue growth: {fmt_pct(data['revenue_growth'])}
Earnings growth: {fmt_pct(data['earnings_growth'])} | Debt/Equity: {fmt_float(data['debt_to_equity'])}
Current ratio: {fmt_float(data['current_ratio'])} | ROE: {fmt_pct(data['roe'])}

=== ANALYST CONSENSUS ===
Rating: {data['analyst_rating']} ({data['analyst_count']} analysts)
Mean target: {fmt_float(data['target_mean'])} | Range: {fmt_float(data['target_low'])} – {fmt_float(data['target_high'])} {cur}

{'=== CHART === A price chart image has been uploaded. Please analyse it.' if has_chart else '=== CHART === No chart provided. Comment on 52-week range momentum only.'}

=== YOUR TASK ===
Respond with EXACTLY these four sections:

**1. COMPANY SNAPSHOT**
2-3 sentences: what the company does, its market position, key financial health observations.

**2. CHART ANALYSIS**
{'Analyse the uploaded chart: trend direction, key support/resistance levels, any visible patterns (head and shoulders, double bottom, consolidation, breakout etc). Be specific.' if has_chart else 'No chart provided. Comment on what the 52-week range data implies about recent price momentum.'}

**3. TRADE ASSESSMENT**
Assess the trader's plan: entry {current_price:.2f}, target {target_price:.2f} ({upside:+.2f}% required).
How does the target compare to analyst consensus? Is it realistic? What is the key risk?

**4. VERDICT**
State: BUY / HOLD / SELL — then 3-4 sentences explaining why.
Be honest. If data is mixed, say so. End with one sentence on what would change your verdict.

Keep total response under 500 words. Plain English — suitable for beginners but useful for experienced traders.
End with: "⚠️ This is AI-generated analysis for educational purposes only. Not financial advice."
"""


# ── CALL CLAUDE ──────────────────────────────────────────────────────────────
def call_claude(api_key: str, prompt: str, image_b64: str = None, media_type: str = None) -> str:
    client = anthropic.Anthropic(api_key=api_key)

    if image_b64 and media_type:
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
            {"type": "text", "text": prompt}
        ]
    else:
        content = prompt

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": content}]
    )
    return message.content[0].text


# ── RENDER DASHBOARD ─────────────────────────────────────────────────────────
def render_dashboard(data: dict, current_price: float, target_price: float, ai_response: str):
    upside = ((target_price - current_price) / current_price) * 100

    st.markdown("---")
    st.markdown(f"## 📊 {data['name']} ({data['ticker']})")
    st.caption(f"{data['exchange']} · {data['sector']} · {data['country']}")

    # ── Top metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Current Price", f"${fmt_float(data['current_price'])}")
    with col2:
        st.metric("Your Entry", f"${fmt_float(current_price)}")
    with col3:
        arrow = "▲" if upside >= 0 else "▼"
        color_label = f"{arrow} {abs(upside):.1f}% to target"
        st.metric("Target Price", f"${fmt_float(target_price)}", delta=f"{upside:+.1f}%")
    with col4:
        st.metric("Market Cap", fmt_currency(data['market_cap'], data['currency']))
    with col5:
        rating = data['analyst_rating']
        st.metric("Analyst Rating", rating if rating != "N/A" else "—")

    st.markdown("---")

    # ── Four panel layout
    left, right = st.columns([1, 1])

    with left:
        # Valuation
        with st.expander("📋 Valuation & Fundamentals", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                st.metric("P/E Ratio",     safe(fmt_float(data['pe_ratio'])))
                st.metric("Forward P/E",   safe(fmt_float(data['forward_pe'])))
                st.metric("EPS",           f"${safe(fmt_float(data['eps']))}")
                st.metric("Price/Book",    safe(fmt_float(data['price_to_book'])))
            with c2:
                st.metric("Beta",          safe(fmt_float(data['beta'])))
                st.metric("52W High",      f"${safe(fmt_float(data['week52_high']))}")
                st.metric("52W Low",       f"${safe(fmt_float(data['week52_low']))}")
                st.metric("Debt/Equity",   safe(fmt_float(data['debt_to_equity'])))

        # Financials
        with st.expander("💰 Financials", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Revenue",        fmt_currency(data['total_revenue'], data['currency']))
                st.metric("Gross Margin",   safe(fmt_pct(data['gross_margins'])))
                st.metric("Profit Margin",  safe(fmt_pct(data['profit_margins'])))
            with c2:
                st.metric("Rev. Growth",    safe(fmt_pct(data['revenue_growth'])))
                st.metric("EPS Growth",     safe(fmt_pct(data['earnings_growth'])))
                st.metric("ROE",            safe(fmt_pct(data['roe'])))

    with right:
        # Dividends
        with st.expander("💵 Dividends", expanded=True):
            if data['pays_dividends']:
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Dividend Yield",   safe(fmt_pct(data['div_yield'])))
                    st.metric("Annual Dividend",  f"${safe(fmt_float(data['div_rate']))}")
                with c2:
                    st.metric("Payout Ratio",     safe(fmt_pct(data['payout_ratio'])))
                    st.metric("Current Ratio",    safe(fmt_float(data['current_ratio'])))
                st.markdown("**Recent dividend history:**")
                st.code(data['div_history'])
            else:
                st.info("This stock does not pay dividends.")

        # Analyst targets
        with st.expander("🎯 Analyst Targets", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Mean Target",  f"${safe(fmt_float(data['target_mean']))}")
            with c2:
                st.metric("High Target",  f"${safe(fmt_float(data['target_high']))}")
            with c3:
                st.metric("Low Target",   f"${safe(fmt_float(data['target_low']))}")
            st.caption(f"Based on {data['analyst_count']} analyst opinions")

    # ── AI Analysis
    st.markdown("---")
    st.markdown("### 🤖 AI Trade Assessment")

    # Parse verdict for colour coding
    response_upper = ai_response.upper()
    if "VERDICT" in response_upper:
        if "BUY" in response_upper[response_upper.find("VERDICT"):response_upper.find("VERDICT")+100]:
            verdict_class = "verdict-buy"
        elif "SELL" in response_upper[response_upper.find("VERDICT"):response_upper.find("VERDICT")+100]:
            verdict_class = "verdict-sell"
        else:
            verdict_class = "verdict-hold"
    else:
        verdict_class = "verdict-hold"

    st.markdown(ai_response)

    st.markdown("""
    <div class="disclaimer">
    ⚠️ TradeIQ is an AI-powered educational tool. This analysis is not financial advice.
    Always conduct your own research and consult a licensed financial adviser before trading.
    Past performance is not indicative of future results.
    </div>
    """, unsafe_allow_html=True)


# ── SIDEBAR ──────────────────────────────────────────────────────────────────
def render_sidebar():
    st.sidebar.markdown("## ⚙️ TradeIQ Settings")
    st.sidebar.markdown("---")

    # API Key
    st.sidebar.markdown("**Anthropic API Key**")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        api_key = st.sidebar.text_input(
            "Paste your API key",
            type="password",
            placeholder="sk-ant-...",
            help="Get a free key at console.anthropic.com"
        )
    else:
        st.sidebar.success("✓ API key loaded from environment")

    st.sidebar.markdown("---")
    st.sidebar.markdown("**How to use TradeIQ**")
    st.sidebar.markdown("""
1. Enter a stock ticker
2. Enter your entry & target price
3. Optionally upload a chart screenshot
4. Click **Analyse**

**ASX stocks** → add `.AX` suffix
e.g. `CBA.AX`, `BHP.AX`, `WES.AX`

**US stocks** → ticker only
e.g. `AAPL`, `TSLA`, `NVDA`
    """)

    st.sidebar.markdown("---")
    st.sidebar.markdown("**About TradeIQ**")
    st.sidebar.caption(
        "TradeIQ combines live market data with Claude AI to give retail traders "
        "a fast, unbiased second opinion — for free. Built as part of an Applied AI "
        "in Finance project."
    )

    return api_key


# ── MAIN APP ──────────────────────────────────────────────────────────────────
def main():
    # Header
    st.markdown('<div class="main-header">📈 TradeIQ</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Your AI-powered personal trade assistant — ASX & US markets</div>',
                unsafe_allow_html=True)

    api_key = render_sidebar()

    # ── Input form
    with st.form("trade_form"):
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            ticker = st.text_input(
                "Stock Ticker",
                placeholder="e.g. AAPL or CBA.AX",
                help="ASX stocks need .AX suffix (e.g. BHP.AX). US stocks are just the ticker (e.g. TSLA)."
            ).strip().upper()

        with col2:
            current_price = st.number_input(
                "Your Entry Price ($)",
                min_value=0.01,
                value=100.00,
                step=0.01,
                format="%.2f"
            )

        with col3:
            target_price = st.number_input(
                "Your Target Price ($)",
                min_value=0.01,
                value=115.00,
                step=0.01,
                format="%.2f"
            )

        chart_file = st.file_uploader(
            "Upload Chart Image (optional — screenshot from TradingView or any platform)",
            type=["png", "jpg", "jpeg", "webp"],
            help="Upload a price chart screenshot for technical pattern analysis."
        )

        submitted = st.form_submit_button("🔍 Analyse", use_container_width=True, type="primary")

    # ── On submit
    if submitted:
        if not ticker:
            st.error("Please enter a stock ticker.")
            return
        if not api_key:
            st.error("Please enter your Anthropic API key in the sidebar.")
            return
        if current_price <= 0 or target_price <= 0:
            st.error("Please enter valid prices.")
            return

        # Show upside preview
        upside = ((target_price - current_price) / current_price) * 100
        if upside >= 0:
            st.success(f"📈 Target implies **+{upside:.1f}%** upside from your entry price.")
        else:
            st.warning(f"📉 Target implies **{upside:.1f}%** downside from your entry price.")

        # Fetch data
        with st.spinner(f"Fetching live data for {ticker}..."):
            try:
                data = fetch_fundamentals(ticker)
            except Exception as e:
                st.error(f"Could not fetch data for '{ticker}'. Check the ticker symbol is correct.\n\nError: {e}")
                return

        if not data.get("current_price"):
            st.error(f"No price data found for '{ticker}'. "
                     f"Make sure ASX stocks have .AX suffix (e.g. CBA.AX).")
            return

        st.success(f"✓ Data loaded for {data['name']}")

        # Encode chart if provided
        image_b64, media_type = None, None
        has_chart = False
        if chart_file:
            with st.spinner("Processing chart image..."):
                image_b64, media_type = encode_image(chart_file)
                has_chart = image_b64 is not None
            if has_chart:
                st.success("✓ Chart image loaded — AI will include technical analysis")
                with st.expander("Preview uploaded chart"):
                    st.image(chart_file)

        # Call Claude
        with st.spinner("Analysing with Claude AI — this takes about 10 seconds..."):
            try:
                prompt   = build_prompt(data, current_price, target_price, has_chart)
                response = call_claude(api_key, prompt, image_b64, media_type)
            except anthropic.AuthenticationError:
                st.error("Invalid API key. Check your key at console.anthropic.com")
                return
            except Exception as e:
                st.error(f"AI analysis failed: {e}")
                return

        # Render dashboard
        render_dashboard(data, current_price, target_price, response)

    else:
        # Landing state
        st.markdown("---")
        st.markdown("### 👋 Welcome to TradeIQ")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### 📊 Live Fundamentals")
            st.markdown("P/E ratio, EPS, market cap, 52-week range, revenue, margins and more — pulled live from Yahoo Finance.")
        with c2:
            st.markdown("#### 💵 Dividend Analysis")
            st.markdown("Full dividend history, yield, payout ratio. Know whether a stock rewards long-term holders.")
        with c3:
            st.markdown("#### 🤖 AI Verdict")
            st.markdown("Upload your chart for technical analysis. Get a plain-English buy/hold/sell with honest reasoning.")

        st.markdown("---")
        st.caption("Enter a ticker in the form above to get started. Try **AAPL**, **TSLA**, **BHP.AX** or **CBA.AX**.")


if __name__ == "__main__":
    main()