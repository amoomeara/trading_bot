import pandas as pd
import glob

def analyze_logs():
    csv_files = glob.glob("*_trades_log.csv")
    
    for file in csv_files:
        symbol = file.split("_")[0]
        df = pd.read_csv(file)
        print(f"\n📊 Stats for {symbol}:")

        pnl = 0
        wins = 0
        losses = 0
        trades = []
        buy_price = None

        for _, row in df.iterrows():
            if row['action'] == 'buy':
                buy_price = row['price']
            elif row['action'] == 'sell' and buy_price is not None:
                sell_price = row['price']
                result = sell_price - buy_price
                trades.append(result)
                pnl += result
                if result > 0:
                    wins += 1
                else:
                    losses += 1
                buy_price = None  # reset for next round

        print(f"Total Trades: {len(trades)}")
        print(f"Profitable: {wins} | Unprofitable: {losses}")
        print(f"Win Rate: {round(100 * wins / max(1, (wins + losses)), 2)}%")
        print(f"Net P&L: ${round(pnl, 2)}")

if __name__ == "__main__":
    analyze_logs()
