import yfinance as yf
from rich.console import Console
from rich.table import Table
from rich.live import Live
import time

STOCKS = {
    "ORRF": "Orrstown Financial",
    "COFS": "ChoiceOne Financial",
    "CWBC": "Community West Bancs",
    "AVBH": "Avidbank Holdings",
    "BCAL": "California BanCorp."
}

def format_market_cap(value):
    if not value:
        return "N/A"
    if value >= 1e9:
        return f"${value / 1e9:.2f}B"
    elif value >= 1e6:
        return f"${value / 1e6:.2f}M"
    else:
        return f"${value:,.0f}"

def get_stock_data():
    data = []
    tickers = list(STOCKS.keys())
    # Fetch data in one go for efficiency
    yf_tickers = yf.Tickers(" ".join(tickers))
    
    for ticker in tickers:
        try:
            info = yf_tickers.tickers[ticker].info
            # Handle potential missing keys in info
            price = info.get("regularMarketPrice") or info.get("currentPrice") or 0.0
            change = info.get("regularMarketChangePercent") or 0.0
            market_cap = info.get("marketCap")
            name = STOCKS.get(ticker)
            
            # New metrics
            beta = info.get("beta")
            range_52w = info.get("fiftyTwoWeekRange")
            short_ratio = info.get("shortRatio")
            pb_ratio = info.get("priceToBook")
            div_yield = info.get("dividendYield")

            # Formatting
            fmt_beta = f"{beta:.2f}" if beta is not None else "N/A"
            fmt_range = str(range_52w) if range_52w else "N/A"
            fmt_short = f"{short_ratio:.2f}" if short_ratio is not None else "N/A"
            fmt_pb = f"{pb_ratio:.2f}" if pb_ratio is not None else "N/A"
            fmt_div = f"{div_yield:.2f}%" if div_yield is not None else "N/A"

            data.append({
                "ticker": ticker,
                "name": name,
                "price": f"${price:,.2f}",
                "change": f"{change:+.2f}%",
                "raw_change": change,
                "market_cap": format_market_cap(market_cap),
                "beta": fmt_beta,
                "range_52w": fmt_range,
                "short_ratio": fmt_short,
                "pb_ratio": fmt_pb,
                "div_yield": fmt_div
            })
        except Exception:
            data.append({
                "ticker": ticker,
                "name": STOCKS.get(ticker),
                "price": "N/A",
                "change": "N/A",
                "raw_change": -float("inf"),
                "market_cap": "N/A",
                "beta": "N/A",
                "range_52w": "N/A",
                "short_ratio": "N/A",
                "pb_ratio": "N/A",
                "div_yield": "N/A"
            })
    
    # Sort data by raw_change in descending order (highest positive first)
    data.sort(key=lambda x: x["raw_change"], reverse=True)
    
    return data

def generate_table(data):
    table = Table(title="Stock Tracker (Live Updates - Ctrl+C to Exit)")
    table.add_column("Ticker", style="cyan", no_wrap=True)
    table.add_column("Company Name", style="magenta")
    table.add_column("Price", justify="right", style="green")
    table.add_column("Change", justify="right")
    table.add_column("Market Cap", justify="right", style="blue")
    table.add_column("Beta", justify="right")
    table.add_column("52W Range", justify="right")
    table.add_column("Short Ratio", justify="right")
    table.add_column("P/B", justify="right")
    table.add_column("Div Yield", justify="right", style="green")

    for item in data:
        change_style = "bold green" if "+" in item["change"] else "bold red"
        table.add_row(
            item["ticker"],
            item["name"],
            item["price"],
            item["change"],
            item["market_cap"],
            item["beta"],
            item["range_52w"],
            item["short_ratio"],
            item["pb_ratio"],
            item["div_yield"],
            style=change_style if "%" in item["change"] and item["change"] != "0.00%" else ""
        )
    return table

def main():
    console = Console()
    with Live(generate_table([]), refresh_per_second=1) as live:
        while True:
            try:
                data = get_stock_data()
                live.update(generate_table(data))
                time.sleep(30)  # Refresh every 30 seconds
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[bold red]Error: {e}")
                time.sleep(10)

if __name__ == "__main__":
    main()
