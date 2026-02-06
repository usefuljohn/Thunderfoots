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

BENCHMARKS = [
    {"ticker": "KRE", "name": "S&P Regional Banking ETF"},
    {"ticker": "VBR", "name": "Vanguard Small-Cap Value ETF"},
    {"ticker": "IJR", "name": "iShares Core S&P Small-Cap ETF"},
    {"ticker": "^BANK", "name": "NASDAQ Bank Index"}
]

def format_market_cap(value):
    if not value:
        return "N/A"
    if value >= 1e9:
        return f"${value / 1e9:.2f}B"
    elif value >= 1e6:
        return f"${value / 1e6:.2f}M"
    else:
        return f"${value:,.0f}"

def get_dashboard_data():
    stock_data = []
    tickers = list(STOCKS.keys())
    benchmark_tickers = [b["ticker"] for b in BENCHMARKS]
    
    # Fetch data for stocks AND indices in one go
    all_tickers = tickers + benchmark_tickers
    yf_tickers = yf.Tickers(" ".join(all_tickers))
    
    # Process Stocks
    valid_changes = []
    
    for ticker in tickers:
        try:
            info = yf_tickers.tickers[ticker].info
            # Handle potential missing keys in info
            price = info.get("regularMarketPrice") or info.get("currentPrice") or 0.0
            change = info.get("regularMarketChangePercent") or 0.0
            market_cap = info.get("marketCap")
            name = STOCKS.get(ticker)
            
            if isinstance(change, (int, float)):
                 valid_changes.append(change)
            
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

            stock_data.append({
                "ticker": ticker,
                "name": name,
                "price": f"${price:,.2f}",
                "change": f"{change:+.2f}%",
                "raw_change": change if isinstance(change, (int, float)) else 0.0,
                "market_cap": format_market_cap(market_cap),
                "beta": fmt_beta,
                "range_52w": fmt_range,
                "short_ratio": fmt_short,
                "pb_ratio": fmt_pb,
                "div_yield": fmt_div
            })
        except Exception:
            stock_data.append({
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
    
    # Sort data by raw_change in descending order
    stock_data.sort(key=lambda x: x["raw_change"], reverse=True)
    
    # Calculate Portfolio Average
    portfolio_avg_change = sum(valid_changes) / len(valid_changes) if valid_changes else 0.0
    
    # Process Benchmarks
    benchmark_data = []
    for b in BENCHMARKS:
        try:
            info = yf_tickers.tickers[b["ticker"]].info
            price = info.get("regularMarketPrice") or info.get("currentPrice") or 0.0
            change = info.get("regularMarketChangePercent") or 0.0
            
            benchmark_data.append({
                "name": b["name"],
                "ticker": b["ticker"],
                "price": price,
                "change": change
            })
        except Exception:
             benchmark_data.append({
                "name": b["name"],
                "ticker": b["ticker"],
                "price": 0.0,
                "change": 0.0
            })

    return {
        "stocks": stock_data,
        "portfolio_avg": portfolio_avg_change,
        "benchmarks": benchmark_data
    }

def generate_dashboard(data_dict):
    # Main Stock Table
    table = Table(title="Thunderfoot Stock Tracker")
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

    for item in data_dict["stocks"]:
        change_style = "bold green" if item["raw_change"] >= 0 else "bold red"
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
            style=change_style if item["change"] != "N/A" else ""
        )
        
    # Summary / Comparison Table
    summary_table = Table(title="Market Comparison (Equal-Weighted)", show_header=True)
    summary_table.add_column("Entity", style="yellow")
    summary_table.add_column("Price", justify="right")
    summary_table.add_column("Daily Change", justify="right")
    
    # Portfolio Row
    port_change_val = data_dict["portfolio_avg"]
    port_color = "bold green" if port_change_val >= 0 else "bold red"
    summary_table.add_row(
        "Thunderfoot Portfolio",
        "-",
        f"[{port_color}]{port_change_val:+.2f}%[/{port_color}]"
    )
    
    # Benchmark Rows
    for b in data_dict["benchmarks"]:
        idx_change_val = b["change"]
        idx_price_val = b["price"]
        idx_color = "bold green" if idx_change_val >= 0 else "bold red"
        summary_table.add_row(
            f"{b['name']} ({b['ticker']})",
            f"${idx_price_val:,.2f}",
            f"[{idx_color}]{idx_change_val:+.2f}%[/{idx_color}]"
        )

    from rich.console import Group
    return Group(table, "\n", summary_table)

def main():
    console = Console()
    with Live(generate_dashboard(get_dashboard_data()), refresh_per_second=1) as live:
        while True:
            try:
                data = get_dashboard_data()
                live.update(generate_dashboard(data))
                time.sleep(30)  # Refresh every 30 seconds
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[bold red]Error: {e}")
                time.sleep(10)

if __name__ == "__main__":
    main()
