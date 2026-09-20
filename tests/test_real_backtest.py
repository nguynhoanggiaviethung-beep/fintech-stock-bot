from datetime import datetime, timezone
import json

import pandas as pd

from data.dnse_client import DNSEDataClient
from data.vnstock_client import VnstockFundamentalClient
from analysis.backtest_runner import BacktestRunner


SYMBOL = "ABB"

START_DATE = "2026-03-01"
END_DATE = "2026-08-31"


def datetime_to_timestamp(dt):
    return int(dt.timestamp())


def load_market_data():

    client = DNSEDataClient()

    start_dt = datetime.strptime(
        START_DATE,
        "%Y-%m-%d",
    ).replace(
        tzinfo=timezone.utc
    )

    end_dt = datetime.strptime(
        END_DATE,
        "%Y-%m-%d",
    ).replace(
        hour=23,
        minute=59,
        second=59,
        tzinfo=timezone.utc,
    )

    response_text = (
        client.get_historical_ohlcv(
            symbol=SYMBOL,
            start_timestamp=(
                datetime_to_timestamp(
                    start_dt
                )
            ),
            end_timestamp=(
                datetime_to_timestamp(
                    end_dt
                )
            ),
            resolution="1D",
        )
    )

    data = json.loads(
        response_text
    )

    return pd.DataFrame(
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


def load_fundamental_data():

    client = (
        VnstockFundamentalClient()
    )

    fundamental_df = (
        client.get_annual_fundamentals(
            SYMBOL
        )
    )

    if (
        fundamental_df is None
        or fundamental_df.empty
    ):
        raise ValueError(
            "Không lấy được fundamental data"
        )

    return fundamental_df.iloc[
        [0]
    ].copy()


def main():

    print("=" * 80)
    print("REAL BACKTEST WITH TRADE EXPLANATION")
    print("=" * 80)

    print(
        f"Symbol     : {SYMBOL}"
    )

    print(
        f"Period     : "
        f"{START_DATE} → {END_DATE}"
    )

    # ==========================================================
    # DATA
    # ==========================================================

    print("\n[1] Loading market data...")

    market_df = load_market_data()

    print(
        f"OHLCV rows: {len(market_df)}"
    )

    print("\n[2] Loading fundamental data...")

    fundamental_df = (
        load_fundamental_data()
    )

    print(
        fundamental_df.to_string(
            index=False
        )
    )

    # ==========================================================
    # BACKTEST
    # ==========================================================

    print("\n[3] Running backtest...")

    runner = BacktestRunner()

    result = runner.run(
        fundamental_df=fundamental_df,
        market_df=market_df,
    )

    signals_df = result["signals"]

    backtest = result["backtest"]

    # ==========================================================
    # SIGNAL EXPLANATION
    # ==========================================================

    signal_rows = signals_df[
        signals_df["signal"].isin(
            ["BUY", "SELL"]
        )
    ].copy()

    print("\n" + "=" * 80)
    print("TRADE SIGNAL EXPLANATION")
    print("=" * 80)

    if signal_rows.empty:

        print(
            "Không có BUY/SELL signal."
        )

    else:

        for _, row in signal_rows.iterrows():

            print("\n" + "-" * 80)

            print(
                f"Date        : "
                f"{row['datetime'].date()}"
            )

            print(
                f"Close       : "
                f"{row['close']}"
            )

            print(
                f"Signal      : "
                f"{row['signal']}"
            )

            print(
                f"Executed    : "
                f"{row['executed_action']}"
            )

            print(
                f"Pending     : "
                f"{row['pending_action']}"
            )

            print(
                f"Position    : "
                f"{row['position_after_execution']}"
            )

            print(
                "\nWHY:"
            )

            for reason in (
                row[
                    "explanation_reasons"
                ]
            ):
                print(
                    f"• {reason}"
                )

            print(
                "\nMetrics:"
            )

            for (
                key,
                value,
            ) in row[
                "explanation_metrics"
            ].items():

                print(
                    f"• {key}: {value}"
                )

    # ==========================================================
    # PERFORMANCE
    # ==========================================================

    print("\n" + "=" * 80)
    print("BACKTEST PERFORMANCE")
    print("=" * 80)

    print(
        f"Initial capital : "
        f"{backtest['initial_capital']:,.0f}"
    )

    print(
        f"Final capital   : "
        f"{backtest['final_capital']:,.0f}"
    )

    print(
        f"Total return    : "
        f"{backtest['total_return_pct']:.2f}%"
    )

    print(
        f"Total trades    : "
        f"{backtest['total_trades']}"
    )

    print(
        f"Winning trades  : "
        f"{backtest['winning_trades']}"
    )

    print(
        f"Losing trades   : "
        f"{backtest['losing_trades']}"
    )

    print(
        f"Win rate        : "
        f"{backtest['win_rate']:.2f}%"
    )

    print(
        f"Average return  : "
        f"{backtest['average_trade_return']:.2f}%"
    )

    print(
        f"Best trade      : "
        f"{backtest['best_trade']:.2f}%"
    )

    print(
        f"Worst trade     : "
        f"{backtest['worst_trade']:.2f}%"
    )

    print(
        f"Profit factor   : "
        f"{backtest['profit_factor']:.2f}"
        if backtest["profit_factor"]
        is not None
        else "Profit factor   : N/A"
    )

    print(
        f"Max drawdown    : "
        f"{backtest['max_drawdown']:.2f}%"
    )

    # ==========================================================
    # TRADE TABLE
    # ==========================================================

    print("\n" + "=" * 80)
    print("COMPLETED TRADES")
    print("=" * 80)

    trades_df = backtest["trades"]

    if trades_df.empty:

        print(
            "Không có completed trade."
        )

    else:

        print(
            trades_df.to_string(
                index=False
            )
        )

    print("\n" + "=" * 80)
    print(
        "REAL BACKTEST EXPLANATION TEST COMPLETED"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()