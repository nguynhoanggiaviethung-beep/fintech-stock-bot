from datetime import datetime, timezone
import json

import pandas as pd

from data.dnse_client import DNSEDataClient
from data.vnstock_client import VnstockFundamentalClient
from analysis.backtest_runner import BacktestRunner


SYMBOLS = [
    "ABB",
    "ABC",
    "ACB",
    "FPT",
]

START_DATE = "2026-03-01"
END_DATE = "2026-08-31"


def datetime_to_timestamp(dt):
    return int(dt.timestamp())


def load_dnse_ohlcv(symbol, start_date, end_date):
    """
    Lấy dữ liệu OHLCV thật từ DNSE.
    """

    client = DNSEDataClient()

    start_dt = datetime.strptime(
        start_date,
        "%Y-%m-%d",
    ).replace(tzinfo=timezone.utc)

    end_dt = datetime.strptime(
        end_date,
        "%Y-%m-%d",
    ).replace(
        hour=23,
        minute=59,
        second=59,
        tzinfo=timezone.utc,
    )

    response_text = client.get_historical_ohlcv(
        symbol=symbol,
        start_timestamp=datetime_to_timestamp(start_dt),
        end_timestamp=datetime_to_timestamp(end_dt),
        resolution="1D",
    )

    data = json.loads(response_text)

    df = pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                data["t"],
                unit="s",
            ),
            "open": data["o"],
            "high": data["h"],
            "low": data["l"],
            "close": data["c"],
            "volume": data["v"],
        }
    )

    return df


def load_fundamental(symbol):
    """
    Lấy fundamental thật từ VNStock.

    Backtest V1 sử dụng năm báo cáo mới nhất
    làm bộ fundamental cố định.
    """

    client = VnstockFundamentalClient()

    result = client.get_annual_fundamentals(
        symbol
    )

    if result is None or result.empty:
        raise ValueError(
            f"Không lấy được fundamental data cho {symbol}"
        )

    return result.iloc[[0]].copy()


def run_single_stock(symbol):
    """
    Chạy backtest cho một mã.
    """

    print("\n" + "=" * 70)
    print(f"BACKTEST: {symbol}")
    print("=" * 70)

    print("[1] Loading OHLCV...")

    market_df = load_dnse_ohlcv(
        symbol=symbol,
        start_date=START_DATE,
        end_date=END_DATE,
    )

    if market_df.empty:
        raise ValueError(
            f"OHLCV rỗng cho {symbol}"
        )

    print(
        f"OHLCV rows: {len(market_df)}"
    )

    print("[2] Loading fundamental...")

    fundamental_df = load_fundamental(
        symbol
    )

    print(
        fundamental_df.to_string(
            index=False
        )
    )

    print("[3] Running backtest...")

    runner = BacktestRunner()

    result = runner.run(
        fundamental_df=fundamental_df,
        market_df=market_df,
    )

    signals_df = result["signals"]
    backtest = result["backtest"]

    print("[4] Result")

    print(
        f"Signals      : "
        f"{signals_df['signal'].value_counts().to_dict()}"
    )

    print(
        f"Trades       : "
        f"{backtest['total_trades']}"
    )

    print(
        f"Win rate     : "
        f"{backtest['win_rate']:.2f}%"
    )

    print(
        f"Total return : "
        f"{backtest['total_return_pct']:.2f}%"
    )

    print(
        f"Profit factor: "
        f"{backtest['profit_factor']}"
    )

    print(
        f"Max drawdown : "
        f"{backtest['max_drawdown']:.2f}%"
    )

    return {
        "symbol": symbol,
        "signals": signals_df,
        "backtest": backtest,
    }


def main():

    print("=" * 70)
    print("MULTI-STOCK BACKTEST TEST")
    print("=" * 70)

    print(f"Symbols    : {SYMBOLS}")
    print(f"Start date : {START_DATE}")
    print(f"End date   : {END_DATE}")

    results = []
    errors = []

    for symbol in SYMBOLS:

        try:
            result = run_single_stock(
                symbol
            )

            results.append(result)

        except Exception as exc:

            print(
                f"\nERROR {symbol}: {exc}"
            )

            errors.append(
                {
                    "symbol": symbol,
                    "error": str(exc),
                }
            )

    # --------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------

    print("\n" + "=" * 70)
    print("MULTI-STOCK SUMMARY")
    print("=" * 70)

    if results:

        summary_rows = []

        for result in results:

            backtest = result["backtest"]

            summary_rows.append(
                {
                    "symbol": result["symbol"],
                    "total_trades": backtest[
                        "total_trades"
                    ],
                    "winning_trades": backtest[
                        "winning_trades"
                    ],
                    "losing_trades": backtest[
                        "losing_trades"
                    ],
                    "win_rate": backtest[
                        "win_rate"
                    ],
                    "total_return_pct": backtest[
                        "total_return_pct"
                    ],
                    "average_trade_return": backtest[
                        "average_trade_return"
                    ],
                    "best_trade": backtest[
                        "best_trade"
                    ],
                    "worst_trade": backtest[
                        "worst_trade"
                    ],
                    "profit_factor": backtest[
                        "profit_factor"
                    ],
                    "max_drawdown": backtest[
                        "max_drawdown"
                    ],
                }
            )

        summary_df = pd.DataFrame(
            summary_rows
        )

        print(
            summary_df.to_string(
                index=False
            )
        )

    else:

        print(
            "Không có mã nào backtest thành công."
        )

    # --------------------------------------------------------------
    # ERRORS
    # --------------------------------------------------------------

    print("\n" + "=" * 70)
    print("ERROR SUMMARY")
    print("=" * 70)

    if errors:

        for error in errors:

            print(
                f"{error['symbol']}: "
                f"{error['error']}"
            )

    else:

        print("No errors.")

    # --------------------------------------------------------------
    # FINAL
    # --------------------------------------------------------------

    print("\n" + "=" * 70)
    print("MULTI-STOCK BACKTEST TEST COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()