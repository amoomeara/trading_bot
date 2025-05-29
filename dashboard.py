import streamlit as st
import pandas as pd
import sqlite3
import time

# Connect to SQLite database
def load_data():
    conn = sqlite3.connect("trades.db")
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trades (
        timestamp TEXT,
        symbol TEXT,
        action TEXT,
        price REAL,
        prediction INTEGER,
        qty INTEGER
    );
    ''')

    conn.commit()
    df = pd.read_sql_query("SELECT * FROM trades", conn)
    conn.close()
    return df

# Streamlit app
st.set_page_config(page_title="Trading Bot Dashboard", layout="wide")
st.title("📊 Trading Bot Dashboard")

df = load_data()

if df.empty:
    st.warning("No trades logged yet.")
else:
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.sort_values("timestamp", ascending=False, inplace=True)

    # Sidebar filters
    symbols = df["symbol"].unique().tolist()
    selected_symbols = st.sidebar.multiselect("Select Symbols", symbols, default=symbols)

    df_filtered = df[df["symbol"].isin(selected_symbols)]

    # Show metrics
    st.metric("Total Trades", len(df_filtered))
    st.dataframe(df_filtered, use_container_width=True)

    # Plot price chart if price column exists
    if "price" in df_filtered.columns and not df_filtered["price"].isnull().all():
        st.line_chart(df_filtered.set_index("timestamp")["price"])
    else:
        st.info("No price data available to plot.")

    # Show P&L summary per symbol
    pnl_data = []
    for symbol in selected_symbols:
        df_symbol = df_filtered[df_filtered["symbol"] == symbol]
        if not df_symbol.empty:
            avg_price = df_symbol["price"].mean()
            latest_price = df_symbol["price"].iloc[-1]
            total_volume = df_symbol["qty"].sum()
            pnl = (latest_price - avg_price) * total_volume
            pnl_data.append((symbol, round(pnl, 2)))

    pnl_data.sort(key=lambda x: x[1], reverse=True)

    if pnl_data:
        st.subheader("📈 Profit/Loss by Symbol")
        for symbol, pnl in pnl_data:
            pnl_color = "🟢" if pnl >= 0 else "🔴"
            st.write(f"{pnl_color} {symbol}: ${pnl:.2f}")

# Auto-refresh every 30 seconds
st.caption("⏳ Auto-refreshing every 30 seconds...")
time.sleep(30)
st.rerun()




