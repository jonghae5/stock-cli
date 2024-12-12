import yaml
import logging
import sys

from typing import List, Dict, Any

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("dashboard.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# 구성 파일 로드
def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    try:
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
        logger.info("Configuration loaded successfully.")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file '{config_path}' not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)


CONFIG = load_config()


# 기본 설정
DEFAULT_GRAPH_SYMBOLS: List[str] = CONFIG.get(
    "symbols", ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-ADA", "KRW-DOGE"]
)
DEFAULT_GRAPH_UPDATE_INTERVAL: int = CONFIG.get("update_interval", 10)
DEFAULT_GRAPH_TABLE_TITLE: str = CONFIG.get("table_title", "업비트 암호화폐 대시보드")
DEFAULT_GRAPH_COLUMNS: List[Dict[str, Any]] = CONFIG.get(
    "columns",
    [
        {"name": "Symbol", "style": "cyan dim", "justify": "left"},
        {"name": "Last Price", "style": "green dim", "justify": "right"},
        {"name": "Change (%)", "style": "magenta dim", "justify": "right"},
        {"name": "Volume", "style": "yellow dim", "justify": "right"},
        {"name": "High", "style": "bright_red dim", "justify": "right"},
        {"name": "Low", "style": "bright_blue dim", "justify": "right"},
    ],
)

DEFAULT_GRAPH_TIMEFRAMES: List[Dict[str, Any]] = CONFIG.get(
    "timeframes",
    [
        {"name": "1H", "unit": 60, "count": 60},
        {"name": "15M", "unit": 15, "count": 60},
        {"name": "5M", "unit": 5, "count": 60},
    ],
)


DEFAULT_PRICE_SYMBOLS: List[str] = CONFIG.get(
    "symbols", ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-ADA", "KRW-DOGE"]
)
DEFAULT_PRICE_UPDATE_INTERVAL: int = CONFIG.get("update_interval", 10)
DEFAULT_PRICE_TABLE_TITLE: str = CONFIG.get(
    "table_title", "Upbit Cryptocurrency Dashboard"
)
DEFAULT_PRICE_COLUMNS: List[Dict[str, Any]] = CONFIG.get(
    "columns",
    [
        {"name": "Symbol", "style": "cyan dim", "justify": "left"},
        {"name": "Last Price", "style": "green dim", "justify": "right"},
        {"name": "Change (%)", "style": "magenta dim", "justify": "right"},
        {"name": "Volume", "style": "yellow dim", "justify": "right"},
        {"name": "High", "style": "bright_red dim", "justify": "right"},
        {"name": "Low", "style": "bright_blue dim", "justify": "right"},
    ],
)



# 필요한 설정들
DEFAULT_STOCK_PRICE_SYMBOLS: List[str] = CONFIG.get(
    "stock_symbols", ["AAPL", "MSFT", "GOOGL"]
)
DEFAULT_STOCK_PRICE_UPDATE_INTERVAL: int = CONFIG.get("update_interval", 10)  # 10초에 한번 업데이트
DEFAULT_STOCK_PRICE_TABLE_TITLE: str = "Stock Dashboard"
# 컬럼 설정 (심볼, 시가, 종가, 변동률, 거래량, 고가, 저가)
DEFAULT_STOCK_PRICE_COLUMNS: List[Dict[str, Any]] = CONFIG.get(
    "stock_columns",
    [
        {"name": "Symbol", "style": "cyan dim", "justify": "left"},
        {"name": "Yesterday", "style": "white dim", "justify": "right"},
        {"name": "Today", "style": "green dim", "justify": "right"},
        {"name": "Change (%)", "style": "magenta dim", "justify": "right"},
        {"name": "Volume", "style": "yellow dim", "justify": "right"},
        {"name": "High", "style": "bright_red dim", "justify": "right"},
        {"name": "Low", "style": "bright_blue dim", "justify": "right"},
]
)


