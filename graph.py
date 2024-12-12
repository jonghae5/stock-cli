import asyncio
import aiohttp
import yaml
import logging
import sys
from datetime import datetime
from typing import List, Optional, Dict, Any
from rich.table import Table
from rich.live import Live
from rich.console import Console
from rich import box
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.align import Align
import click
import plotille
from config import load_config

from config import (
    DEFAULT_GRAPH_SYMBOLS,
    DEFAULT_GRAPH_UPDATE_INTERVAL,
    DEFAULT_GRAPH_TABLE_TITLE,
    DEFAULT_GRAPH_COLUMNS,
    DEFAULT_GRAPH_TIMEFRAMES,
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
                    logger.warning(f"{symbol}에 대한 데이터가 반환되지 않았습니다.")
                    return None
            else:
                logger.error(
                    f"{symbol}의 데이터를 가져오지 못했습니다. 상태 코드: {response.status}"
                )
                return None
    except aiohttp.ClientError as e:
        logger.error(f"{symbol} 데이터를 가져오는 중 클라이언트 오류 발생: {e}")
        return None
    except asyncio.TimeoutError:
        logger.error(f"{symbol}의 요청이 시간 초과되었습니다.")
        return None
    except Exception as e:
        logger.error(f"{symbol} 데이터를 가져오는 중 예상치 못한 오류 발생: {e}")
        return None


# Upbit API에서 캔들 데이터 fetching
async def fetch_candles(
    session: aiohttp.ClientSession, symbol: str, unit: int, count: int
) -> Optional[List[Dict[str, Any]]]:
    url = f"{UPBIT_API_URL}candles/minutes/{unit}?market={symbol}&count={count}"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data:
                    return data
                else:
                    logger.warning(
                        f"{symbol}, 단위: {unit}에 대한 캔들 데이터가 반환되지 않았습니다."
                    )
                    return None
            else:
                logger.error(
                    f"{symbol}, 단위: {unit}의 캔들 데이터를 가져오지 못했습니다. 상태 코드: {response.status}"
                )
                return None
    except aiohttp.ClientError as e:
        logger.error(
            f"{symbol}, 단위: {unit}의 캔들 데이터를 가져오는 중 클라이언트 오류 발생: {e}"
        )
        return None
    except asyncio.TimeoutError:
        logger.error(
            f"{symbol}, 단위: {unit}의 캔들 데이터 요청이 시간 초과되었습니다."
        )
        return None
    except Exception as e:
        logger.error(
            f"{symbol}, 단위: {unit}의 캔들 데이터를 가져오는 중 예상치 못한 오류 발생: {e}"
        )
        return None


# 모든 심볼에 대해 티커 데이터 fetching
async def fetch_all_tickers(
    session: aiohttp.ClientSession, symbols: List[str]
) -> List[Optional[Dict[str, Any]]]:
    tasks = [fetch_ticker(session, symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return results


# 모든 심볼과 시간프레임에 대한 캔들 데이터 fetching
async def fetch_all_candles(
    session: aiohttp.ClientSession, symbols: List[str], timeframes: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Optional[List[Dict[str, Any]]]]]:
    candle_data = {}
    tasks = []
    for symbol in symbols:
        candle_data[symbol] = {}
        for timeframe in timeframes:
            tasks.append(
                (
                    symbol,
                    timeframe,
                    fetch_candles(
                        session, symbol, timeframe["unit"], timeframe["count"]
                    ),
                )
            )
    # 모든 fetch_candles 작업 실행
    results = await asyncio.gather(
        *(task[2] for task in tasks), return_exceptions=False
    )
    # 결과를 candle_data에 할당
    for i, (symbol, timeframe, _) in enumerate(tasks):
        candle_data[symbol][timeframe["name"]] = results[i]
    return candle_data


# 테이블 생성
def create_table(tickers: List[Optional[Dict[str, Any]]], table_title: str) -> Table:
    table = Table(
        title=f"{table_title} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        box=box.MINIMAL_DOUBLE_HEAD,
        expand=True,
    )

    # 컬럼 추가
    for column in DEFAULT_GRAPH_COLUMNS:
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


# plotille을 사용하여 그래프를 문자열로 캡처하는 함수
def create_plotille_line_chart(
    prices: List[float], width: int = 60, height: int = 20
) -> str:
    if not prices:
        return "데이터 없음"

    fig = plotille.Figure()
    fig.width = width
    fig.height = height
    fig.x_label = "Time"
    fig.y_label = "Price"
    fig.title = "Price Chart"
    fig.color_mode = "byte"
    fig.grid = True
    fig.plot(list(range(len(prices))), prices, label="Price", lc=1)
    fig.legend = True

    # 그래프를 문자열로 변환
    plot_output = fig.show(legend=True)
    return plot_output


# 그래프 패널 생성
def create_plot_graph_panel(
    symbol: str,
    timeframe: str,
    candles: Optional[List[Dict[str, Any]]],
    width: int = 60,
    height: int = 20,
) -> Panel:
    if candles is None:
        content = "데이터 없음"
    else:
        # 종가 추출
        closing_prices = [candle["trade_price"] for candle in reversed(candles)]
        content = create_plotille_line_chart(closing_prices, width=width, height=height)
    title = f"{symbol} - {timeframe}"
    return Panel(Align.left(content), title=title, border_style="blue")


# 그래프들 생성
def create_graphs(
    candle_data: Dict[str, Dict[str, Optional[List[Dict[str, Any]]]]]
) -> List[Panel]:
    panels = []
    for symbol, timeframes in candle_data.items():
        for timeframe, candles in timeframes.items():
            panel = create_plot_graph_panel(symbol, timeframe, candles)
            panels.append(panel)
    return panels


# 메인 루프
async def run_dashboard(
    symbols: List[str],
    timeframes: List[Dict[str, Any]],
    update_interval: int,
    table_title: str,
):
    console = Console()
    layout = Layout()

    layout.split(
        Layout(name="upper"), Layout(name="lower", size=5)  # 하단 레이아웃 활성화
    )

    layout["upper"].split_row(
        Layout(name="table", ratio=2), Layout(name="graphs", ratio=3)
    )

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=10)
    ) as session:
        with Live(layout, console=console, refresh_per_second=1):
            while True:
                # 티커 데이터 가져오기
                tickers_data = await fetch_all_tickers(session, symbols)
                table = create_table(tickers_data, table_title)

                # 캔들 데이터 가져오기
                candle_data = await fetch_all_candles(session, symbols, timeframes)
                graphs = create_graphs(candle_data)

                # 레이아웃 업데이트
                layout["upper"]["table"].update(table)

                # 그래프를 열로 배열
                graph_columns = []
                columns_per_row = 1  # 한 행에 몇 개의 그래프를 배치할지 조정 (터미널 너비에 따라 조정)

                for i in range(0, len(graphs), columns_per_row):
                    graph_slice = graphs[i : i + columns_per_row]
                    graph_columns.append(graph_slice)

                graph_layout = Layout()
                for graph_row in graph_columns:
                    graph_layout_split = Layout()
                    for panel in graph_row:
                        graph_layout_split.split_column(Layout(panel))
                    graph_layout.split_row(*graph_layout_split.children)

                layout["upper"]["graphs"].update(graph_layout)

                # 하단 레이아웃 업데이트 (예: 마지막 업데이트 시간)
                last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                footer_text = Text(
                    f"Last Update: {last_update} | Press Ctrl+C to exit.", style="dim"
                )
                layout["lower"].update(Align.center(footer_text))

                await asyncio.sleep(update_interval)


# CLI 정의
@click.command()
@click.option(
    "--symbols",
    "-s",
    multiple=True,
    help="추가할 심볼을 지정합니다. 예: KRW-BTC KRW-ETH",
)
@click.option(
    "--timeframe",
    "-t",
    multiple=True,
    help="추가할 시간 프레임을 지정합니다. 형식: 이름:단위:개수 (예: 1H:60:60)",
)
@click.option(
    "--update-interval",
    "-u",
    default=None,
    type=int,
    help="업데이트 간격을 초 단위로 설정합니다.",
)
@click.option(
    "--config",
    "-c",
    default="config.yaml",
    type=click.Path(exists=True),
    help="사용할 구성 파일을 지정합니다.",
)
def cli(symbols, timeframe, update_interval, config):
    """
    업비트 암호화폐 대시보드 CLI
    """
    # 구성 파일 로드
    config_data = load_config(config)

    # 심볼 설정: CLI에서 제공된 심볼을 우선 사용, 없으면 구성 파일 또는 기본값 사용
    if symbols:
        selected_symbols = list(symbols)
    else:
        selected_symbols = config_data.get("symbols", DEFAULT_GRAPH_SYMBOLS)

    # 타임프레임 설정: CLI에서 제공된 타임프레임을 우선 사용, 없으면 구성 파일 또는 기본값 사용
    if timeframe:
        selected_timeframes = []
        for tf in timeframe:
            try:
                name, unit, count = tf.split(":")
                selected_timeframes.append(
                    {"name": name, "unit": int(unit), "count": int(count)}
                )
            except ValueError:
                logger.error(
                    f"타임프레임 형식이 잘못되었습니다: '{tf}'. 형식은 이름:단위:개수 여야 합니다."
                )
                sys.exit(1)
    else:
        selected_timeframes = config_data.get("timeframes", DEFAULT_GRAPH_TIMEFRAMES)

    # 업데이트 간격 설정: CLI에서 제공된 값을 우선 사용, 없으면 구성 파일 또는 기본값 사용
    if update_interval is not None:
        selected_update_interval = update_interval
    else:
        selected_update_interval = config_data.get(
            "update_interval", DEFAULT_GRAPH_UPDATE_INTERVAL
        )

    # 테이블 제목 설정
    selected_table_title = config_data.get("table_title", DEFAULT_GRAPH_TABLE_TITLE)

    # 비동기 루프 실행
    try:
        asyncio.run(
            run_dashboard(
                selected_symbols,
                selected_timeframes,
                selected_update_interval,
                selected_table_title,
            )
        )
    except KeyboardInterrupt:
        logger.info("사용자에 의해 대시보드가 종료되었습니다.")
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {e}")


if __name__ == "__main__":
    cli()
