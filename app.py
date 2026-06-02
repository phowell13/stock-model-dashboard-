import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Stock Modelling Dashboard", layout="wide")

st.title("Stock Modelling Dashboard")

ticker = st.sidebar.text_input("Ticker", value="CARR").upper()
period = st.sidebar.selectbox("Period", ["1y", "2y", "5y", "10y"], index=2)

@st.cache_data
def load_price_data(ticker, period):
    data = yf.download(
        ticker,
        period=period,
        auto_adjust=True,
        progress=False
    )

    # Flatten MultiIndex columns if yfinance returns them
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.dropna()

    data["Return"] = data["Close"].pct_change()
    data["Volatility_30d"] = data["Return"].rolling(30).std()
    data["MA_50"] = data["Close"].rolling(50).mean()
    data["MA_200"] = data["Close"].rolling(200).mean()

    return data


df = load_price_data(ticker, period)

st.write(df.columns)

st.subheader(f"{ticker} Price Chart")
fig = px.line(df, y=["Close", "MA_50", "MA_200"])
st.plotly_chart(fig, use_container_width=True)

col1, col2, col3 = st.columns(3)

col1.metric("Latest Price", f"${df['Close'].iloc[-1]:.2f}")
col2.metric("30D Volatility", f"{df['Volatility_30d'].iloc[-1] * 100:.2f}%")
col3.metric("1Y Return", f"{((df['Close'].iloc[-1] / df['Close'].iloc[-252]) - 1) * 100:.2f}%")

st.subheader("Raw Data")
st.dataframe(df.tail(20))
