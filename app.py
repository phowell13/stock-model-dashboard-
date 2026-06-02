import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Penny Stock Breakout Scanner", layout="wide")

st.title("Penny Stock Breakout Scanner")

watchlists = {
    "Custom": "",
    "UK AIM / Penny Stocks": "PREM.L, HE1.L, BOIL.L, UKOG.L, 88E.L, EUA.L, GGP.L, COPL.L, EEE.L, KOD.L",
    "US Penny / Small Caps": "SOUN, BBAI, KULR, RGTI, IONQ, LUNR, JOBY, ACHR, OPEN, PLUG",
    "Mining / Resources": "PREM.L, HE1.L, GGP.L, KOD.L, EUA.L, 88E.L, EEE.L, SOLG.L, UFO.L, MARU.L",
    "AI / Speculative Tech": "SOUN, BBAI, AI, RGTI, IONQ, KULR, SERV, LUNR, ACHR"
}

selected_watchlist = st.sidebar.selectbox(
    "Choose watchlist",
    list(watchlists.keys())
)

default_tickers = watchlists[selected_watchlist]

tickers_input = st.sidebar.text_area(
    "Enter tickers",
    value=default_tickers if default_tickers else "PREM.L, HE1.L, BOIL.L"
)


period = st.sidebar.selectbox("Period", ["6mo", "1y", "2y", "5y"], index=2)

max_price = st.sidebar.number_input("Max share price", value=5.00)
min_avg_volume = st.sidebar.number_input("Minimum 20D average volume", value=250000)
min_value_traded = st.sidebar.number_input("Minimum daily value traded", value=100000)

min_score = st.sidebar.slider(
    "Minimum breakout score",
    min_value=0,
    max_value=100,
    value=70,
    step=5
)

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

    return data.dropna()


@st.cache_data
def get_company_name(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return info.get("longName", ticker)
    except Exception:
        return ticker


def add_indicators(df):
    df = df.copy()

    df["Return"] = df["Close"].pct_change()

    df["MA_20"] = df["Close"].rolling(20).mean()
    df["MA_50"] = df["Close"].rolling(50).mean()
    df["MA_200"] = df["Close"].rolling(200).mean()

    df["Volume_MA_20"] = df["Volume"].rolling(20).mean()
    df["Volume_Ratio"] = df["Volume"] / df["Volume_MA_20"]

    df["Value_Traded"] = df["Close"] * df["Volume"]
    df["Avg_Value_Traded_20D"] = df["Value_Traded"].rolling(20).mean()

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

    true_range = pd.concat(
        [high_low, high_close, low_close],
        axis=1
    ).max(axis=1)

    df["ATR_14"] = true_range.rolling(14).mean()
    df["ATR_Percent"] = df["ATR_14"] / df["Close"]

    return df


def calculate_penny_breakout_score(df):
    latest = df.iloc[-1]

    score = 0
    reasons = []

    squeeze_threshold = df["BB_Width"].rolling(120).quantile(0.25).iloc[-1]

    if latest["BB_Width"] < squeeze_threshold:
        score += 20
        reasons.append("Volatility squeeze")

    if latest["Close"] > latest["Resistance_50d"]:
        score += 25
        reasons.append("Break above 50D resistance")

    if latest["Volume_Ratio"] >= 2:
        score += 20
        reasons.append("Volume spike above 2x average")

    if latest["Volume_Ratio"] >= 5:
        score += 15
        reasons.append("Major volume spike above 5x average")

    if latest["Close"] > latest["MA_20"] and latest["MA_20"] > latest["MA_50"]:
        score += 10
        reasons.append("Short-term trend turning up")

    if 45 <= latest["RSI"] <= 75:
        score += 10
        reasons.append("RSI in breakout zone")

    if not reasons:
        reasons.append("No major breakout signal yet")

    return min(score, 100), ", ".join(reasons)


def get_signal_grade(score):
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    else:
        return "D"


results = []

for ticker in tickers:
    try:
        df = load_price_data(ticker, period)
        df = add_indicators(df).dropna()

        if len(df) < 120:
            continue

        latest = df.iloc[-1]

        if latest["Close"] > max_price:
            continue

        if latest["Volume_MA_20"] < min_avg_volume:
            continue

        if latest["Avg_Value_Traded_20D"] < min_value_traded:
            continue

        score, reasons = calculate_penny_breakout_score(df)
        company_name = get_company_name(ticker)

        results.append({
            "Ticker": ticker,
            "Company": company_name,
            "Close": round(latest["Close"], 4),
            "Breakout Score": score,
            "Grade": get_signal_grade(score),
            "Volume Ratio": round(latest["Volume_Ratio"], 2),
            "20D Avg Volume": int(latest["Volume_MA_20"]),
            "20D Avg Value Traded": int(latest["Avg_Value_Traded_20D"]),
            "RSI": round(latest["RSI"], 1),
            "Above 50D Resistance": latest["Close"] > latest["Resistance_50d"],
            "Signal": reasons
        })

    except Exception as e:
        st.warning(f"Could not load {ticker}: {e}")


results_df = pd.DataFrame(results)

st.subheader("Penny Stock Breakout Results")

if not results_df.empty:
    results_df = results_df[results_df["Breakout Score"] >= min_score]
    results_df = results_df.sort_values("Breakout Score", ascending=False)

    if results_df.empty:
        st.warning(
            "No shares met your minimum breakout score. "
            "Try lowering the Top Opportunities filter."
        )
        st.stop()

    st.dataframe(results_df, use_container_width=True)

    selected_ticker = st.selectbox(
        "Select ticker to chart",
        results_df["Ticker"].tolist()
    )

    selected_company = results_df.loc[
        results_df["Ticker"] == selected_ticker,
        "Company"
    ].iloc[0]

    df = load_price_data(selected_ticker, period)
    df = add_indicators(df).dropna()

    score, reasons = calculate_penny_breakout_score(df)

    st.subheader(f"{selected_company} ({selected_ticker}) Breakout Dashboard")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Latest Price", f"{df['Close'].iloc[-1]:.4f}")
    col2.metric("Breakout Score", f"{score}/100")
    col3.metric("Grade", get_signal_grade(score))
    col4.metric("Volume Ratio", f"{df['Volume_Ratio'].iloc[-1]:.2f}x")
    col5.metric("RSI", f"{df['RSI'].iloc[-1]:.1f}")

    st.write(f"**Signal:** {reasons}")

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
        y=df["MA_20"],
        name="20D MA"
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["MA_50"],
        name="50D MA"
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["BB_Upper"],
        name="Bollinger Upper"
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["BB_Lower"],
        name="Bollinger Lower"
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
    st.error(
        "No shares passed the penny-stock filters. "
        "Try lowering the volume/value thresholds or adding more tickers."
    )
