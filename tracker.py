import json
import time
import argparse
import sys
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

import yfinance as yf
from rich.console import Console, Group
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

# --- Configuration & Constants ---
DEFAULT_CONFIG = "portfolio.json"
DEFAULT_REFRESH = 30

@dataclass
class StockData:
    ticker: str
    name: str
    price: float
    change_pct: float
    market_cap: Optional[float]
    beta: Optional[float]
    range_52w_low: Optional[float]
    range_52w_high: Optional[float]
    short_ratio: Optional[float]
    pb_ratio: Optional[float]
    div_yield: Optional[float]
    roa: Optional[float]

    @property
    def formatted_price(self) -> str:
        return f"${self.price:,.2f}"

    @property
    def formatted_change(self) -> str:
        return f"{self.change_pct:+.2f}%"

    @property
    def formatted_market_cap(self) -> str:
        if not self.market_cap:
            return "N/A"
        if self.market_cap >= 1e9:
            return f"${self.market_cap / 1e9:.2f}B"
        elif self.market_cap >= 1e6:
            return f"${self.market_cap / 1e6:.2f}M"
        return f"${self.market_cap:,.0f}"

    @property
    def formatted_beta(self) -> str:
        return f"{self.beta:.2f}" if self.beta is not None else "N/A"

    @property
    def formatted_range_52w(self) -> str:
        if self.range_52w_low and self.range_52w_high:
            return f"{self.range_52w_low:,.2f} - {self.range_52w_high:,.2f}"
        return "N/A"

    @property
    def formatted_short_ratio(self) -> str:
        return f"{self.short_ratio:.2f}" if self.short_ratio is not None else "N/A"

    @property
    def formatted_pb_ratio(self) -> str:
        return f"{self.pb_ratio:.2f}" if self.pb_ratio is not None else "N/A"

    @property
    def formatted_div_yield(self) -> str:
        return f"{self.div_yield:.2f}%" if self.div_yield is not None else "N/A"

    @property
    def formatted_roa(self) -> str:
        return f"{self.roa * 100:.2f}%" if self.roa is not None else "N/A"

class PortfolioTracker:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.stocks = self.config.get("stocks", {})
        # Check for indices_etfs first, then fall back to benchmarks
        self.benchmarks = self.config.get("indices_etfs") or self.config.get("benchmarks") or []

    def _load_config(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Config file '{path}' not found.")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Config file '{path}' is not valid JSON.")
            sys.exit(1)

    def fetch_data(self) -> Dict[str, Any]:
        stock_tickers = list(self.stocks.keys())
        benchmark_tickers = [b["ticker"] for b in self.benchmarks]
        all_tickers = stock_tickers + benchmark_tickers
        
        # Batch fetch
        try:
            tickers_data = yf.Tickers(" ".join(all_tickers))
        except Exception as e:
            # Fallback or error logging
            return {"stocks": [], "portfolio_avg": 0.0, "benchmarks": [], "error": str(e)}

        processed_stocks: List[StockData] = []
        valid_changes: List[float] = []

        # Process Stocks
        for ticker in stock_tickers:
            try:
                info = tickers_data.tickers[ticker].info
                
                # Extract Data safely
                price = info.get("regularMarketPrice") or info.get("currentPrice") or 0.0
                change = info.get("regularMarketChangePercent") or 0.0
                
                if isinstance(change, (int, float)):
                    valid_changes.append(change)

                processed_stocks.append(StockData(
                    ticker=ticker,
                    name=self.stocks.get(ticker, ticker),
                    price=price,
                    change_pct=change,
                    market_cap=info.get("marketCap"),
                    beta=info.get("beta"),
                    range_52w_low=info.get("fiftyTwoWeekLow"),
                    range_52w_high=info.get("fiftyTwoWeekHigh"),
                    short_ratio=info.get("shortRatio"),
                    pb_ratio=info.get("priceToBook"),
                    div_yield=info.get("dividendYield"),
                    roa=info.get("returnOnAssets")
                ))

            except Exception:
                # Add a dummy empty record on failure to keep the list consistent or just skip
                processed_stocks.append(StockData(
                    ticker=ticker,
                    name=self.stocks.get(ticker, ticker),
                    price=0.0,
                    change_pct=0.0,
                    market_cap=None,
                    beta=None,
                    range_52w_low=None,
                    range_52w_high=None,
                    short_ratio=None,
                    pb_ratio=None,
                    div_yield=None,
                    roa=None
                ))

        # Sort by change descending
        processed_stocks.sort(key=lambda x: x.change_pct, reverse=True)

        # Portfolio Avg
        portfolio_avg = sum(valid_changes) / len(valid_changes) if valid_changes else 0.0

        # Process Benchmarks
        processed_benchmarks = []
        for b in self.benchmarks:
            try:
                info = tickers_data.tickers[b["ticker"]].info
                price = info.get("regularMarketPrice") or info.get("currentPrice") or 0.0
                change = info.get("regularMarketChangePercent") or 0.0
                processed_benchmarks.append({
                    "name": b["name"],
                    "ticker": b["ticker"],
                    "price": price,
                    "change": change
                })
            except Exception:
                processed_benchmarks.append({
                    "name": b["name"],
                    "ticker": b["ticker"],
                    "price": 0.0,
                    "change": 0.0
                })

        # Sort benchmarks by change descending
        processed_benchmarks.sort(key=lambda x: x["change"], reverse=True)

        return {
            "stocks": processed_stocks,
            "portfolio_avg": portfolio_avg,
            "benchmarks": processed_benchmarks,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

def generate_dashboard(data: Dict[str, Any]) -> Group:
    if "error" in data:
        return Group(Panel(f"[bold red]Error fetching data:[/bold red] {data['error']}"))

    # Header with timestamp
    timestamp_text = Text(f"Last Updated: {data.get('timestamp', 'N/A')}", style="dim italic", justify="right")

    # Main Stock Table
    table = Table(title="Thunderfoot Stock Tracker", expand=True)
    table.add_column("Ticker", style="cyan", no_wrap=True)
    table.add_column("Company Name", style="magenta")
    table.add_column("Price", justify="right", style="green")
    table.add_column("Change", justify="right")
    table.add_column("Market Cap", justify="right", style="blue")
    table.add_column("Beta", justify="right")
    table.add_column("52W Range", justify="right")
    table.add_column("Short Ratio", justify="right")
    table.add_column("P/B", justify="right")
    table.add_column("ROA", justify="right", style="cyan")
    table.add_column("Div Yield", justify="right", style="green")

    for stock in data["stocks"]:
        change_style = "bold green" if stock.change_pct >= 0 else "bold red"
        table.add_row(
            stock.ticker,
            stock.name,
            stock.formatted_price,
            f"[{change_style}]{stock.formatted_change}[/{change_style}]",
            stock.formatted_market_cap,
            stock.formatted_beta,
            stock.formatted_range_52w,
            stock.formatted_short_ratio,
            stock.formatted_pb_ratio,
            stock.formatted_roa,
            stock.formatted_div_yield
        )
        
    # Summary Table
    summary_table = Table(title="Market Comparison", show_header=True, expand=True)
    summary_table.add_column("Entity", style="yellow")
    summary_table.add_column("Price", justify="right")
    summary_table.add_column("Daily Change", justify="right")
    
    # Portfolio Row
    port_val = data["portfolio_avg"]
    port_color = "bold green" if port_val >= 0 else "bold red"
    summary_table.add_row(
        "Thunderfoot Portfolio (Avg)",
        "-",
        f"[{port_color}]{port_val:+.2f}%[/{port_color}]"
    )
    
    # Benchmark Rows
    for b in data["benchmarks"]:
        color = "bold green" if b["change"] >= 0 else "bold red"
        summary_table.add_row(
            f"{b['name']} ({b['ticker']})",
            f"${b['price']:,.2f}",
            f"[{color}]{b['change']:+.2f}%[/{color}]"
        )

    return Group(timestamp_text, table, "\n", summary_table)

def main():
    parser = argparse.ArgumentParser(description="Thunderfoot Stock Tracker")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG, help="Path to config JSON file")
    parser.add_argument("--interval", type=int, default=DEFAULT_REFRESH, help="Refresh interval in seconds")
    args = parser.parse_args()

    console = Console()
    tracker = PortfolioTracker(args.config)

    console.print("[bold green]Starting Thunderfoot Tracker...[/bold green]")
    
    # Initial Fetch to show immediate data
    try:
        data = tracker.fetch_data()
    except KeyboardInterrupt:
        return

    with Live(generate_dashboard(data), refresh_per_second=1, screen=True) as live:
        while True:
            try:
                time.sleep(args.interval)
                data = tracker.fetch_data()
                live.update(generate_dashboard(data))
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[bold red]Unexpected Error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    main()