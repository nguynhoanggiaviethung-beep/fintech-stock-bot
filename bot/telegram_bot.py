import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from data.market_updater import MarketUpdater
from data.data_manager import DataManager
from analysis.signal_engine import SignalEngine
from analysis.chart_engine import ChartEngine
from analysis.stock_scanner import StockScanner
from analysis.backtest_runner import BacktestRunner


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# ============================================================
# SHARED SERVICES
# ============================================================

data_manager = DataManager()
market_updater = MarketUpdater(
    cache=data_manager.market_manager.cache,
    fetch_func=lambda: data_manager.market_manager.get_market_data(
        symbol="VNINDEX",
        days=60,
    ),
    interval_seconds=300,
)
signal_engine = SignalEngine()
chart_engine = ChartEngine()


# ============================================================
# SUBSCRIPTION CONFIGURATION
# ============================================================

SUBSCRIPTION_FILE = Path(
    "data/subscriptions.json"
)

# Kiểm tra cảnh báo mỗi 15 phút
ALERT_INTERVAL_SECONDS = 15 * 60

subscription_state = {
    "subscriptions": {},
    "last_signals": {},
}

alert_task = None

# ============================================================
# WATCHLIST / PORTFOLIO STORAGE
# ============================================================

WATCHLIST_FILE = Path(
    "data/watchlist.json"
)

PORTFOLIO_FILE = Path(
    "data/portfolio.json"
)

watchlist_state = {
    "symbols": []
}

portfolio_state = {
    "positions": {}
}


def _load_watchlist():
    global watchlist_state

    if not WATCHLIST_FILE.exists():
        watchlist_state = {
            "symbols": []
        }
        return

    try:
        with open(
            WATCHLIST_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        symbols = data.get("symbols", [])

        watchlist_state = {
            "symbols": sorted(
                set(
                    str(symbol).upper().strip()
                    for symbol in symbols
                    if str(symbol).strip()
                )
            )
        }

    except (
        json.JSONDecodeError,
        OSError,
        TypeError,
    ):
        watchlist_state = {
            "symbols": []
        }


def _save_watchlist():
    WATCHLIST_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        WATCHLIST_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            watchlist_state,
            file,
            ensure_ascii=False,
            indent=2,
        )


def _load_portfolio():
    global portfolio_state

    if not PORTFOLIO_FILE.exists():
        portfolio_state = {
            "positions": {}
        }
        return

    try:
        with open(
            PORTFOLIO_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        portfolio_state = {
            "positions": data.get(
                "positions",
                {},
            )
        }

    except (
        json.JSONDecodeError,
        OSError,
        TypeError,
    ):
        portfolio_state = {
            "positions": {}
        }


def _save_portfolio():
    PORTFOLIO_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        PORTFOLIO_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            portfolio_state,
            file,
            ensure_ascii=False,
            indent=2,
        )
# ============================================================
# HELPERS
# ============================================================

def _get_timestamp_range(days: int = 90):
    """
    Tạo khoảng thời gian lấy dữ liệu thị trường.
    """

    now = datetime.now(timezone.utc)

    end_timestamp = int(
        now.timestamp()
    )

    start_timestamp = int(
        now.timestamp()
        - days * 24 * 60 * 60
    )

    return (
        start_timestamp,
        end_timestamp,
    )


def _format_number(
    value,
    decimals=2,
):
    """
    Format số an toàn để hiển thị trên Telegram.
    """

    if value is None:
        return "N/A"

    try:
        return f"{float(value):,.{decimals}f}"

    except (
        TypeError,
        ValueError,
    ):
        return "N/A"


def _format_pct(value):
    """
    Format phần trăm.
    """

    if value is None:
        return "N/A"

    try:
        return f"{float(value):.2f}%"

    except (
        TypeError,
        ValueError,
    ):
        return "N/A"



def _format_price(value):
    """
    Format giá cổ phiếu.
    """

    if value is None:
        return "N/A"

    try:
        return f"{float(value):,.2f}"

    except (
        TypeError,
        ValueError,
    ):
        return "N/A"

def _format_signal(signal):
    """Chuyển tín hiệu nội bộ sang nội dung hiển thị trên Telegram."""
    
    signal_map = {
        "BUY": "🟢 MUA",
        "SELL": "🔴 BÁN",
        "NO_SIGNAL": "⚪ KHÔNG CÓ TÍN HIỆU",
    }

    return signal_map.get(
        signal,
        "⚪ KHÔNG CÓ TÍN HIỆU",
    )


def _format_condition(condition):
    """Chuyển trạng thái điều kiện sang tiếng Việt."""
    
    return "ĐẠT" if condition else "KHÔNG ĐẠT"
# ============================================================
# SUBSCRIPTION STORAGE
# ============================================================

def _load_subscription_state():
    """
    Đọc danh sách đăng ký cảnh báo từ file JSON.
    """

    global subscription_state

    if not SUBSCRIPTION_FILE.exists():

        subscription_state = {
            "subscriptions": {},
            "last_signals": {},
        }

        return

    try:

        with open(
            SUBSCRIPTION_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        subscription_state = {
            "subscriptions": data.get(
                "subscriptions",
                {},
            ),
            "last_signals": data.get(
                "last_signals",
                {},
            ),
        }

    except (
        json.JSONDecodeError,
        OSError,
        TypeError,
    ):

        subscription_state = {
            "subscriptions": {},
            "last_signals": {},
        }


def _save_subscription_state():
    """
    Lưu danh sách đăng ký cảnh báo.
    """

    SUBSCRIPTION_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        SUBSCRIPTION_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            subscription_state,
            file,
            ensure_ascii=False,
            indent=2,
        )


def _get_chat_subscriptions(
    chat_id,
):
    """
    Lấy danh sách mã cổ phiếu
    mà một Telegram chat đang theo dõi.
    """

    chat_key = str(chat_id)

    return list(
        subscription_state[
            "subscriptions"
        ].get(
            chat_key,
            [],
        )
    )


def _set_chat_subscriptions(
    chat_id,
    symbols,
):
    """
    Cập nhật danh sách mã đăng ký của một chat.
    """

    chat_key = str(chat_id)

    unique_symbols = sorted(
        set(symbols)
    )

    if unique_symbols:

        subscription_state[
            "subscriptions"
        ][chat_key] = unique_symbols

    else:

        subscription_state[
            "subscriptions"
        ].pop(
            chat_key,
            None,
        )

    _save_subscription_state()


# ============================================================
# SIGNAL SNAPSHOT FOR ALERT
# ============================================================

def _build_signal_snapshot(
    symbol: str,
) -> dict:
    """
    Lấy dữ liệu cần thiết để kiểm tra tín hiệu.

    Không tạo chart và không lấy realtime trade,
    vì alert chỉ cần SignalEngine.
    """

    symbol = (
        symbol.upper()
        .strip()
    )

    if not symbol:

        raise ValueError(
            "Mã cổ phiếu không được để trống."
        )

    start_timestamp, end_timestamp = (
        _get_timestamp_range(
            days=90
        )
    )

    market_df = (
        data_manager.get_market_data(
            symbol=symbol,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            resolution="1D",
        )
    )

    fundamental_df = (
        data_manager.get_fundamental_data(
            symbol=symbol
        )
    )

    if market_df.empty:

        raise ValueError(
            f"Không có dữ liệu thị trường "
            f"cho {symbol}."
        )

    if fundamental_df.empty:

        raise ValueError(
            f"Không có dữ liệu tài chính "
            f"cho {symbol}."
        )

    result = signal_engine.analyze(
        market_df=market_df,
        fundamental_df=fundamental_df,
        symbol=symbol,
    )

    return result


# ============================================================
# ALERT MONITOR
# ============================================================

async def _check_subscriptions(
    application,
):
    """
    Kiểm tra các mã đã đăng ký.

    Chỉ gửi cảnh báo khi tín hiệu thay đổi
    sang MUA hoặc BÁN.
    """

    for chat_id, symbols in list(
        subscription_state[
            "subscriptions"
        ].items()
    ):

        for symbol in list(symbols):

            try:

                result = await asyncio.to_thread(
                    _build_signal_snapshot,
                    symbol,
                )

                current_signal = (
                    result.get("signal")
                    or "NO_SIGNAL"
                )

                chat_signals = (
                    subscription_state[
                        "last_signals"
                    ].setdefault(
                        str(chat_id),
                        {},
                    )
                )

                previous_signal = (
                    chat_signals.get(
                        symbol
                    )
                )

                # ------------------------------------------------
                # Lần đầu kiểm tra:
                # chỉ lưu trạng thái,
                # không gửi cảnh báo.
                # ------------------------------------------------

                if previous_signal is None:

                    chat_signals[
                        symbol
                    ] = current_signal

                    _save_subscription_state()

                    continue

                # ------------------------------------------------
                # Tín hiệu không thay đổi
                # ------------------------------------------------

                if (
                    previous_signal
                    == current_signal
                ):

                    continue

                # ------------------------------------------------
                # Cập nhật trạng thái
                # ------------------------------------------------

                chat_signals[
                    symbol
                ] = current_signal

                _save_subscription_state()

                # ------------------------------------------------
                # Chỉ cảnh báo BUY / SELL
                # ------------------------------------------------

                if current_signal not in {
                    "BUY",
                    "SELL",
                }:

                    continue

                signal_text = _format_signal(
                    current_signal
                )

                message = (
                    "🚨 CẢNH BÁO TÍN HIỆU\n\n"
                    f"📌 Mã: {symbol}\n"
                    f"🎯 Tín hiệu: {signal_text}\n\n"
                    f"• Tăng trưởng doanh thu: "
                    f"{_format_pct(result.get('revenue_growth'))}\n"
                    f"• Tăng trưởng lợi nhuận: "
                    f"{_format_pct(result.get('net_income_growth'))}\n"
                    f"• ROE: "
                    f"{_format_pct(result.get('roe'))}\n"
                    f"• Giá đóng cửa: "
                    f"{_format_price(result.get('close'))}\n"
                    f"• MA20: "
                    f"{_format_price(result.get('price_ma20'))}\n"
                    f"• Tỷ lệ khối lượng: "
                    f"{_format_number(result.get('volume_ratio'))}x"
                )

                await application.bot.send_message(
                    chat_id=int(chat_id),
                    text=message,
                )

            except Exception as error:

                print(
                    f"[ALERT ERROR] "
                    f"{symbol}: {error}"
                )

async def _check_watchlist_alerts(
    application,
):
    """
    Kiểm tra tín hiệu của các mã trong watchlist.

    Watchlist dùng chung cơ chế last_signals
    của subscription theo từng chat.
    """

    if not watchlist_state["symbols"]:
        return

    for chat_id in list(
        subscription_state["subscriptions"].keys()
    ):

        chat_key = str(chat_id)

        subscribed_symbols = set(
            _get_chat_subscriptions(
                chat_id
            )
        )

        # Chỉ alert watchlist cho chat đã
        # đăng ký ít nhất một mã.
        if not subscribed_symbols:
            continue

        for symbol in watchlist_state["symbols"]:

            try:
                result = await asyncio.to_thread(
                    _build_signal_snapshot,
                    symbol,
                )

                current_signal = (
                    result.get("signal")
                    or "NO_SIGNAL"
                )

                chat_signals = (
                    subscription_state[
                        "last_signals"
                    ].setdefault(
                        chat_key,
                        {},
                    )
                )

                watch_key = (
                    f"WATCH_{symbol}"
                )

                previous_signal = (
                    chat_signals.get(
                        watch_key
                    )
                )

                if previous_signal is None:
                    chat_signals[
                        watch_key
                    ] = current_signal

                    _save_subscription_state()

                    continue

                if (
                    previous_signal
                    == current_signal
                ):
                    continue

                chat_signals[
                    watch_key
                ] = current_signal

                _save_subscription_state()

                if current_signal not in {
                    "BUY",
                    "SELL",
                }:
                    continue

                message = (
                    "⭐ SMART WATCHLIST ALERT\n\n"
                    f"📌 Mã: {symbol}\n"
                    f"🎯 Tín hiệu: "
                    f"{_format_signal(current_signal)}\n\n"
                    f"📈 Tăng trưởng DT: "
                    f"{_format_pct(result.get('revenue_growth'))}\n"
                    f"📈 Tăng trưởng LN: "
                    f"{_format_pct(result.get('net_income_growth'))}\n"
                    f"🏦 ROE: "
                    f"{_format_pct(result.get('roe'))}\n"
                    f"📊 Volume Ratio: "
                    f"{_format_number(result.get('volume_ratio'))}x\n"
                    f"📐 Giá / MA20: "
                    f"{_format_price(result.get('close'))} / "
                    f"{_format_price(result.get('price_ma20'))}"
                )

                await application.bot.send_message(
                    chat_id=int(chat_id),
                    text=message,
                )

            except Exception as error:
                print(
                    f"[WATCHLIST ALERT ERROR] "
                    f"{symbol}: {error}"
                )

async def _alert_loop(
    application,
):
    """
    Vòng lặp kiểm tra cảnh báo định kỳ.
    """

    while True:

        try:

            await _check_subscriptions(
                application
            )

            await _check_watchlist_alerts(
                application
            )

        except Exception as error:

            print(
                f"[ALERT LOOP ERROR] "
                f"{error}"
            )

        await asyncio.sleep(
            ALERT_INTERVAL_SECONDS
        )


async def _post_init(
    application,
):
    global alert_task

    _load_subscription_state()
    _load_watchlist()
    _load_portfolio()

    alert_task = asyncio.create_task(
        _alert_loop(application)
    )

    print(
        "Alert monitor started."
    )
    print(
        f"Watchlist loaded: "
        f"{len(watchlist_state['symbols'])} symbols"
    )
    print(
        f"Portfolio loaded: "
        f"{len(portfolio_state['positions'])} positions"
    )
    

async def _post_shutdown(
    application,
):
    """
    Dừng alert loop khi bot shutdown.
    """

    global alert_task

    if alert_task is not None:

        alert_task.cancel()

        try:

            await alert_task

        except asyncio.CancelledError:

            pass

        alert_task = None

# ============================================================
# PORTFOLIO HELPERS
# ============================================================

def _normalize_stock_price(price):
    """
    VNStock trả giá cổ phiếu Việt Nam theo đơn vị nghìn đồng.
    Ví dụ:
        27.7  -> 27,700 VND
        120.5 -> 120,500 VND

    Nếu giá đã ở dạng VND thì giữ nguyên.
    """
    if price is None:
        return None

    price = float(price)

    if 0 < price < 1000:
        return price * 1000

    return price


def _get_position_price(
    symbol,
    position,
):
    """
    Lấy giá hiện tại, ưu tiên realtime.
    Chuẩn hóa đơn vị về VND.
    """

    try:
        realtime = data_manager.get_realtime_trade(
            symbol
        )

        realtime_price = realtime.get(
            "price"
        )

        if realtime_price is not None:
            return _normalize_stock_price(
                realtime_price
            )

    except Exception:
        pass

    current_price = position.get(
        "current_price"
    )

    if current_price is not None:
        return float(current_price)

    return None

# ============================================================
# /portfolio
# ============================================================

async def portfolio(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    positions = portfolio_state.get(
        "positions",
        {},
    )

    if not positions:
        await update.message.reply_text(
            "💼 PORTFOLIO\n\n"
            "Danh mục đang trống.\n\n"
            "Thêm vị thế bằng:\n"
            "/add FPT 1000 120000"
        )
        return

    total_value = 0
    total_cost = 0

    rows = []

    for symbol, position in positions.items():

        quantity = float(
            position.get(
                "quantity",
                0,
            )
        )

        avg_price = float(
            position.get(
                "avg_price",
                0,
            )
        )

        current_price = await asyncio.to_thread(
            _get_position_price,
            symbol,
            position,
        )

        if current_price is None:
            current_price = avg_price

        cost = quantity * avg_price
        value = quantity * current_price
        pnl = value - cost

        total_cost += cost
        total_value += value

        if cost != 0:
            pnl_pct = (
                pnl / cost * 100
            )
        else:
            pnl_pct = 0

        pnl_icon = (
            "🟢"
            if pnl >= 0
            else "🔴"
        )

        rows.append(
            f"{pnl_icon} {symbol}\n"
            f"   SL: {_format_number(quantity, 0)}\n"
            f"   Giá vốn: {_format_price(avg_price)}\n"
            f"   Giá hiện tại: {_format_price(current_price)}\n"
            f"   Giá trị: {_format_number(value, 0)}\n"
            f"   P/L: {_format_number(pnl, 0)} "
            f"({_format_pct(pnl_pct)})"
        )

    total_pnl = (
        total_value - total_cost
    )

    if total_cost != 0:
        total_pnl_pct = (
            total_pnl
            / total_cost
            * 100
        )
    else:
        total_pnl_pct = 0

    message = (
        "💼 PORTFOLIO\n\n"
        + "\n\n".join(rows)
        + "\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"💰 Tổng giá trị: "
        f"{_format_number(total_value, 0)}\n"
        f"💵 Tổng vốn: "
        f"{_format_number(total_cost, 0)}\n"
        f"📈 Tổng P/L: "
        f"{_format_number(total_pnl, 0)} "
        f"({_format_pct(total_pnl_pct)})"
    )

    await update.message.reply_text(
        message
    )


# ============================================================
# /add
# ============================================================

async def add_position(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    /add FPT 1000 120000
    """

    if len(context.args) != 3:
        await update.message.reply_text(
            "❌ Cú pháp:\n"
            "/add FPT 1000 120000\n\n"
            "Trong đó:\n"
            "• FPT = mã cổ phiếu\n"
            "• 1000 = số lượng\n"
            "• 120000 = giá vốn"
        )
        return

    symbol = (
        context.args[0]
        .upper()
        .strip()
    )

    try:
        quantity = float(
            context.args[1]
        )

        avg_price = float(
            context.args[2]
        )

    except ValueError:
        await update.message.reply_text(
            "❌ Số lượng hoặc giá vốn không hợp lệ."
        )
        return

    if (
        not symbol.isalnum()
        or quantity <= 0
        or avg_price <= 0
    ):
        await update.message.reply_text(
            "❌ Dữ liệu vị thế không hợp lệ."
        )
        return

    positions = portfolio_state[
        "positions"
    ]

    if symbol in positions:

        old = positions[symbol]

        old_quantity = float(
            old.get(
                "quantity",
                0,
            )
        )

        old_avg_price = float(
            old.get(
                "avg_price",
                0,
            )
        )

        new_quantity = (
            old_quantity + quantity
        )

        new_avg_price = (
            (
                old_quantity
                * old_avg_price
            )
            + (
                quantity
                * avg_price
            )
        ) / new_quantity

        positions[symbol] = {
            "quantity": new_quantity,
            "avg_price": new_avg_price,
        }

    else:

        positions[symbol] = {
            "quantity": quantity,
            "avg_price": avg_price,
        }

    _save_portfolio()

    await update.message.reply_text(
        "💼 THÊM VỊ THẾ THÀNH CÔNG\n\n"
        f"• Mã: {symbol}\n"
        f"• Số lượng: "
        f"{_format_number(quantity, 0)}\n"
        f"• Giá vốn: "
        f"{_format_price(avg_price)}"
    )


# ============================================================
# /remove
# ============================================================

async def remove_position(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """/remove FPT 500"""
    if len(context.args) != 2:
        await update.message.reply_text("❌ Cú pháp:\n/remove FPT 500")
        return

    symbol = context.args[0].upper().strip()

    try:
        quantity = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Số lượng không hợp lệ.")
        return

    positions = portfolio_state["positions"]

    if symbol not in positions:
        await update.message.reply_text(f"ℹ️ Không có vị thế {symbol}.")
        return

    if quantity <= 0:
        await update.message.reply_text("❌ Số lượng phải lớn hơn 0.")
        return

    current_quantity = float(positions[symbol].get("quantity", 0))

    # --- SỬA TỪ ĐOẠN NÀY ---
    if quantity >= current_quantity:
        positions.pop(symbol)
        message = f"🗑️ ĐÃ XÓA VỊ THẾ\n\n• Mã: {symbol}"
    else:
        positions[symbol]["quantity"] = current_quantity - quantity
        message = (
            "💼 ĐÃ GIẢM VỊ THẾ\n\n"
            f"• Mã: {symbol}\n"
            f"• Số lượng bán: {_format_number(quantity, 0)}\n"
            f"• Còn lại: {_format_number(current_quantity - quantity, 0)}"
        )

    _save_portfolio()

    await update.message.reply_text(message)

# ============================================================
# PORTFOLIO HELPERS
# ============================================================

def _get_position_price(
    symbol,
    position,
):
    """
    Lấy giá hiện tại ưu tiên realtime.
    """

    try:
        realtime = data_manager.get_realtime_trade(
            symbol
        )

        realtime_price = realtime.get(
            "price"
        )

        if realtime_price is not None:
            return float(realtime_price)

    except Exception:
        pass

    current_price = position.get(
        "current_price"
    )

    if current_price is not None:
        return float(current_price)

    return None


# ============================================================
# /portfolio
# ============================================================

async def portfolio(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    positions = portfolio_state.get(
        "positions",
        {},
    )

    if not positions:
        await update.message.reply_text(
            "💼 PORTFOLIO\n\n"
            "Danh mục đang trống.\n\n"
            "Thêm vị thế bằng:\n"
            "/add FPT 1000 120000"
        )
        return

    total_value = 0
    total_cost = 0

    rows = []

    for symbol, position in positions.items():

        quantity = float(
            position.get(
                "quantity",
                0,
            )
        )

        avg_price = float(
            position.get(
                "avg_price",
                0,
            )
        )

        current_price = await asyncio.to_thread(
            _get_position_price,
            symbol,
            position,
        )

        if current_price is None:
            current_price = avg_price

        cost = quantity * avg_price
        value = quantity * current_price
        pnl = value - cost

        total_cost += cost
        total_value += value

        if cost != 0:
            pnl_pct = (
                pnl / cost * 100
            )
        else:
            pnl_pct = 0

        pnl_icon = (
            "🟢"
            if pnl >= 0
            else "🔴"
        )

        rows.append(
            f"{pnl_icon} {symbol}\n"
            f"   SL: {_format_number(quantity, 0)}\n"
            f"   Giá vốn: {_format_price(avg_price)}\n"
            f"   Giá hiện tại: {_format_price(current_price)}\n"
            f"   Giá trị: {_format_number(value, 0)}\n"
            f"   P/L: {_format_number(pnl, 0)} "
            f"({_format_pct(pnl_pct)})"
        )

    total_pnl = (
        total_value - total_cost
    )

    if total_cost != 0:
        total_pnl_pct = (
            total_pnl
            / total_cost
            * 100
        )
    else:
        total_pnl_pct = 0

    message = (
        "💼 PORTFOLIO\n\n"
        + "\n\n".join(rows)
        + "\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"💰 Tổng giá trị: "
        f"{_format_number(total_value, 0)}\n"
        f"💵 Tổng vốn: "
        f"{_format_number(total_cost, 0)}\n"
        f"📈 Tổng P/L: "
        f"{_format_number(total_pnl, 0)} "
        f"({_format_pct(total_pnl_pct)})"
    )

    await update.message.reply_text(
        message
    )


# ============================================================
# /add
# ============================================================

async def add_position(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    /add FPT 1000 120000
    """

    if len(context.args) != 3:
        await update.message.reply_text(
            "❌ Cú pháp:\n"
            "/add FPT 1000 120000\n\n"
            "Trong đó:\n"
            "• FPT = mã cổ phiếu\n"
            "• 1000 = số lượng\n"
            "• 120000 = giá vốn"
        )
        return

    symbol = (
        context.args[0]
        .upper()
        .strip()
    )

    try:
        quantity = float(
            context.args[1]
        )

        avg_price = float(
            context.args[2]
        )

    except ValueError:
        await update.message.reply_text(
            "❌ Số lượng hoặc giá vốn không hợp lệ."
        )
        return

    if (
        not symbol.isalnum()
        or quantity <= 0
        or avg_price <= 0
    ):
        await update.message.reply_text(
            "❌ Dữ liệu vị thế không hợp lệ."
        )
        return

    positions = portfolio_state[
        "positions"
    ]

    if symbol in positions:

        old = positions[symbol]

        old_quantity = float(
            old.get(
                "quantity",
                0,
            )
        )

        old_avg_price = float(
            old.get(
                "avg_price",
                0,
            )
        )

        new_quantity = (
            old_quantity + quantity
        )

        new_avg_price = (
            (
                old_quantity
                * old_avg_price
            )
            + (
                quantity
                * avg_price
            )
        ) / new_quantity

        positions[symbol] = {
            "quantity": new_quantity,
            "avg_price": new_avg_price,
        }

    else:

        positions[symbol] = {
            "quantity": quantity,
            "avg_price": avg_price,
        }

    _save_portfolio()

    await update.message.reply_text(
        "💼 THÊM VỊ THẾ THÀNH CÔNG\n\n"
        f"• Mã: {symbol}\n"
        f"• Số lượng: "
        f"{_format_number(quantity, 0)}\n"
        f"• Giá vốn: "
        f"{_format_price(avg_price)}"
    )


# ============================================================
# /remove
# ============================================================

async def remove_position(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    /remove FPT 500
    """

    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Cú pháp:\n"
            "/remove FPT 500"
        )
        return

    symbol = (
        context.args[0]
        .upper()
        .strip()
    )

    try:
        quantity = float(
            context.args[1]
        )

    except ValueError:
        await update.message.reply_text(
            "❌ Số lượng không hợp lệ."
        )
        return

    positions = portfolio_state[
        "positions"
    ]

    if symbol not in positions:
        await update.message.reply_text(
            f"ℹ️ Không có vị thế {symbol}."
        )
        return

    if quantity <= 0:
        await update.message.reply_text(
            "❌ Số lượng phải lớn hơn 0."
        )
        return

    current_quantity = float(
        positions[symbol].get(
            "quantity",
            0,
        )
    )

    if quantity >= current_quantity:

        positions.pop(
            symbol
        )

        message = (
            "🗑️ ĐÃ XÓA VỊ THẾ\n\n"
            f"• Mã: {symbol}"
        )

    else:

        positions[symbol][
            "quantity"
        ] = (
            current_quantity
            - quantity
        )

        message = (
            "💼 ĐÃ GIẢM VỊ THẾ\n\n"
            f"• Mã: {symbol}\n"
            f"• Số lượng bán: "
            f"{_format_number(quantity, 0)}\n"
            f"• Còn lại: "
            f"{_format_number(current_quantity - quantity, 0)}"
        )

    _save_portfolio()

    await update.message.reply_text(
        message
    )

# ============================================================
# STOCK ANALYSIS
# ============================================================

def build_stock_analysis(
    symbol: str,
) -> dict:
    """
    Lấy dữ liệu và xây dựng stock analysis snapshot.

    Data:
        - Historical market data
        - Realtime trade
        - Fundamental data
        - Technical signal
        - Valuation metrics
        - Chart
    """

    symbol = (
        symbol.upper()
        .strip()
    )

    if not symbol:

        raise ValueError(
            "Mã cổ phiếu không được để trống."
        )

    start_timestamp, end_timestamp = (
        _get_timestamp_range(
            days=90
        )
    )

    # --------------------------------------------------------
    # DATA LAYER
    # --------------------------------------------------------

    market_df = (
        data_manager.get_market_data(
            symbol=symbol,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            resolution="1D",
        )
    )

    fundamental_df = (
        data_manager.get_fundamental_data(
            symbol=symbol
        )
    )

    try:
        realtime_trade = data_manager.get_realtime_trade(
            symbol=symbol
        )
        realtime_error = None

    except Exception as error:
        realtime_trade = {
            "price": None,
            "volume": None,
            "time": None,
            "match_type": None,
        }
        realtime_error = str(error)

    # --------------------------------------------------------
    # VALIDATE DATA
    # --------------------------------------------------------

    if market_df.empty:

        raise ValueError(
            f"Không có dữ liệu thị trường "
            f"cho {symbol}."
        )

    if fundamental_df.empty:

        raise ValueError(
            f"Không có dữ liệu tài chính "
            f"cho {symbol}."
        )

    # --------------------------------------------------------
    # ANALYSIS LAYER
    # --------------------------------------------------------

    signal_result = signal_engine.analyze(
        market_df=market_df,
        fundamental_df=fundamental_df,
        symbol=symbol,
    )

    # --------------------------------------------------------
    # CHART
    # --------------------------------------------------------

    chart_path = (
        chart_engine.create_stock_chart(
            symbol=symbol,
            market_df=market_df,
            signal=signal_result.get(
                "signal"
            ),
        )
    )

    # --------------------------------------------------------
    # LATEST FUNDAMENTAL
    # --------------------------------------------------------

    latest_fundamental = (
        fundamental_df.iloc[0]
    )

    # --------------------------------------------------------
    # LATEST MARKET
    # --------------------------------------------------------

    latest_market = (
        market_df.iloc[-1]
    )
    # --------------------------------------------------------
    # REALTIME
    # --------------------------------------------------------

    realtime_price = realtime_trade.get("price")
    realtime_volume = realtime_trade.get("volume")
    realtime_time = realtime_trade.get("time")
    realtime_match_type = realtime_trade.get("match_type")

    # Nếu có realtime → dùng realtime.
    # Nếu không có realtime → fallback về giá đóng cửa gần nhất.
    if realtime_price is not None:
        display_price = float(realtime_price)
        price_source = "REALTIME"
    else:
        display_price = latest_market.get("close")
        price_source = "LATEST_CLOSE"
    # --------------------------------------------------------
    # RETURN STRUCTURED RESULT
    # --------------------------------------------------------

    return {
        "symbol": symbol,
        "chart_path": chart_path,

        # Market
        "market_close": latest_market.get(
            "close"
        ),
        "display_price": display_price,
        "price_source": price_source,
        "market_volume": latest_market.get(
            "volume"
        ),

        # Realtime
        "realtime_price": realtime_price,
        "realtime_volume": realtime_volume,
        "realtime_time": realtime_time,
        "realtime_match_type": (
        realtime_match_type
        ),
        "realtime_error": realtime_error,

        # Fundamental
        "report_period": (
            latest_fundamental.get(
                "report_period"
            )
        ),
        "revenue": latest_fundamental.get(
            "revenue"
        ),
        "revenue_growth": (
            latest_fundamental.get(
                "revenue_growth"
            )
        ),
        "net_income": (
            latest_fundamental.get(
                "net_income"
            )
        ),
        "net_income_growth": (
            latest_fundamental.get(
                "net_income_growth"
            )
        ),
        "eps": latest_fundamental.get(
            "eps"
        ),
        "roe": latest_fundamental.get(
            "roe"
        ),
        "debt_equity": (
            latest_fundamental.get(
                "debt_equity"
            )
        ),

        # Valuation
        "current_price": (
            latest_fundamental.get(
                "current_price"
            )
        ),
        "market_cap": (
            latest_fundamental.get(
                "market_cap"
            )
        ),
        "shares_outstanding": (
            latest_fundamental.get(
                "shares_outstanding"
            )
        ),
        "bvps": latest_fundamental.get(
            "bvps"
        ),
        "pe": latest_fundamental.get(
            "pe"
        ),
        "pb": latest_fundamental.get(
            "pb"
        ),

        # Signal
        "signal": signal_result.get(
            "signal"
        ),
        "fundamental_pass": (
            signal_result.get(
                "fundamental_pass"
            )
        ),
        "volume_breakout": (
            signal_result.get(
                "volume_breakout"
            )
        ),
        "price_momentum": (
            signal_result.get(
                "price_momentum"
            )
        ),
        "close": signal_result.get(
            "close"
        ),
        "price_ma20": (
            signal_result.get(
                "price_ma20"
            )
        ),
        "volume": signal_result.get(
            "volume"
        ),
        "volume_ma20": (
            signal_result.get(
                "volume_ma20"
            )
        ),
        "volume_ratio": (
            signal_result.get(
                "volume_ratio"
            )
        ),
    }


# ============================================================
# /start
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = (
        "FINSTOCKVN BOT\n\n"
        "Bot phân tích tín hiệu đầu tư "
        "chứng khoán.\n\n"

        "📊 PHÂN TÍCH\n"
        "/market - Tổng quan VNINDEX\n"
        "/signals - Quét tín hiệu BUY\n"
        "/signal ABB - Tín hiệu cổ phiếu\n"
        "/analyze ABB - Phân tích chi tiết + biểu đồ\n"
        "/compare ABB FPT - So sánh 2 cổ phiếu\n"
        "/explain ABB - Giải thích tín hiệu\n"
        "/backtest ABB - Backtest 180 ngày\n"
        "/backtest ABB 365 - Backtest 365 ngày\n\n"

        "⭐ WATCHLIST\n"
        "/watchlist - Xem watchlist\n"
        "/watchadd ABB - Thêm mã\n"
        "/watchremove ABB - Xóa mã\n\n"

        "🔔 ALERT\n"
        "/subscribe ABB - Bật cảnh báo\n"
        "/unsubscribe ABB - Tắt cảnh báo\n\n"

        "💼 PORTFOLIO\n"
        "/portfolio - Xem danh mục\n"
        "/add ABB 1000 25000 - Thêm vị thế\n"
        "/remove ABB 500 - Giảm vị thế\n"
        "/risk - Phân tích rủi ro"
    )

    await update.message.reply_text(
        message
    )


# ============================================================
# /signals
# ============================================================

async def signals(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🔎 Đang quét tín hiệu BUY...\n"
        "Vui lòng chờ trong giây lát."
    )

    try:

        scanner = StockScanner()

        # ----------------------------------------------------
        # Hiện tại quét 20 mã để tránh API load quá lớn.
        # Sẽ tối ưu thành market-wide scan sau.
        # ----------------------------------------------------

        results, stats = await asyncio.to_thread(
            scanner.scan_all,
            limit=20,
        )

        buy_signals = (
            scanner.get_buy_signals(
                results
            )
        )

        # ----------------------------------------------------
        # KHÔNG CÓ TÍN HIỆU MUA
        # ----------------------------------------------------

        if not buy_signals:

            await update.message.reply_text(
                "📊 KẾT QUẢ QUÉT TÍN HIỆU\n\n"
                "Không tìm thấy mã nào thỏa mãn "
                "Strategy 2 trong phạm vi quét hiện tại.\n\n"
                f"• Đã quét: {stats['total']} mã\n"
                f"• MUA: {stats['buy_signals']} mã\n"
                f"• Fundamental PASS: "
                f"{stats['fundamental_pass']} mã\n"
                f"• Volume Breakout PASS: "
                f"{stats['volume_breakout']} mã"
            )

            return

        # ----------------------------------------------------
        # CÓ TÍN HIỆU MUA
        # ----------------------------------------------------

        lines = [
            "📈 TÍN HIỆU MUA HÔM NAY",
            "",
            f"Đã quét: {stats['total']} mã",
            f"Tìm thấy: {len(buy_signals)} mã MUA",
            "",
        ]

        for item in buy_signals:

            symbol = item[
                "symbol"
            ]

            lines.append(
                f"🟢 {symbol}\n"
                f"   • Tăng trưởng doanh thu: "
                f"{_format_pct(item['revenue_growth'])}\n"
                f"   • Tăng trưởng lợi nhuận: "
                f"{_format_pct(item['net_income_growth'])}\n"
                f"   • ROE: "
                f"{_format_pct(item['roe'])}\n"
                f"   • Tỷ lệ khối lượng: "
                f"{_format_number(item['volume_ratio'])}x\n"
                f"   • Giá đóng cửa: "
                f"{_format_price(item['close'])}\n"
                f"   • MA20: "
                f"{_format_price(item['price_ma20'])}\n"
            )

        await update.message.reply_text(
            "\n".join(lines)
        )

    except Exception as error:

        await update.message.reply_text(
            "❌ Không thể quét tín hiệu.\n\n"
            f"Lỗi: {error}"
        )


# ============================================================
# /signal
# ============================================================

async def signal(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.args:

        await update.message.reply_text(
            "Vui lòng nhập mã cổ phiếu.\n\n"
            "Ví dụ:\n"
            "/signal FPT"
        )

        return

    symbol = (
        context.args[0]
        .upper()
        .strip()
    )

    if not symbol.isalnum():

        await update.message.reply_text(
            "❌ Mã cổ phiếu không hợp lệ."
        )

        return

    await update.message.reply_text(
        f"🔍 Đang phân tích {symbol}..."
    )

    try:

        result = await asyncio.to_thread(
            build_stock_analysis,
            symbol,
        )

        signal_value = result["signal"]

        signal_text = _format_signal(
                signal_value
            )

        message = (
            f"📊 {symbol} — TÍN HIỆU CỔ PHIẾU\n\n"

            f"🎯 TÍN HIỆU\n"
            f"• {signal_text}\n\n"

            f"🏦 PHÂN TÍCH CƠ BẢN\n"
            f"• Tăng trưởng doanh thu: "
            f"{_format_pct(result['revenue_growth'])}\n"
            f"• Tăng trưởng lợi nhuận: "
            f"{_format_pct(result['net_income_growth'])}\n"
            f"• ROE: "
            f"{_format_pct(result['roe'])}\n\n"

            f"📈 PHÂN TÍCH KỸ THUẬT\n"
            f"• Giá đóng cửa: "
            f"{_format_price(result['close'])}\n"
            f"• MA20: "
            f"{_format_price(result['price_ma20'])}\n"
            f"• Khối lượng: "
            f"{_format_number(result['volume'])}\n"
            f"• Khối lượng MA20: "
            f"{_format_number(result['volume_ma20'])}\n"
            f"• Tỷ lệ khối lượng: "
            f"{_format_number(result['volume_ratio'])}x\n\n"

            f"🔎 ĐIỀU KIỆN CHIẾN LƯỢC\n"
            f"• Cơ bản: "
            f"{_format_condition(result['fundamental_pass'])}\n"
            f"• Bứt phá khối lượng: "
            f"{_format_condition(result['volume_breakout'])}\n"
            f"• Động lượng giá: "
            f"{_format_condition(result['price_momentum'])}"
        )

        await update.message.reply_text(
            message
        )

    except Exception as error:

        await update.message.reply_text(
            f"❌ Không thể phân tích "
            f"{symbol}.\n\n"
            f"Lỗi: {error}"
        )


# ============================================================
# /analyze
# ============================================================

async def analyze(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.args:

        await update.message.reply_text(
            "Vui lòng nhập mã cổ phiếu.\n\n"
            "Ví dụ:\n"
            "/analyze FPT"
        )

        return

    symbol = (
        context.args[0]
        .upper()
        .strip()
    )

    if not symbol.isalnum():

        await update.message.reply_text(
            "❌ Mã cổ phiếu không hợp lệ."
        )

        return

    await update.message.reply_text(
        f"📈 Đang phân tích chi tiết "
        f"{symbol}..."
    )

    try:

        result = await asyncio.to_thread(
            build_stock_analysis,
            symbol,
        )

        signal_value = result["signal"]

        signal_text = _format_signal(
            signal_value
        )

        realtime_price = result["realtime_price"]

        realtime_volume = result["realtime_volume"]

        realtime_time = result["realtime_time"]

        match_type = result["realtime_match_type"]

        realtime_time = (
            result["realtime_time"]
        )

        match_type = (
            result["realtime_match_type"]
        )

        message = (
            f"📊 {symbol} — PHÂN TÍCH CỔ PHIẾU\n\n"

            f"💰 THỊ TRƯỜNG\n"
            f"• Giá hiện tại: "
            f"{_format_price(result['display_price'])}\n"
            f"• Nguồn giá: "
            f"{'Realtime' if result['price_source'] == 'REALTIME' else 'Giá đóng cửa gần nhất'}\n"
            f"• Giá đóng cửa gần nhất: "
            f"{_format_price(result['market_close'])}\n"
            f"• Khối lượng phiên gần nhất: "
            f"{_format_number(result['market_volume'])}\n\n"

            f"⚡ KHỚP LỆNH GẦN NHẤT\n"
            f"• Giá: "
            f"{_format_price(realtime_price) if realtime_price is not None else 'Chưa có dữ liệu'}\n"
            f"• Khối lượng: "
            f"{_format_number(realtime_volume) if realtime_volume is not None else 'Chưa có dữ liệu'}\n"
            f"• Loại khớp: "
            f"{match_type or 'Chưa có dữ liệu'}\n"
            f"• Thời gian: "
            f"{realtime_time or 'Chưa có dữ liệu'}\n"
            f"• Trạng thái: "
            f"{'Đang có dữ liệu realtime' if realtime_price is not None else 'Dữ liệu realtime hiện chưa khả dụng  (ngoài thời gian giao dịch hoặc dữ liệu chưa được mở)'}\n\n"

            f"🏦 PHÂN TÍCH CƠ BẢN\n"
            f"• Kỳ báo cáo: "
            f"{result['report_period'] or 'N/A'}\n"
            f"• Doanh thu: "
            f"{_format_number(result['revenue'])}\n"
            f"• Tăng trưởng doanh thu: "
            f"{_format_pct(result['revenue_growth'])}\n"
            f"• Lợi nhuận ròng: "
            f"{_format_number(result['net_income'])}\n"
            f"• Tăng trưởng lợi nhuận: "
            f"{_format_pct(result['net_income_growth'])}\n"
            f"• EPS: "
            f"{_format_number(result['eps'])}\n"
            f"• ROE: "
            f"{_format_pct(result['roe'])}\n"
            f"• D/E: "
            f"{_format_number(result['debt_equity'])}\n\n"

            f"📐 ĐỊNH GIÁ\n"
            f"• BVPS: "
            f"{_format_number(result['bvps'])}\n"
            f"• P/E: "
            f"{_format_number(result['pe'])}\n"
            f"• P/B: "
            f"{_format_number(result['pb'])}\n"
            f"• Vốn hóa: "
            f"{_format_number(result['market_cap'])}\n\n"

            f"🎯 TÍN HIỆU\n"
            f"• {signal_text}\n"
            f"• Điều kiện cơ bản: "
            f"{_format_condition(result['fundamental_pass'])}\n"
            f"• Bứt phá khối lượng: "
            f"{_format_condition(result['volume_breakout'])}\n"
            f"• Động lượng giá: "
            f"{_format_condition(result['price_momentum'])}"
        )

        await update.message.reply_text(
            message
        )

        chart_path = (
            result.get("chart_path")
        )

        if chart_path:

            with open(
                chart_path,
                "rb",
            ) as chart_file:

                await update.message.reply_photo(
                    photo=chart_file,
                    caption=(
                        f"📈 {symbol} — "
                        f"Price & Volume Chart"
                    ),
                )

    except Exception as error:

        await update.message.reply_text(
            f"❌ Không thể phân tích "
            f"{symbol}.\n\n"
            f"Lỗi: {error}"
        )

# ============================================================
# /compare
# ============================================================

async def compare(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    So sánh 2 cổ phiếu.

    Cú pháp:

        /compare ACB FPT
    """

    # --------------------------------------------------------
    # Kiểm tra số lượng mã
    # --------------------------------------------------------

    if len(context.args) != 2:

        await update.message.reply_text(
            "❌ Vui lòng nhập đúng 2 mã cổ phiếu.\n\n"
            "Ví dụ:\n"
            "/compare ACB FPT"
        )

        return

    symbols = [
        argument.upper().strip()
        for argument in context.args
    ]

    # --------------------------------------------------------
    # Kiểm tra mã hợp lệ
    # --------------------------------------------------------

    if not all(
        symbol.isalnum()
        for symbol in symbols
    ):

        await update.message.reply_text(
            "❌ Mã cổ phiếu không hợp lệ."
        )

        return

    symbol_1, symbol_2 = symbols

    await update.message.reply_text(
        f"📊 Đang so sánh {symbol_1} và {symbol_2}...\n"
        "Vui lòng chờ trong giây lát."
    )

    try:

        # ----------------------------------------------------
        # Lấy dữ liệu song song
        # ----------------------------------------------------

        result_1, result_2 = await asyncio.gather(
            asyncio.to_thread(
                build_stock_analysis,
                symbol_1,
            ),
            asyncio.to_thread(
                build_stock_analysis,
                symbol_2,
            ),
        )

        # ----------------------------------------------------
        # Message
        # ----------------------------------------------------

        def _condition_text(value):
            return "✅ ĐẠT" if value else "❌ KHÔNG ĐẠT"


        def _build_compare_section(symbol, data):
            realtime_price = data.get("realtime_price")

            if realtime_price is not None:
                price = realtime_price
            else:
                price = data.get("current_price")

            market_cap = data.get("market_cap")

            if market_cap is not None:
                market_cap_text = f"{market_cap / 1_000_000_000:,.2f} tỷ"
            else:
                market_cap_text = "N/A"

            return (
                f"🔵 {symbol}\n\n"

                f"💰 Giá hiện tại: "
                f"{_format_price(price)}\n"

                f"📈 Tăng trưởng DT: "
                f"{_format_pct(data.get('revenue_growth'))}\n"

                f"📈 Tăng trưởng LN: "
                f"{_format_pct(data.get('net_income_growth'))}\n"

                f"🏦 ROE: "
                f"{_format_pct(data.get('roe'))}\n"

                f"💳 D/E: "
                f"{_format_number(data.get('debt_equity'))}\n"

                f"💵 EPS: "
                f"{_format_number(data.get('eps'), 0)}\n"

                f"📐 P/E: "
                f"{_format_number(data.get('pe'))}\n"

                f"📐 P/B: "
                f"{_format_number(data.get('pb'))}\n"

                f"💼 Vốn hóa: "
                f"{market_cap_text}\n\n"

                f"🎯 Strategy 2\n"

                f"• Cơ bản: "
                f"{_condition_text(data.get('fundamental_pass'))}\n"

                f"• Volume Breakout: "
                f"{_condition_text(data.get('volume_breakout'))}\n"

                f"• Price Momentum: "
                f"{_condition_text(data.get('price_momentum'))}\n"

                f"• Tín hiệu: "
                f"{_format_signal(data.get('signal'))}"
            )
        
        message = (
            f"📊 SO SÁNH CỔ PHIẾU\n"
            f"{symbol_1} ↔ {symbol_2}\n\n"

            f"━━━━━━━━━━━━━━━━\n"
            f"{_build_compare_section(symbol_1, result_1)}\n\n"

            f"━━━━━━━━━━━━━━━━\n"
            f"{_build_compare_section(symbol_2, result_2)}"
        )

        await update.message.reply_text(
            message
        )

    except Exception as error:

        await update.message.reply_text(
            "❌ Không thể so sánh cổ phiếu.\n\n"
            f"Lỗi: {error}"
        )
# ============================================================
# /explain
# ============================================================

async def explain(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Giải thích chi tiết vì sao cổ phiếu
    đạt hoặc không đạt Strategy 2.
    """

    # --------------------------------------------------------
    # Kiểm tra mã
    # --------------------------------------------------------

    if len(context.args) != 1:

        await update.message.reply_text(
            "❌ Vui lòng nhập đúng 1 mã cổ phiếu.\n\n"
            "Ví dụ:\n"
            "/explain ACB"
        )

        return

    symbol = (
        context.args[0]
        .upper()
        .strip()
    )

    if not symbol.isalnum():

        await update.message.reply_text(
            "❌ Mã cổ phiếu không hợp lệ."
        )

        return

    await update.message.reply_text(
        f"🔍 Đang giải thích tín hiệu {symbol}..."
    )

    try:

        result = await asyncio.to_thread(
            build_stock_analysis,
            symbol,
        )

        # ----------------------------------------------------
        # Fundamental values
        # ----------------------------------------------------

        revenue_growth = result.get(
            "revenue_growth"
        )

        net_income_growth = result.get(
            "net_income_growth"
        )

        roe = result.get(
            "roe"
        )

        # ----------------------------------------------------
        # Technical values
        # ----------------------------------------------------

        close = result.get(
            "close"
        )

        price_ma20 = result.get(
            "price_ma20"
        )

        volume_ratio = result.get(
            "volume_ratio"
        )

        # ----------------------------------------------------
        # Conditions
        # ----------------------------------------------------

        revenue_pass = (
            revenue_growth is not None
            and revenue_growth > 15
        )

        net_income_pass = (
            net_income_growth is not None
            and net_income_growth > 15
        )

        roe_pass = (
            roe is not None
            and roe > 15
        )

        volume_pass = (
            volume_ratio is not None
            and volume_ratio >= 1.5
        )

        momentum_pass = (
            close is not None
            and price_ma20 is not None
            and close > price_ma20
        )

        fundamental_pass = (
            revenue_pass
            and net_income_pass
            and roe_pass
        )

        # ----------------------------------------------------
        # Signal
        # ----------------------------------------------------

        signal_value = result.get(
            "signal"
        )

        if signal_value == "MUA":

            signal_text = "🟢 MUA"

        elif signal_value == "BÁN":

            signal_text = "🔴 BÁN"

        else:

            signal_text = "⚪ KHÔNG CÓ TÍN HIỆU"

        # ----------------------------------------------------
        # Fundamental explanation
        # ----------------------------------------------------

        if revenue_growth is None:

            revenue_text = (
                "❌ Revenue Growth\n"
                "   Không có dữ liệu"
            )

        elif revenue_pass:

            revenue_text = (
                "✅ Revenue Growth\n"
                f"   {_format_pct(revenue_growth)} > 15%"
            )

        else:

            revenue_text = (
                "❌ Revenue Growth\n"
                f"   {_format_pct(revenue_growth)} ≤ 15%"
            )

        if net_income_growth is None:

            net_income_text = (
                "❌ Net Income Growth\n"
                "   Không có dữ liệu"
            )

        elif net_income_pass:

            net_income_text = (
                "✅ Net Income Growth\n"
                f"   {_format_pct(net_income_growth)} > 15%"
            )

        else:

            net_income_text = (
                "❌ Net Income Growth\n"
                f"   {_format_pct(net_income_growth)} ≤ 15%"
            )

        if roe is None:

            roe_text = (
                "❌ ROE\n"
                "   Không có dữ liệu"
            )

        elif roe_pass:

            roe_text = (
                "✅ ROE\n"
                f"   {_format_pct(roe)} > 15%"
            )

        else:

            roe_text = (
                "❌ ROE\n"
                f"   {_format_pct(roe)} ≤ 15%"
            )

        # ----------------------------------------------------
        # Volume explanation
        # ----------------------------------------------------

        if volume_ratio is None:

            volume_text = (
                "❌ Volume Breakout\n"
                "   Không có dữ liệu"
            )

        elif volume_pass:

            volume_text = (
                "✅ Volume Breakout\n"
                f"   Volume Ratio: "
                f"{_format_number(volume_ratio)}x\n"
                "   Yêu cầu: ≥ 1.50x"
            )

        else:

            volume_text = (
                "❌ Volume Breakout\n"
                f"   Volume Ratio: "
                f"{_format_number(volume_ratio)}x\n"
                "   Yêu cầu: ≥ 1.50x"
            )

        # ----------------------------------------------------
        # Momentum explanation
        # ----------------------------------------------------

        if (
            close is None
            or price_ma20 is None
        ):

            momentum_text = (
                "❌ Price Momentum\n"
                "   Không có đủ dữ liệu"
            )

        elif momentum_pass:

            momentum_text = (
                "✅ Price Momentum\n"
                f"   Close: {_format_price(close)}\n"
                f"   MA20: {_format_price(price_ma20)}\n"
                "   Yêu cầu: Close > MA20"
            )

        else:

            momentum_text = (
                "❌ Price Momentum\n"
                f"   Close: {_format_price(close)}\n"
                f"   MA20: {_format_price(price_ma20)}\n"
                "   Yêu cầu: Close > MA20"
            )

        # ----------------------------------------------------
        # Conclusion
        # ----------------------------------------------------

        if signal_value == "MUA":

            conclusion = (
                "💡 KẾT LUẬN\n\n"
                "Cổ phiếu thỏa mãn đầy đủ "
                "các điều kiện BUY của Strategy 2."
            )

        elif signal_value == "BÁN":

            conclusion = (
                "💡 KẾT LUẬN\n\n"
                "Cổ phiếu đang có tín hiệu SELL "
                "theo điều kiện thoát lệnh."
            )

        else:

            failed_conditions = []

            if not fundamental_pass:
                failed_conditions.append(
                    "Fundamental"
                )

            if not volume_pass:
                failed_conditions.append(
                    "Volume Breakout"
                )

            if not momentum_pass:
                failed_conditions.append(
                    "Price Momentum"
                )

            conclusion = (
                "💡 KẾT LUẬN\n\n"
                "Cổ phiếu chưa thỏa mãn đầy đủ "
                "các điều kiện của Strategy 2.\n\n"
                "Điều kiện chưa đạt: "
                + ", ".join(
                    failed_conditions
                )
            )

        # ----------------------------------------------------
        # Final message
        # ----------------------------------------------------

        message = (
            f"📊 GIẢI THÍCH TÍN HIỆU\n"
            f"{symbol}\n\n"

            f"🎯 KẾT QUẢ\n"
            f"{signal_text}\n\n"

            f"━━━━━━━━━━━━━━━━\n"
            f"📌 FUNDAMENTAL\n\n"

            f"{revenue_text}\n\n"
            f"{net_income_text}\n\n"
            f"{roe_text}\n\n"

            f"→ Fundamental: "
            f"{'✅ ĐẠT' if fundamental_pass else '❌ KHÔNG ĐẠT'}\n\n"

            f"━━━━━━━━━━━━━━━━\n"
            f"📈 TECHNICAL\n\n"

            f"{volume_text}\n\n"
            f"{momentum_text}\n\n"

            f"━━━━━━━━━━━━━━━━\n"
            f"{conclusion}"
        )

        await update.message.reply_text(
            message
        )

    except Exception as error:

        await update.message.reply_text(
            f"❌ Không thể giải thích "
            f"tín hiệu {symbol}.\n\n"
            f"Lỗi: {error}"
        )
# ============================================================
# /subscribe
# ============================================================

async def subscribe(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Đăng ký cảnh báo cho một mã cổ phiếu.
    """

    if not context.args:

        await update.message.reply_text(
            "Vui lòng nhập mã cổ phiếu.\n\n"
            "Ví dụ:\n"
            "/subscribe ABB"
        )

        return

    symbol = (
        context.args[0]
        .upper()
        .strip()
    )

    if not symbol.isalnum():

        await update.message.reply_text(
            "❌ Mã cổ phiếu không hợp lệ."
        )

        return

    chat_id = update.effective_chat.id

    symbols = _get_chat_subscriptions(
        chat_id
    )

    if symbol in symbols:

        await update.message.reply_text(
            f"🔔 {symbol} đã được đăng ký "
            "cảnh báo trước đó."
        )

        return

    await update.message.reply_text(
        f"🔎 Đang kiểm tra {symbol}..."
    )

    try:

        result = await asyncio.to_thread(
            _build_signal_snapshot,
            symbol,
        )

        current_signal = (
            result.get("signal")
            or "NO_SIGNAL"
        )

        symbols.append(
            symbol
        )

        _set_chat_subscriptions(
            chat_id,
            symbols,
        )

        subscription_state[
            "last_signals"
        ].setdefault(
            str(chat_id),
            {},
        )[symbol] = current_signal

        _save_subscription_state()

        await update.message.reply_text(
            "🔔 ĐĂNG KÝ CẢNH BÁO THÀNH CÔNG\n\n"
            f"• Mã: {symbol}\n"
            f"• Tín hiệu hiện tại: "
            f"{_format_signal(current_signal)}\n"
            f"• Kiểm tra định kỳ: "
            f"{ALERT_INTERVAL_SECONDS // 60} phút\n\n"
            "Bot sẽ gửi thông báo khi tín hiệu "
            "chuyển sang MUA hoặc BÁN."
        )

    except Exception as error:

        await update.message.reply_text(
            f"❌ Không thể đăng ký "
            f"{symbol}.\n\n"
            f"Lỗi: {error}"
        )


# ============================================================
# /unsubscribe
# ============================================================

async def unsubscribe(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Hủy đăng ký cảnh báo cho một mã.
    """

    if not context.args:

        await update.message.reply_text(
            "Vui lòng nhập mã cổ phiếu.\n\n"
            "Ví dụ:\n"
            "/unsubscribe ABB"
        )

        return

    symbol = (
        context.args[0]
        .upper()
        .strip()
    )

    if not symbol.isalnum():

        await update.message.reply_text(
            "❌ Mã cổ phiếu không hợp lệ."
        )

        return

    chat_id = update.effective_chat.id

    symbols = _get_chat_subscriptions(
        chat_id
    )

    if symbol not in symbols:

        await update.message.reply_text(
            f"ℹ️ Bạn chưa đăng ký "
            f"cảnh báo {symbol}."
        )

        return

    symbols.remove(
        symbol
    )

    _set_chat_subscriptions(
        chat_id,
        symbols,
    )

    chat_key = str(
        chat_id
    )

    if chat_key in subscription_state[
        "last_signals"
    ]:

        subscription_state[
            "last_signals"
        ][chat_key].pop(
            symbol,
            None,
        )

        if not subscription_state[
            "last_signals"
        ][chat_key]:

            subscription_state[
                "last_signals"
            ].pop(
                chat_key,
                None,
            )

    _save_subscription_state()

    await update.message.reply_text(
        "🔕 HỦY CẢNH BÁO THÀNH CÔNG\n\n"
        f"Bạn đã hủy theo dõi {symbol}."
    )


# ============================================================
# BACKTEST HELPER
# ============================================================

def _run_backtest(
    symbol: str,
    days: int,
) -> dict:
    """
    Hàm synchronous để chạy backtest.

    Telegram handler gọi hàm này thông qua
    asyncio.to_thread().
    """

    start_timestamp, end_timestamp = (
        _get_timestamp_range(
            days=days
        )
    )

    market_df = (
        data_manager.get_market_data(
            symbol=symbol,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            resolution="1D",
        )
    )

    fundamental_df = (
        data_manager.get_fundamental_data(
            symbol=symbol
        )
    )

    if market_df.empty:

        raise ValueError(
            f"Không có dữ liệu thị trường "
            f"cho {symbol}."
        )

    if fundamental_df.empty:

        raise ValueError(
            f"Không có dữ liệu tài chính "
            f"cho {symbol}."
        )

    runner = BacktestRunner()

    result = runner.run(
        market_df=market_df,
        fundamental_df=fundamental_df,
        symbol=symbol,
    )

    return {
        "symbol": symbol,
        "market_df": market_df,
        "fundamental_df": fundamental_df,
        "backtest": result[
            "backtest"
        ],
        "signals": result[
            "signals"
        ],
    }


# ============================================================
# /backtest
# ============================================================

async def backtest(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Chạy backtest Strategy 2.

    Cú pháp:

        /backtest ABB

    hoặc:

        /backtest ABB 365
    """

    if not context.args:

        await update.message.reply_text(
            "Vui lòng nhập mã cổ phiếu.\n\n"
            "Ví dụ:\n"
            "/backtest ABB\n"
            "/backtest ABB 365"
        )

        return

    symbol = (
        context.args[0]
        .upper()
        .strip()
    )

    if not symbol.isalnum():

        await update.message.reply_text(
            "❌ Mã cổ phiếu không hợp lệ."
        )

        return

    # --------------------------------------------------------
    # Số ngày backtest
    # --------------------------------------------------------

    days = 180

    if len(context.args) >= 2:

        try:

            days = int(
                context.args[1]
            )

        except ValueError:

            await update.message.reply_text(
                "❌ Số ngày không hợp lệ.\n\n"
                "Ví dụ:\n"
                "/backtest ABB 180"
            )

            return

    if days < 30 or days > 1000:

        await update.message.reply_text(
            "❌ Khoảng backtest phải từ "
            "30 đến 1000 ngày."
        )

        return

    await update.message.reply_text(
        f"📊 Đang chạy backtest {symbol}...\n"
        f"Khoảng thời gian: {days} ngày\n\n"
        "Vui lòng chờ trong giây lát."
    )

    try:

        result = await asyncio.to_thread(
            _run_backtest,
            symbol,
            days,
        )

        backtest_result = result[
            "backtest"
        ]

        market_df = result[
            "market_df"
        ]

        # ----------------------------------------------------
        # Metrics
        # ----------------------------------------------------

        total_return = (
            backtest_result.get(
                "total_return_pct"
            )
        )

        win_rate = (
            backtest_result.get(
                "win_rate"
            )
        )

        average_trade_return = (
            backtest_result.get(
                "average_trade_return"
            )
        )

        best_trade = (
            backtest_result.get(
                "best_trade"
            )
        )

        worst_trade = (
            backtest_result.get(
                "worst_trade"
            )
        )

        profit_factor = (
            backtest_result.get(
                "profit_factor"
            )
        )

        max_drawdown = (
            backtest_result.get(
                "max_drawdown"
            )
        )

        initial_capital = (
            backtest_result.get(
                "initial_capital"
            )
        )

        final_capital = (
            backtest_result.get(
                "final_capital"
            )
        )

        total_trades = (
            backtest_result.get(
                "total_trades",
                0,
            )
        )

        winning_trades = (
            backtest_result.get(
                "winning_trades",
                0,
            )
        )

        losing_trades = (
            backtest_result.get(
                "losing_trades",
                0,
            )
        )

        # ----------------------------------------------------
        # Message
        # ----------------------------------------------------

        message = (
            f"📊 BACKTEST — {symbol}\n\n"

            f"📅 THỜI GIAN\n"
            f"• Từ: "
            f"{market_df['datetime'].iloc[0]}\n"
            f"• Đến: "
            f"{market_df['datetime'].iloc[-1]}\n"
            f"• Số phiên giao dịch: "
            f"{len(market_df)}\n\n"

            f"💰 HIỆU SUẤT\n"
            f"• Vốn ban đầu: "
            f"{_format_number(initial_capital, 0)}\n"
            f"• Vốn cuối kỳ: "
            f"{_format_number(final_capital, 0)}\n"
            f"• Tổng lợi nhuận: "
            f"{_format_pct(total_return)}\n"
            f"• Mức sụt giảm tối đa: "
            f"{_format_pct(max_drawdown)}\n\n"

            f"📈 GIAO DỊCH\n"
            f"• Tổng số giao dịch: "
            f"{total_trades}\n"
            f"• Giao dịch có lãi: "
            f"{winning_trades}\n"
            f"• Giao dịch thua lỗ: "
            f"{losing_trades}\n"
            f"• Tỷ lệ thắng: "
            f"{_format_pct(win_rate)}\n"
            f"• Lợi nhuận giao dịch trung bình: "
            f"{_format_pct(average_trade_return)}\n"
            f"• Giao dịch tốt nhất: "
            f"{_format_pct(best_trade)}\n"
            f"• Giao dịch tệ nhất: "
            f"{_format_pct(worst_trade)}\n"
            f"• Hệ số lợi nhuận: "
            f"{_format_number(profit_factor)}\n\n"

            f"🎯 CHIẾN LƯỢC 2\n"
            f"• Tăng trưởng doanh thu > 15%\n"
            f"• Tăng trưởng lợi nhuận sau thuế > 15%\n"
            f"• ROE > 15%\n"
            f"• Khối lượng đột biến ≥ 1.5× MA20\n"
            f"• Giá đóng cửa > MA20\n"
            f"• Điểm vào lệnh: Giá mở cửa phiên kế tiếp"
        )

        await update.message.reply_text(
            message
        )

    except Exception as error:

        await update.message.reply_text(
            "❌ Không thể chạy backtest.\n\n"
            f"Lỗi: {error}"
        )

async def explain(update, context):
    if not context.args:
        await update.message.reply_text(
            "❗ Cú pháp:\n"
            "/explain <MÃ>\n\n"
            "Ví dụ:\n"
            "/explain BVL"
        )
        return

    symbol = context.args[0].upper().strip()

    try:
        result = await asyncio.to_thread(
            build_stock_analysis,
            symbol,
        )

        signal_value = result.get("signal", "NO_SIGNAL")

        if signal_value == "BUY":
            signal_text = "🟢 BUY"
        elif signal_value == "SELL":
            signal_text = "🔴 SELL"
        else:
            signal_text = "⚪ KHÔNG CÓ TÍN HIỆU"

        fundamental_pass = result.get("fundamental_pass", False)
        volume_breakout = result.get("volume_breakout", False)
        price_momentum = result.get("price_momentum", False)

        reasons = []

        if fundamental_pass:
            reasons.append("• Cơ bản: ✅ ĐẠT")
        else:
            reasons.append("• Cơ bản: ❌ KHÔNG ĐẠT")

        if volume_breakout:
            reasons.append("• Bứt phá khối lượng: ✅ ĐẠT")
        else:
            reasons.append("• Bứt phá khối lượng: ❌ KHÔNG ĐẠT")

        if price_momentum:
            reasons.append("• Động lượng giá: ✅ ĐẠT")
        else:
            reasons.append("• Động lượng giá: ❌ KHÔNG ĐẠT")

        revenue_growth = result.get("revenue_growth")
        net_income_growth = result.get("net_income_growth")
        roe = result.get("roe")

        if revenue_growth is not None:
            revenue_text = f"{revenue_growth:.2f}%"
        else:
            revenue_text = "N/A"

        if net_income_growth is not None:
            income_text = f"{net_income_growth:.2f}%"
        else:
            income_text = "N/A"

        if roe is not None:
            roe_text = f"{roe:.2f}%"
        else:
            roe_text = "N/A"

        message = (
            f"🔎 GIẢI THÍCH TÍN HIỆU — {symbol}\n\n"

            f"🎯 Tín hiệu hiện tại: {signal_text}\n\n"

            f"📊 ĐIỀU KIỆN CƠ BẢN\n"
            f"• Tăng trưởng doanh thu: {revenue_text} "
            f"(yêu cầu > 15%)\n"
            f"• Tăng trưởng lợi nhuận: {income_text} "
            f"(yêu cầu > 15%)\n"
            f"• ROE: {roe_text} "
            f"(yêu cầu > 15%)\n\n"

            f"🔎 ĐIỀU KIỆN CHIẾN LƯỢC\n"
            + "\n".join(reasons)
            + "\n\n"

            f"📌 KẾT LUẬN\n"
        )

        if signal_value == "BUY":
            message += (
                "Cổ phiếu thỏa mãn các điều kiện BUY của Strategy 2."
            )
        elif signal_value == "SELL":
            message += (
                "Cổ phiếu đang thỏa mãn điều kiện SELL của hệ thống."
            )
        else:
            failed_conditions = []

            if not fundamental_pass:
                failed_conditions.append("điều kiện cơ bản")

            if not volume_breakout:
                failed_conditions.append("bứt phá khối lượng")

            if not price_momentum:
                failed_conditions.append("động lượng giá")

            if failed_conditions:
                message += (
                    "Chưa có tín hiệu vì chưa đồng thời đạt: "
                    + ", ".join(failed_conditions)
                    + "."
                )
            else:
                message += (
                    "Các điều kiện chính chưa tạo thành tín hiệu BUY/SELL."
                )

        await update.message.reply_text(message)

    except Exception as exc:
        await update.message.reply_text(
            f"❌ Không thể phân tích {symbol}.\n"
            f"Lỗi: {exc}"
        )

# ============================================================
# /market
# ============================================================

async def market(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Tổng quan VNINDEX.

    VNINDEX được lấy qua VNStock và được quản lý bởi
    MarketUpdater + MarketCache.

    Không sử dụng DNSE cho /market.
    """

    print("[MARKET] command received", flush=True)

    await update.message.reply_text(
        "📊 Đang lấy dữ liệu thị trường..."
    )

    try:
        # ----------------------------------------------------
        # Import cần thiết
        # ----------------------------------------------------

        from data.market_cache import MarketCache
        from data.market_updater import MarketUpdater
        from vnstock import stock_historical_data

        # ----------------------------------------------------
        # Hàm lấy dữ liệu VNINDEX
        # ----------------------------------------------------

        def fetch_vnindex():
            end_date = pd.Timestamp.now().strftime(
                "%Y-%m-%d"
            )

            start_date = (
                pd.Timestamp.now()
                - pd.Timedelta(days=60)
            ).strftime("%Y-%m-%d")

            print(
                "[MARKET] fetching VNINDEX from VNStock",
                flush=True,
            )

            df = stock_historical_data(
                "VNINDEX",
                start_date,
                end_date,
                "1D",
                "index",
            )

            if df is None:
                return pd.DataFrame()

            if not isinstance(df, pd.DataFrame):
                return pd.DataFrame()

            if df.empty:
                return pd.DataFrame()

            return df

        # ----------------------------------------------------
        # Tạo Cache + Updater một lần
        # ----------------------------------------------------
        #
        # Dùng attribute của function để giữ cache/updater
        # giữa các lần gọi /market.
        #
        # Không cần sửa thêm code bên ngoài.
        # ----------------------------------------------------

        if not hasattr(market, "_market_cache"):

            print(
                "[MARKET] initializing MarketCache",
                flush=True,
            )

            market._market_cache = MarketCache()

            market._market_updater = MarketUpdater(
                cache=market._market_cache,
                fetch_func=fetch_vnindex,
                interval_seconds=300,
            )

        market_cache = market._market_cache
        market_updater = market._market_updater

        # ----------------------------------------------------
        # Lấy dữ liệu
        # ----------------------------------------------------

        print(
            "[MARKET] updating VNINDEX",
            flush=True,
        )

        market_df = await asyncio.to_thread(
            market_updater.update_once
        )

        print(
            "[MARKET] updater returned",
            flush=True,
        )

        # ----------------------------------------------------
        # Kiểm tra dữ liệu
        # ----------------------------------------------------

        if (
            market_df is None
            or not isinstance(
                market_df,
                pd.DataFrame,
            )
            or market_df.empty
        ):
            raise ValueError(
                "Không có dữ liệu VNINDEX."
            )

        # ----------------------------------------------------
        # Chuẩn hóa thứ tự thời gian
        # ----------------------------------------------------

        if "datetime" in market_df.columns:

            market_df = (
                market_df
                .sort_values(
                    "datetime"
                )
                .reset_index(
                    drop=True
                )
            )

        # ----------------------------------------------------
        # Latest
        # ----------------------------------------------------

        latest = market_df.iloc[-1]

        close = latest.get("close")
        volume = latest.get("volume")

        # ----------------------------------------------------
        # Previous close
        # ----------------------------------------------------

        previous_close = None

        if len(market_df) >= 2:

            previous_close = (
                market_df.iloc[-2]
                .get("close")
            )

        # ----------------------------------------------------
        # Change %
        # ----------------------------------------------------

        if (
            close is not None
            and previous_close is not None
            and float(previous_close) != 0
        ):

            change_pct = (
                (
                    float(close)
                    - float(previous_close)
                )
                / float(previous_close)
                * 100
            )

        else:

            change_pct = None

        # ----------------------------------------------------
        # Format change
        # ----------------------------------------------------

        if change_pct is None:

            change_text = "N/A"

        elif change_pct > 0:

            change_text = (
                f"🟢 +{change_pct:.2f}%"
            )

        elif change_pct < 0:

            change_text = (
                f"🔴 {change_pct:.2f}%"
            )

        else:

            change_text = "⚪ 0.00%"

        # ----------------------------------------------------
        # Latest date
        # ----------------------------------------------------

        latest_datetime = latest.get(
            "datetime"
        )

        if latest_datetime is not None:

            date_text = str(
                latest_datetime
            )

        else:

            date_text = "N/A"

        # ----------------------------------------------------
        # Kiểm tra updater có lỗi trước đó không
        # ----------------------------------------------------

        last_error = (
            market_updater.get_last_error()
        )

        cache_note = ""

        if last_error is not None:

            cache_note = (
                "\n⚠️ DNSE/VNStock cập nhật chậm; "
                "bot đang sử dụng dữ liệu cache gần nhất."
            )

        # ----------------------------------------------------
        # Message
        # ----------------------------------------------------

        message = (
            "📊 TỔNG QUAN THỊ TRƯỜNG\n\n"

            "🇻🇳 VNINDEX\n"
            f"• Điểm số: "
            f"{_format_price(close)}\n"

            f"• Thay đổi: "
            f"{change_text}\n"

            f"• Khối lượng: "
            f"{_format_number(volume, 0)}\n"

            f"• Phiên gần nhất: "
            f"{date_text}\n\n"

            "📅 DỮ LIỆU\n"
            f"• Số phiên: "
            f"{len(market_df)}\n"

            "• Nguồn: VNStock\n"
            "• Bộ cập nhật: MarketUpdater\n"

            f"{cache_note}\n\n"

            "💡 VNINDEX được sử dụng để cung cấp "
            "bối cảnh thị trường; tín hiệu BUY/SELL "
            "vẫn được xác định riêng theo Strategy 2."
        )

        await update.message.reply_text(
            message
        )

        print(
            "[MARKET] response sent",
            flush=True,
        )

    except Exception as error:

        print(
            f"[MARKET ERROR] {error}",
            flush=True,
        )

        await update.message.reply_text(
            "❌ Không thể lấy dữ liệu thị trường.\n\n"
            f"Lỗi: {error}"
        )
# ============================================================
# /watchlist
# ============================================================

async def watchlist(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    symbols = watchlist_state.get(
        "symbols",
        [],
    )

    if not symbols:
        await update.message.reply_text(
            "⭐ WATCHLIST\n\n"
            "Watchlist đang trống.\n\n"
            "Thêm mã bằng:\n"
            "/watchadd FPT"
        )
        return

    lines = [
        "⭐ WATCHLIST",
        "",
    ]

    for symbol in symbols:
        lines.append(
            f"• {symbol}"
        )

    lines.extend([
        "",
        "Thêm: /watchadd FPT",
        "Xóa: /watchremove FPT",
        "",
        "Watchlist được dùng để theo dõi "
        "tín hiệu Strategy 2."
    ])

    await update.message.reply_text(
        "\n".join(lines)
    )


# ============================================================
# /watchadd
# ============================================================

async def watchadd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if len(context.args) != 1:
        await update.message.reply_text(
            "❌ Cú pháp:\n"
            "/watchadd FPT"
        )
        return

    symbol = (
        context.args[0]
        .upper()
        .strip()
    )

    if not symbol.isalnum():
        await update.message.reply_text(
            "❌ Mã cổ phiếu không hợp lệ."
        )
        return

    if symbol in watchlist_state["symbols"]:
        await update.message.reply_text(
            f"⭐ {symbol} đã có trong watchlist."
        )
        return

    await update.message.reply_text(
        f"🔎 Đang kiểm tra {symbol}..."
    )

    try:
        result = await asyncio.to_thread(
            _build_signal_snapshot,
            symbol,
        )

        current_signal = (
            result.get("signal")
            or "NO_SIGNAL"
        )

        watchlist_state["symbols"].append(
            symbol
        )

        watchlist_state["symbols"] = sorted(
            set(watchlist_state["symbols"])
        )

        _save_watchlist()

        await update.message.reply_text(
            "⭐ THÊM WATCHLIST THÀNH CÔNG\n\n"
            f"• Mã: {symbol}\n"
            f"• Tín hiệu hiện tại: "
            f"{_format_signal(current_signal)}\n\n"
            "Bot sẽ theo dõi thay đổi tín hiệu "
            "Strategy 2 của mã này."
        )

    except Exception as error:
        await update.message.reply_text(
            f"❌ Không thể thêm {symbol}.\n\n"
            f"Lỗi: {error}"
        )


# ============================================================
# /watchremove
# ============================================================

async def watchremove(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if len(context.args) != 1:
        await update.message.reply_text(
            "❌ Cú pháp:\n"
            "/watchremove FPT"
        )
        return

    symbol = (
        context.args[0]
        .upper()
        .strip()
    )

    if symbol not in watchlist_state["symbols"]:
        await update.message.reply_text(
            f"ℹ️ {symbol} không có trong watchlist."
        )
        return

    watchlist_state["symbols"].remove(
        symbol
    )

    _save_watchlist()

    await update.message.reply_text(
        "🗑️ ĐÃ XÓA KHỎI WATCHLIST\n\n"
        f"• Mã: {symbol}"
    )
def _get_chat_portfolio(chat_id):
    chat_id = str(chat_id)

    if chat_id not in portfolio_state:
        portfolio_state[chat_id] = {}

    return portfolio_state[chat_id]

def _get_current_price(symbol):
    symbol = symbol.upper().strip()

    # Ưu tiên giá realtime
    try:
        realtime = data_manager.get_realtime_trade(symbol)

        if realtime and realtime.get("price") is not None:
            return float(realtime["price"])
    except Exception:
        pass

    # Nếu không lấy được realtime thì lấy giá đóng cửa gần nhất
    start_timestamp, end_timestamp = _get_timestamp_range(30)

    market_df = data_manager.get_market_data(
        symbol,
        start_timestamp,
        end_timestamp,
    )

    if market_df is None or market_df.empty:
        raise ValueError(f"Không lấy được dữ liệu giá của {symbol}")

    latest_close = market_df.iloc[-1].get("close")

    if latest_close is None:
        raise ValueError(f"Không có giá đóng cửa của {symbol}")

    return float(latest_close)

# ============================================================
# /risk
# ============================================================

async def risk(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Phân tích rủi ro danh mục hiện tại.

    Rule:
        - Tỷ trọng một mã > 30%  -> cảnh báo tập trung
        - P/L <= -5%             -> cảnh báo mức lỗ
    """

    positions = portfolio_state.get(
        "positions",
        {},
    )

    # --------------------------------------------------------
    # Portfolio trống
    # --------------------------------------------------------

    if not positions:

        await update.message.reply_text(
            "⚠️ PORTFOLIO RỦI RO\n\n"
            "Danh mục đang trống.\n\n"
            "Thêm vị thế bằng:\n"
            "/add A32 100 27500"
        )

        return

    # --------------------------------------------------------
    # Tính giá trị từng vị thế
    # --------------------------------------------------------

    rows = []

    total_value = 0

    for symbol, position in positions.items():

        quantity = float(
            position.get(
                "quantity",
                0,
            )
        )

        avg_price = float(
            position.get(
                "avg_price",
                0,
            )
        )

        current_price = await asyncio.to_thread(
            _get_position_price,
            symbol,
            position,
        )

        # Nếu không lấy được realtime
        # dùng giá vốn để không làm crash risk
        if current_price is None:
            current_price = avg_price

        cost = (
            quantity
            * avg_price
        )

        value = (
            quantity
            * current_price
        )

        pnl = (
            value
            - cost
        )

        if cost != 0:

            pnl_pct = (
                pnl
                / cost
                * 100
            )

        else:

            pnl_pct = 0

        total_value += value

        rows.append(
            {
                "symbol": symbol,
                "quantity": quantity,
                "avg_price": avg_price,
                "current_price": current_price,
                "cost": cost,
                "value": value,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
            }
        )

    # --------------------------------------------------------
    # Phân tích rủi ro
    # --------------------------------------------------------

    lines = [
        "⚠️ PORTFOLIO RỦI RO",
        "",
        f"💰 Tổng giá trị: "
        f"{_format_number(total_value, 0)}",
        "",
    ]

    for row in rows:

        symbol = row["symbol"]
        value = row["value"]
        pnl_pct = row["pnl_pct"]

        if total_value != 0:

            weight = (
                value
                / total_value
                * 100
            )

        else:

            weight = 0

        warnings = []

        # ----------------------------------------------------
        # Concentration risk
        # ----------------------------------------------------

        if weight > 30:

            warnings.append(
                "⚠️ Tập trung >30%"
            )

        # ----------------------------------------------------
        # Loss risk
        # ----------------------------------------------------

        if pnl_pct <= -5:

            warnings.append(
                "🛑 P/L ≤ -5%"
            )

        if not warnings:

            warnings.append(
                "✅ Không có cảnh báo"
            )

        lines.append(
            f"📌 {symbol}\n"
            f"   • Tỷ trọng: "
            f"{_format_pct(weight)}\n"
            f"   • P/L: "
            f"{_format_pct(pnl_pct)}\n"
            f"   • "
            f"{' | '.join(warnings)}\n"
        )

    # --------------------------------------------------------
    # Rule hệ thống
    # --------------------------------------------------------

    lines.extend(
        [
            "━━━━━━━━━━━━━━━━",
            "📋 QUY TẮC RỦI RO",
            "",
            "• Tỷ trọng >30%: cảnh báo tập trung",
            "• P/L ≤ -5%: cảnh báo mức lỗ",
            "",
            "ℹ️ Đây là cảnh báo theo rule "
            "của hệ thống, không tự động bán."
        ]
    )

    await update.message.reply_text(
        "\n".join(lines)
    )
    
# ============================================================
# CREATE BOT
# ============================================================

def create_bot():

    if not TOKEN:

        raise ValueError(
            "Không tìm thấy TELEGRAM_BOT_TOKEN "
            "trong file .env"
        )

    application = (
        Application
        .builder()
        .token(TOKEN)
        .updater(None)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )

    # --------------------------------------------------------
    # COMMAND HANDLERS
    # --------------------------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "signals",
            signals,
        )
    )

    application.add_handler(
        CommandHandler(
            "signal",
            signal,
        )
    )

    application.add_handler(
        CommandHandler(
            "analyze",
            analyze,
        )
    )

    application.add_handler(
        CommandHandler(
            "compare",
            compare,
        )
    )

    application.add_handler(
        CommandHandler(
            "explain",
            explain,
        )
    )

    application.add_handler(
        CommandHandler(
            "subscribe",
            subscribe,
        )
    )

    application.add_handler(
        CommandHandler(
            "unsubscribe",
            unsubscribe,
        )
    )

    application.add_handler(
        CommandHandler(
            "backtest",
            backtest,
        )
    )

    application.add_handler(
        CommandHandler(
            "market",
            market,
        )
    )

    application.add_handler(
        CommandHandler(
            "watchlist",
            watchlist,
        )
    )

    application.add_handler(
        CommandHandler(
            "watchadd",
            watchadd,
        )
    )

    application.add_handler(
        CommandHandler(
            "watchremove",
            watchremove,
        )
    )

    application.add_handler(
        CommandHandler(
            "portfolio",
            portfolio,
        )
    )

    application.add_handler(
        CommandHandler(
            "add",
            add_position,
        )
    )

    application.add_handler(
        CommandHandler(
            "remove",
            remove_position,
        )
    )

    application.add_handler(
        CommandHandler(
            "risk",
            risk,
        )
    )
    return application