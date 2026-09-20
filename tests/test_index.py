import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from data.data_manager import MarketDataManager


def main():
    manager = MarketDataManager()

    df = manager.get_historical_index(
        index_symbol="VNINDEX",
        days=30
    )

    print("Rows:", len(df))
    print("Columns:", df.columns.tolist())
    print("\nData:")
    print(df)


if __name__ == "__main__":
    main()