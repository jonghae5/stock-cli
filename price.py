import asyncio
import aiohttp
import logging
import sys
from datetime import datetime
from typing import List, Optional, Dict, Any
from rich.table import Table
from rich.live import Live
from rich.console import Console
from rich import box
from config import (
    DEFAULT_PRICE_SYMBOLS,
    DEFAULT_PRICE_UPDATE_INTERVAL,
    DEFAULT_PRICE_TABLE_TITLE,
    DEFAULT_PRICE_COLUMNS,
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


UPBIT_API_URL: str = "https://api.upbit.com/v1/"


# Upbit API에서 데이터 fetching
async def fetch_ticker(
    session: aiohttp.ClientSession, symbol: str
) -> Optional[Dict[str, Any]]:
    url = f"{UPBIT_API_URL}ticker?markets={symbol}"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data:
                    return data[0]
                else:
                    logger.warning(f"No data returned for symbol: {symbol}")
                    return None
            else:
                logger.error(
                    f"Failed to fetch data for {symbol}. Status Code: {response.status}"
                )
                return None
    except aiohttp.ClientError as e:
        logger.error(f"Client error while fetching data for {symbol}: {e}")
        return None
    except asyncio.TimeoutError:
        logger.error(f"Request timed out for symbol: {symbol}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while fetching data for {symbol}: {e}")
        return None


# 모든 심볼에 대해 데이터 fetching
async def fetch_all_tickers(symbols: List[str]) -> List[Optional[Dict[str, Any]]]:
    timeout = aiohttp.ClientTimeout(total=10)  # 전체 요청 타임아웃 설정
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [fetch_ticker(session, symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results


# 테이블 생성
def create_table(tickers: List[Optional[Dict[str, Any]]]) -> Table:
    table = Table(
        title=f"{DEFAULT_PRICE_TABLE_TITLE} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        box=box.MINIMAL_DOUBLE_HEAD,
        expand=True,
    )

    # 컬럼 추가
    for column in DEFAULT_PRICE_COLUMNS:
        table.add_column(
            column["name"],
            style=column.get("style", "dim"),
            justify=column.get("justify", "left"),
        )

    # 데이터 추가
    for ticker in tickers:
        if ticker:
            symbol: str = ticker.get("market", "N/A")
            trade_price: Any = ticker.get("trade_price", "N/A")
            change_rate: float = (
                ticker.get("signed_change_rate", 0.0) * 100
            )  # 소수점으로 반환됨
            trade_volume: Any = ticker.get("trade_volume", 0)
            high_price: Any = ticker.get("high_price", "N/A")
            low_price: Any = ticker.get("low_price", "N/A")

            # 색상 설정: 변동률에 따라 색상 변경
            change_color = "green dim" if change_rate >= 0 else "red dim"
            change_display = f"[{change_color}]{change_rate:.2f}%[/{change_color}]"

            # 값 포맷팅
            trade_price_str = (
                f"{trade_price:,.0f} KRW"
                if isinstance(trade_price, (int, float))
                else "N/A"
            )
            trade_volume_str = (
                f"{trade_volume:,.2f}"
                if isinstance(trade_volume, (int, float))
                else "N/A"
            )
            high_price_str = (
                f"{high_price:,.0f} KRW"
                if isinstance(high_price, (int, float))
                else "N/A"
            )
            low_price_str = (
                f"{low_price:,.0f} KRW"
                if isinstance(low_price, (int, float))
                else "N/A"
            )

            # 행 추가
            table.add_row(
                symbol,
                trade_price_str,
                change_display,
                trade_volume_str,
                high_price_str,
                low_price_str,
            )
        else:
            # 데이터가 없을 경우
            table.add_row("N/A", "N/A", "N/A", "N/A", "N/A", "N/A")
    return table


# 메인 루프
async def main():
    console = Console()
    with Live(console=console, refresh_per_second=1) as live:
        while True:
            tickers_data = await fetch_all_tickers(DEFAULT_PRICE_SYMBOLS)
            table = create_table(tickers_data)
            live.update(table)
            await asyncio.sleep(DEFAULT_PRICE_UPDATE_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Dashboard terminated by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
