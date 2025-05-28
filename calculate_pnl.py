import pandas as pd

def calculate_pnl(log_file="trades_log.csv"):
    df = pd.read_csv(log_file)

    pnl = 0
    trades = []
    buy_price = None

    for _, row in df.iterrows():
        if row['action'] == 'buy':
            buy_price = row['price']
        elif row['action'] == 'sell' and buy_price is not None:
            sell_price = row['price']
            trade_pnl = sell_price - buy_price
            trades.append(trade_pnl)
            pnl += trade_pnl
            buy_price = None  # Reset for next trade

    print("📊 Trade History:")
    for i, t in enumerate(trades):
        print(f"Trade {i+1}: {'Profit' if t > 0 else 'Loss'} of ${round(t, 2)}")

    print(f"\n💰 Total P&L: ${round(pnl, 2)}")

if __name__ == "__main__":
    calculate_pnl()
