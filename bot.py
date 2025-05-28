from dotenv import load_dotenv
import os
import alpaca_trade_api as tradeapi
import pandas as pd
import ta
from sklearn.ensemble import RandomForestClassifier
import schedule
import time
from datetime import datetime
import csv
import sqlite3
from twilio.rest import Client


# Load S&P 500 symbols from CSV
sp500_df = pd.read_csv("sp500_symbols.csv")
symbols = sp500_df["symbol"].tolist()
symbols = [s for s in symbols if "." not in s and "-" not in s]


# Load environment variables
load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = 'https://paper-api.alpaca.markets'

# Initialize Alpaca API
api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL)

# Initialize SQLite DB
def init_db():
    conn = sqlite3.connect("trades.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            timestamp TEXT,
            symbol TEXT,
            action TEXT,
            price REAL,
            prediction INTEGER,
            qty INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def log_trade_db_simple(symbol, volume, price, timestamp):

    conn = sqlite3.connect("trades.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO trades (symbol, volume, price, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (symbol, volume, price, timestamp))
    conn.commit()
    conn.close()

# Log each trade to SQLite
def log_trade_to_db(symbol, action, price, prediction, qty):
    conn = sqlite3.connect("trades.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO trades (timestamp, symbol, action, price, prediction, qty)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datetime.now(), symbol, action, round(price, 2), prediction, qty))
    conn.commit()
    conn.close()

# CSV Logging (for backup or manual inspection)
def log_trade(symbol, action, price, prediction):
    filename = f"{symbol}_trades_log.csv"
    file_exists = os.path.isfile(filename)

    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["timestamp", "symbol", "action", "price", "prediction"])
        writer.writerow([datetime.now(), symbol, action, round(price, 2), prediction])

# Track trades per symbol per day
def has_reached_trade_limit(symbol, max_trades=3):
    filename = f"{symbol}_trades_log.csv"
    if not os.path.isfile(filename):
        return False

    today = datetime.now().date()
    df = pd.read_csv(filename, parse_dates=["timestamp"])
    df = df[df["timestamp"].dt.date == today]

    return len(df) >= max_trades

# Allocation limit
def calculate_quantity(symbol, max_pct=0.05):
    account = api.get_account()
    buying_power = float(account.buying_power)
    max_allocation = buying_power * max_pct

    last_price = api.get_latest_trade(symbol).price
    qty = int(max_allocation / last_price)
    return max(qty, 1), last_price

# Prevent double-buying
def is_already_in_position(symbol):
    positions = api.list_positions()
    return any(p.symbol == symbol for p in positions)

# SMS Notifications
def send_sms_alert(symbol, action, price):
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_num = os.getenv("TWILIO_PHONE_NUMBER")
    my_num = os.getenv("MY_PHONE_NUMBER")

    client = Client(sid, token)
    body = f"📈 Trade Alert: {action.upper()} {symbol} at ${round(price, 2)}"

    try:
        client.messages.create(
            body=body,
            from_=twilio_num,
            to=my_num
        )
        print(f"📲 SMS sent: {body}")
    except Exception as e:
        print(f"❌ Failed to send SMS: {e}")

# Get recent price data
def get_price_data(symbol="AAPL"):
    bars = api.get_bars(symbol, tradeapi.TimeFrame.Minute, limit=100).df
    return bars


# Run bot
def run_bot(symbol):
    print(f"\n🚀 Running bot for {symbol}...")

    if has_reached_trade_limit(symbol):
        print(f"⛔ Max trades reached for {symbol} today. Skipping.")
        return

    if is_already_in_position(symbol):
        print(f"🔁 Already in a position for {symbol}. Skipping.")
        return

    df = get_price_data(symbol)

    if 'close' not in df.columns or df.empty:
        print(f"⚠️ Skipping {symbol} — no valid price data.")
        return

    df['sma_10'] = ta.trend.sma_indicator(df['close'], window=10)
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['macd'] = ta.trend.MACD(df['close']).macd()
    df.dropna(inplace=True)

    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
    df.dropna(inplace=True)

    features = ['sma_10', 'rsi', 'macd']
    X = df[features]
    y = df['target']

    model = RandomForestClassifier()
    model.fit(X[:-1], y[:-1])

    latest_data = X.iloc[-1].values.reshape(1, -1)
    prediction = model.predict(latest_data)[0]

    qty, last_price = calculate_quantity(symbol)
    action = 'buy' if prediction == 1 else 'sell'

    # Fix SL/TP logic depending on action
    if action == 'buy':
        stop_loss_price = last_price * 0.98
        take_profit_price = last_price * 1.02
    else:  # sell
        stop_loss_price = last_price * 1.02
        take_profit_price = last_price * 0.98

    print(f"📈 BUY signal!" if prediction == 1 else "📉 SELL signal!")
    print(f"📤 Placing {action.upper()} order with SL/TP...")

    try:
        api.submit_order(
            symbol=symbol,
            qty=qty,
            side=action,
            type='market',
            time_in_force='gtc',
            order_class='bracket',
            stop_loss={'stop_price': round(stop_loss_price, 2)},
            take_profit={'limit_price': round(take_profit_price, 2)},
            extended_hours=False
        )

        log_trade(symbol, action, last_price, prediction)
        log_trade_to_db(symbol, action, last_price, prediction, qty)
        send_sms_alert(symbol, action, last_price)

    except Exception as e:
        print(f"❌ Failed to place order: {e}")


for symbol in symbols:
    run_bot(symbol)

    

schedule.every(5).minutes.do(lambda: [run_bot(sym) for sym in symbols])

print("⏳ Bot is now running every 5 minutes... Press Ctrl+C to stop.")


try:
    while True:
        schedule.run_pending()
        time.sleep(1)
except KeyboardInterrupt:
    print("🛑 Bot stopped manually.")




