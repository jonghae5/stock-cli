import asyncio
import logging
import sys
from datetime import datetime
from typing import List, Optional, Dict, Any

import yfinance as yf
from rich.table import Table
from rich.live import Live
from rich.console import Console
from rich import box
from config import (
    DEFAULT_STOCK_PRICE_SYMBOLS,
    DEFAULT_STOCK_PRICE_UPDATE_INTERVAL,
    DEFAULT_STOCK_PRICE_TABLE_TITLE,
    DEFAULT_STOCK_PRICE_COLUMNS
)

from dotenv import load_dotenv
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("dashboard.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def fetch_ticker(symbol: str) -> Optional[Dict[str, Any]]:
    """yfinance를 통해 심볼의 최근 일자 주가를 가져온다."""
    try:
        # yfinance는 동기적이므로 to_thread로 비동기 래핑 
        # ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y'
        data = await asyncio.to_thread(yf.Ticker(symbol).history, period="5d", interval="1d")
        if data.empty:
            logger.warning(f"No data returned for symbol: {symbol}")
            return None
        
        # 최근 행(마지막 분봉 또는 종가)에서 종가, 고가, 저가, 거래량
        last_row = data.iloc[-1]        
        yesterday_price = last_row["Open"]
        today_price = last_row["Close"]
        high_price = last_row["High"]
        low_price = last_row["Low"]
        volume = last_row["Volume"]
        
        # 변동률 계산: (금일종가 - 금일시가) / 금일시가 * 100
        change_rate = ((today_price - yesterday_price) / yesterday_price) * 100
        

        return {
            "symbol": symbol,
            "yesterday": yesterday_price,
            "today": today_price,
            "change_rate": change_rate,
            "volume": volume,
            "high": high_price,
            "low": low_price,
        }
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None


async def fetch_all_tickers(symbols: List[str]) -> List[Optional[Dict[str, Any]]]:
    tasks = [fetch_ticker(symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return results


def create_table(tickers: List[Optional[Dict[str, Any]]]) -> Table:
    table = Table(
        title=f"{DEFAULT_STOCK_PRICE_TABLE_TITLE} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        box=box.MINIMAL_DOUBLE_HEAD,
        expand=True,
    )

    # 컬럼 추가
    for column in DEFAULT_STOCK_PRICE_COLUMNS:
        table.add_column(
            column["name"],
            style=column.get("style", "dim"),
            justify=column.get("justify", "left"),
        )

    for ticker in tickers:
        if ticker:
            symbol = ticker.get("symbol", "N/A")
            yesterday_price = ticker.get("yesterday", "N/A")
            today_price = ticker.get("today", "N/A")
            change_rate = ticker.get("change_rate", 0.0)
            volume = ticker.get("volume", 0)
            high_price = ticker.get("high", "N/A")
            low_price = ticker.get("low", "N/A")

            change_color = "green dim" if change_rate >= 0 else "red dim"
            change_display = f"[{change_color}]{change_rate:.2f}%[/{change_color}]"

            yesterday_price_str = (
                f"{yesterday_price:,.2f}" if isinstance(yesterday_price, (int, float)) else "N/A"
            )
            today_price_str = (
                f"{today_price:,.2f}" if isinstance(today_price, (int, float)) else "N/A"
            )
            volume_str = (
                f"{volume:,.0f}"
                if isinstance(volume, (int, float))
                else "N/A"
            )
            high_price_str = (
                f"{high_price:,.2f}"
                if isinstance(high_price, (int, float))
                else "N/A"
            )
            low_price_str = (
                f"{low_price:,.2f}"
                if isinstance(low_price, (int, float))
                else "N/A"
            )

            table.add_row(
                symbol,
                yesterday_price_str,
                today_price_str,
                change_display,
                volume_str,
                high_price_str,
                low_price_str,
            )
        else:
            # 데이터가 없을 경우
            table.add_row("N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A")
    return table


async def main():
    console = Console()
    with Live(console=console, refresh_per_second=1) as live:
        while True:
            tickers_data = await fetch_all_tickers(DEFAULT_STOCK_PRICE_SYMBOLS)
            table = create_table(tickers_data)
            live.update(table)
            await asyncio.sleep(DEFAULT_STOCK_PRICE_UPDATE_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Dashboard terminated by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")