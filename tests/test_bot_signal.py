from datetime import datetime, timezone

from data.data_manager import DataManager
from analysis.signal_engine import SignalEngine


def main():

    symbol = "ABB"

    print("=" * 60)
    print(f"TEST BOT SIGNAL: {symbol}")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. Khởi tạo Data + Analysis layer
    # --------------------------------------------------------

    data_manager = DataManager()
    signal_engine = SignalEngine()

    # --------------------------------------------------------
    # 2. Thời gian: 90 ngày gần nhất
    # --------------------------------------------------------

    now = datetime.now(timezone.utc)

    end_timestamp = int(
        now.timestamp()
    )

    start_timestamp = int(
        now.timestamp()
        - 90 * 24 * 60 * 60
    )

    # --------------------------------------------------------
    # 3. Lấy market data
    # --------------------------------------------------------

    print("\n[1] Getting market data...")

    market_df = data_manager.get_market_data(
        symbol=symbol,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        resolution="1D",
    )

    print(
        f"PASS: market data = "
        f"{len(market_df)} rows"
    )

    # --------------------------------------------------------
    # 4. Lấy fundamental data
    # --------------------------------------------------------

    print("\n[2] Getting fundamental data...")

    fundamental_df = data_manager.get_fundamental_data(
        symbol=symbol
    )

    print(
        f"PASS: fundamental data = "
        f"{len(fundamental_df)} rows"
    )

    # --------------------------------------------------------
    # 5. Chạy Signal Engine
    # --------------------------------------------------------

    print("\n[3] Running Signal Engine...")

    result = signal_engine.analyze(
        market_df=market_df,
        fundamental_df=fundamental_df,
        symbol=symbol,
    )

    print("PASS: Signal Engine")

    # --------------------------------------------------------
    # 6. In kết quả
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("SIGNAL RESULT")
    print("=" * 60)

    print(
        f"Symbol              : "
        f"{result.get('symbol')}"
    )

    print(
        f"Signal              : "
        f"{result.get('signal')}"
    )

    print(
        f"Revenue Growth      : "
        f"{result.get('revenue_growth')}"
    )

    print(
        f"Net Income Growth   : "
        f"{result.get('net_income_growth')}"
    )

    print(
        f"ROE                 : "
        f"{result.get('roe')}"
    )

    print(
        f"Fundamental Pass    : "
        f"{result.get('fundamental_pass')}"
    )

    print(
        f"Close               : "
        f"{result.get('close')}"
    )

    print(
        f"MA20                : "
        f"{result.get('price_ma20')}"
    )

    print(
        f"Volume              : "
        f"{result.get('volume')}"
    )

    print(
        f"Volume MA20         : "
        f"{result.get('volume_ma20')}"
    )

    print(
        f"Volume Ratio        : "
        f"{result.get('volume_ratio')}"
    )

    print(
        f"Volume Breakout     : "
        f"{result.get('volume_breakout')}"
    )

    print(
        f"Price Momentum      : "
        f"{result.get('price_momentum')}"
    )

    print(
        f"Position Held       : "
        f"{result.get('position_held')}"
    )

    print("=" * 60)

    # --------------------------------------------------------
    # 7. Kiểm tra các field bắt buộc
    # --------------------------------------------------------

    required_fields = [
        "symbol",
        "signal",
        "fundamental_pass",
        "revenue_growth",
        "net_income_growth",
        "roe",
        "volume_breakout",
        "price_momentum",
        "volume",
        "volume_ma20",
        "volume_ratio",
        "close",
        "price_ma20",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in result
    ]

    if missing_fields:

        raise AssertionError(
            f"Missing fields: {missing_fields}"
        )

    # --------------------------------------------------------
    # 8. Kiểm tra signal hợp lệ
    # --------------------------------------------------------

    valid_signals = [
        "BUY",
        "SELL",
        "NO_SIGNAL",
    ]

    if result["signal"] not in valid_signals:

        raise AssertionError(
            f"Invalid signal: "
            f"{result['signal']}"
        )

    print(
        "\nALL BOT SIGNAL TESTS PASSED"
    )


if __name__ == "__main__":
    main()