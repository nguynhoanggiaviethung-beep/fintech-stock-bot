import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest import result

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

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
    """
    Khởi tạo subscription và alert loop
    khi Telegram bot bắt đầu chạy.
    """

    global alert_task

    _load_subscription_state()

    alert_task = asyncio.create_task(
        _alert_loop(application)
    )

    print(
        "Alert monitor started."
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

        "Các lệnh:\n"
        "/start - Xem hướng dẫn\n"
        "/signals - Xem tín hiệu BUY hôm nay\n"
        "/signal ABB - Xem tín hiệu cổ phiếu\n"
        "/analyze ABB - Phân tích chi tiết + biểu đồ\n"
        "/subscribe ABB - Đăng ký cảnh báo\n"
        "/unsubscribe ABB - Hủy cảnh báo\n"
        "/backtest ABB - Backtest 180 ngày\n"
        "/backtest ABB 365 - Backtest 365 ngày"
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
            f"{_format_price(realtime_price) if realtime_price is not None else 'Chưa có dữ liệu realtime'}\n"
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
            f"{'Đang có dữ liệu realtime' if realtime_price is not None else 'Dữ liệu realtime hiện chưa khả dụng'}\n\n"

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

    return application