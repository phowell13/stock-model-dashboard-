import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Breakout Scanner", layout="wide")

st.title("Stock Breakout Scanner")

tickers_input = st.sidebar.text_area(
    "Enter tickers",
    value="CARR, AAPL, MSFT, NVDA, JCI, TT, HON"
)

period = st.sidebar.selectbox("Period", ["1y", "2y", "5y"], index=1)

tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]


@st.cache_data
def load_price_data(ticker, period):
    data = yf.download(
        ticker,
        period=period,
        auto_adjust=True,
        progress=False
    )

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.dropna()

    return data


def add_indicators(df):
    df = df.copy()

    df["Return"] = df["Close"].pct_change()

    df["MA_20"] = df["Close"].rolling(20).mean()
    df["MA_50"] = df["Close"].rolling(50).mean()
    df["MA_200"] = df["Close"].rolling(200).mean()

    df["Volume_MA_20"] = df["Volume"].rolling(20).mean()

    df["Resistance_50d"] = df["Close"].rolling(50).max().shift(1)
    df["Support_50d"] = df["Close"].rolling(50).min().shift(1)

    df["BB_Middle"] = df["Close"].rolling(20).mean()
    df["BB_Std"] = df["Close"].rolling(20).std()
    df["BB_Upper"] = df["BB_Middle"] + 2 * df["BB_Std"]
    df["BB_Lower"] = df["BB_Middle"] - 2 * df["BB_Std"]
    df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / df["BB_Middle"]

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR_14"] = true_range.rolling(14).mean()

    return df


def calculate_breakout_score(df):
    latest = df.iloc[-1]
    score = 0
    reasons = []

    squeeze_threshold = df["BB_Width"].rolling(120).quantile(0.2).iloc[-1]

    if latest["BB_Width"] < squeeze_threshold:
        score += 25
        reasons.append("Volatility squeeze")

    if latest["Close"] > latest["Resistance_50d"]:
        score += 25
        reasons.append("Price broke 50-day resistance")

    if latest["Volume"] > latest["Volume_MA_20"] * 1.5:
        score += 20
        reasons.append("Strong volume confirmation")

    if latest["Close"] > latest["MA_50"] and latest["MA_50"] > latest["MA_200"]:
        score += 15
        reasons.append("Strong uptrend")

    if 50 < latest["RSI"] < 70:
        score += 15
        reasons.append("Healthy RSI momentum")

    if not reasons:
        reasons.append("No major breakout signal yet")

    return score, ", ".join(reasons)


results = []

for ticker in tickers:
    try:
        df = load_price_data(ticker, period)
        df = add_indicators(df)
        df = df.dropna()

        if len(df) < 200:
            continue

        score, reasons = calculate_breakout_score(df)
        latest = df.iloc[-1]

        results.append({
            "Ticker": ticker,
            "Close": round(latest["Close"], 2),
            "Breakout Score": score,
            "RSI": round(latest["RSI"], 1),
            "Volume vs 20D Avg": round(latest["Volume"] / latest["Volume_MA_20"], 2),
            "Above 50D Resistance": latest["Close"] > latest["Resistance_50d"],
            "Signal": reasons
        })

    except Exception as e:
        st.warning(f"Could not load {ticker}: {e}")


results_df = pd.DataFrame(results)

st.subheader("Breakout Scanner Results")

if not results_df.empty:
    results_df = results_df.sort_values("Breakout Score", ascending=False)
    st.dataframe(results_df, use_container_width=True)

    selected_ticker = st.selectbox(
        "Select ticker to chart",
        results_df["Ticker"].tolist()
    )

    df = load_price_data(selected_ticker, period)
    df = add_indicators(df)
    df = df.dropna()

    latest_score, latest_reasons = calculate_breakout_score(df)

    st.subheader(f"{selected_ticker} Breakout Dashboard")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Latest Price", f"${df['Close'].iloc[-1]:.2f}")
    col2.metric("Breakout Score", f"{latest_score}/100")
    col3.metric("RSI", f"{df['RSI'].iloc[-1]:.1f}")
    col4.metric("Volume / 20D Avg", f"{df['Volume'].iloc[-1] / df['Volume_MA_20'].iloc[-1]:.2f}x")

    st.write(f"**Signal:** {latest_reasons}")

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price"
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["MA_50"],
        name="50D MA"
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["MA_200"],
        name="200D MA"
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["BB_Upper"],
        name="Bollinger Upper",
        line=dict(width=1)
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["BB_Lower"],
        name="Bollinger Lower",
        line=dict(width=1)
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["Resistance_50d"],
        name="50D Resistance",
        line=dict(dash="dash")
    ))

    fig.update_layout(
        height=650,
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("No valid data found. Try different tickers or a longer period.")
