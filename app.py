import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime


st.set_page_config(page_title="Penny Stock Breakout Scanner", layout="wide")

st.title("Penny Stock Breakout Scanner")

watchlists = {
    "Custom": "",

    "UK AIM / Penny Stocks": """
PREM.L,HE1.L,BOIL.L,88E.L,EUA.L,GGP.L,COPL.L,
EEE.L,KOD.L,SOLG.L,UFO.L,MARU.L,PHE.L,
PANR.L,POW.L,CORA.L,PXC.L,GCM.L,
BMN.L,ARB.L,SRES.L,ORR.L,KEFI.L,
JLP.L,WRES.L,VAST.L,GST.L,
KAV.L,RRR.L,MKA.L,AFN.L,TYM.L,
XTR.L,HZM.L,ECR.L,AAZ.L,
CTL.L,EMH.L,RBD.L
""",

    "Mining / Resources": """
PREM.L,HE1.L,GGP.L,KOD.L,EUA.L,
88E.L,SOLG.L,UFO.L,MARU.L,
BMN.L,CORA.L,PXC.L,GCM.L,
PANR.L,HZM.L,POW.L,KEFI.L,
JLP.L,VAST.L,ECR.L,XTR.L,
MKA.L,RRR.L,KAV.L,SRES.L,
AAZ.L,EMH.L
""",

    "AI / Speculative Tech": """
SOUN,BBAI,AI,RGTI,IONQ,KULR,SERV,LUNR,ACHR,
PLTR,REKR,AISP,PRST,CXAI,GFAI,VERI,
LAES,INOD,DATS,MARK,WIMI,DUOT,
CISO,RDZN,BTBT,MLGO,PBTS,
AMST,VRAR,ALAR,BKSY
""",

    "US Penny / Small Caps": """
SOUN,BBAI,KULR,RGTI,IONQ,LUNR,
JOBY,ACHR,OPEN,PLUG,RDZN,CISO,
BTBT,WIMI,MARK,PRST,CXAI,GFAI,
AISP,REKR,VERI,INOD,LAES,
DATS,DUOT,PBTS,MLGO,
VRAR,BKSY,SATL,ASTS,RANI,
SABS,OCGN,TTOO,GSAT
"""
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

if selected_watchlist == "UK AIM / Penny Stocks":
    max_price = 5

elif selected_watchlist == "Mining / Resources":
    max_price = 10

elif selected_watchlist == "AI / Speculative Tech":
    max_price = 25

elif selected_watchlist == "US Penny / Small Caps":
    max_price = 15

else:
    max_price = st.sidebar.number_input(
        "Max share price",
        value=10.0
    )

st.sidebar.write(f"Max Price Filter: {max_price}")
auto_price_filter = st.sidebar.checkbox(
    "Auto price filter",
    value=True
)
if auto_price_filter:

    if selected_watchlist == "UK AIM / Penny Stocks":
        max_price = 5

    elif selected_watchlist == "Mining / Resources":
        max_price = 10

    elif selected_watchlist == "AI / Speculative Tech":
        max_price = 25

    elif selected_watchlist == "US Penny / Small Caps":
        max_price = 15

    else:
        max_price = 10

    st.sidebar.write(f"Auto Max Price: {max_price}")

else:
    max_price = st.sidebar.number_input(
        "Max share price",
        value=10.0
    )



auto_volume_filter = st.sidebar.checkbox(
    "Auto volume filters",
    value=True
)

if auto_volume_filter:

    if selected_watchlist == "UK AIM / Penny Stocks":
        min_avg_volume = 50000
        min_value_traded = 10000

    elif selected_watchlist == "Mining / Resources":
        min_avg_volume = 100000
        min_value_traded = 25000

    elif selected_watchlist == "AI / Speculative Tech":
        min_avg_volume = 500000
        min_value_traded = 250000

    elif selected_watchlist == "US Penny / Small Caps":
        min_avg_volume = 250000
        min_value_traded = 100000

    else:
        min_avg_volume = 0
        min_value_traded = 0

    st.sidebar.write(f"Min Avg Volume: {min_avg_volume:,}")
    st.sidebar.write(f"Min Value Traded: {min_value_traded:,}")

else:
    min_avg_volume = st.sidebar.number_input(
        "Minimum 20D average volume",
        value=250000
    )

    min_value_traded = st.sidebar.number_input(
        "Minimum daily value traded",
        value=100000
    )

min_score = st.sidebar.slider(
    "Minimum breakout score",
    min_value=0,
    max_value=100,
    value=0,
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
SCAN_FILE = Path("scan_history.csv")

def save_scan_results(results_df):
    if results_df.empty:
        return

    today = datetime.now().strftime("%Y-%m-%d")

    df_to_save = results_df.copy()
    df_to_save["Scan Date"] = today
    df_to_save["Scan Time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if SCAN_FILE.exists():
        old_df = pd.read_csv(SCAN_FILE)

        # Remove today's previous scan so we only keep one scan per day
        if "Scan Date" in old_df.columns:
            old_df = old_df[old_df["Scan Date"] != today]
        elif "Scan Time" in old_df.columns:
            old_df["Scan Date"] = pd.to_datetime(old_df["Scan Time"]).dt.strftime("%Y-%m-%d")
            old_df = old_df[old_df["Scan Date"] != today]

        combined = pd.concat([old_df, df_to_save], ignore_index=True)

    else:
        combined = df_to_save

    combined.to_csv(SCAN_FILE, index=False)



def load_previous_scan():
    if not SCAN_FILE.exists():
        return pd.DataFrame()

    history = pd.read_csv(SCAN_FILE)

    if history.empty or "Scan Time" not in history.columns:
        return pd.DataFrame()

    latest_time = history["Scan Time"].max()
    previous_scans = history[history["Scan Time"] < latest_time]

    if previous_scans.empty:
        return pd.DataFrame()

    previous_time = previous_scans["Scan Time"].max()

    return previous_scans[previous_scans["Scan Time"] == previous_time]

results = []

def get_status(score):
    if score >= 90:
        return "🔥 Action Zone"
    elif score >= 80:
        return "✅ Candidate"
    elif score >= 70:
        return "👀 Watch"
    else:
        return "❌ Ignore"

with st.spinner("Scanning stocks..."):

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
            "Status": get_status(score),
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

save_scan_results(results_df)
previous_df = load_previous_scan()

if SCAN_FILE.exists():
    history = pd.read_csv(SCAN_FILE)

    st.write(
        history.groupby("Scan Date")
        .size()
        .reset_index(name="Stocks Scanned")
    )


st.subheader("Penny Stock Breakout Results")
if not results_df.empty:

    if not previous_df.empty:
        comparison = results_df.merge(
            previous_df[["Ticker", "Breakout Score"]],
            on="Ticker",
            how="left",
            suffixes=("", " Previous")
        )

        comparison["Score Change"] = (
            comparison["Breakout Score"] -
            comparison["Breakout Score Previous"]
        )

        new_breakouts = comparison[
            (comparison["Breakout Score"] >= 80) &
            (
                comparison["Breakout Score Previous"].isna()
                |
                (comparison["Breakout Score Previous"] < 70)
            )
        ]

        st.subheader("🚀 New Breakouts")

        if not new_breakouts.empty:
            st.dataframe(
                new_breakouts.sort_values("Score Change", ascending=False),
                use_container_width=True
            )
        else:
            st.info("No new breakouts detected.")

        risers = comparison.dropna(subset=["Score Change"])
        risers = risers[risers["Score Change"] > 0]
        risers = risers.sort_values("Score Change", ascending=False)

        st.subheader("🔥 Biggest Score Increases")

        if not risers.empty:
            st.dataframe(
                risers[
                    [
                        "Ticker",
                        "Company",
                        "Breakout Score Previous",
                        "Breakout Score",
                        "Score Change",
                        "Grade",
                        "Status",
                        "Volume Ratio",
                        "RSI"
                    ]
                ].head(10),
                use_container_width=True
            )
        else:
            st.info("No score increases detected this scan.")

        hidden_gems = comparison.dropna(subset=["Score Change"])

        hidden_gems = hidden_gems[
            (hidden_gems["Score Change"] >= 15) &
            (hidden_gems["Breakout Score"] >= 60) &
            (hidden_gems["Breakout Score"] < 80)
        ]

        hidden_gems = hidden_gems.sort_values("Score Change", ascending=False)

        st.subheader("💎 Hidden Gems")

        if not hidden_gems.empty:
            st.dataframe(
                hidden_gems[
                    [
                        "Ticker",
                        "Company",
                        "Breakout Score Previous",
                        "Breakout Score",
                        "Score Change",
                        "Grade",
                        "Status",
                        "Volume Ratio",
                        "RSI"
                    ]
                ].head(10),
                use_container_width=True
            )
        else:
            st.info("No hidden gems detected this scan.")

    else:
        st.info("No previous scan yet. Refresh later to detect new breakouts.")

    st.subheader("📊 Scanner Summary")


    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Stocks", len(results_df))
    col2.metric("New Breakouts", len(new_breakouts) if "new_breakouts" in locals() else 0)
    col3.metric("Biggest Risers", len(risers) if "risers" in locals() else 0)
    col4.metric("Hidden Gems", len(hidden_gems) if "hidden_gems" in locals() else 0)
    results_df = results_df[results_df["Breakout Score"] >= min_score]
    results_df = results_df.sort_values("Breakout Score", ascending=False)
    if results_df.empty:
            st.warning(
                "No shares met your minimum breakout score. "
                "Try lowering the Top Opportunities filter."
            )
            st.stop()


    
    results_df["Rank"] = range(1, len(results_df) + 1)


    action_zone = results_df[
    results_df["Breakout Score"] >= 90
    ]

    st.subheader("🔥 Action Zone")

    if not action_zone.empty:
        st.dataframe(
            action_zone[
                [
                    "Rank",
                    "Ticker",
                    "Company",
                    "Breakout Score",
                    "Grade",
                    "Status",
                    "Volume Ratio",
                    "RSI"
                ]
            ],
            use_container_width=True
        )
    else:
        st.info("No Action Zone candidates today.")

    


    st.subheader("🏆 Top Opportunities")

    top_opportunities = results_df.head(10)

    st.dataframe(
        top_opportunities[
            [
                "Rank",
                "Ticker",
                "Company",
                "Breakout Score",
                "Grade",
                "Status",
                "Volume Ratio",
                "RSI"
            ]
        ],
        use_container_width=True
    )

    st.subheader("Full Scanner Results")
    st.dataframe(results_df, use_container_width=True)

    export_df = results_df.copy()
    export_df["Scan Date"] = datetime.now().strftime("%Y-%m-%d")

    csv = export_df.to_csv(index=False)

    st.download_button(
    label="📥 Download Results CSV",
    data=csv,
    file_name="scanner_results.csv",
    mime="text/csv"
    )

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

    fig.add_trace(go.Scatter(x=df.index, y=df["MA_20"], name="20D MA"))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA_50"], name="50D MA"))
    fig.add_trace(go.Scatter(x=df.index, y=df["BB_Upper"], name="Bollinger Upper"))
    fig.add_trace(go.Scatter(x=df.index, y=df["BB_Lower"], name="Bollinger Lower"))

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
