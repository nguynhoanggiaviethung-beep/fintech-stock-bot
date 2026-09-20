from __future__ import annotations

import pandas as pd

from vnstock.api.quote import Quote


class VnstockRealtimeClient:
    """
    Client lấy dữ liệu thị trường gần real-time từ VNStock.

    Nguồn:
    VNStock Quote API.

    Dữ liệu sử dụng:
    - time
    - price
    - volume
    - match_type
    - id
    """

    def __init__(
        self,
        source: str = "VCI",
    ):
        self.source = source

    # ============================================================
    # CREATE QUOTE CLIENT
    # ============================================================

    def _get_quote(
        self,
        symbol: str,
    ) -> Quote:
        """
        Khởi tạo Quote client theo API mới của VNStock.
        """

        return Quote(
            symbol=symbol.upper(),
            source=self.source,
        )

    # ============================================================
    # REAL-TIME INTRADAY
    # ============================================================

    def get_intraday(
        self,
        symbol: str,
        page_size: int = 1,
    ) -> pd.DataFrame:
        """
        Lấy dữ liệu khớp lệnh intraday gần nhất.

        Parameters
        ----------
        symbol : str
            Mã cổ phiếu, ví dụ ABB, ACB, FPT.

        page_size : int
            Số giao dịch muốn lấy.

        Returns
        -------
        pd.DataFrame
            Các cột:
            - time
            - price
            - volume
            - match_type
            - id
        """

        symbol = symbol.upper().strip()

        if not symbol:
            raise ValueError(
                "symbol không được để trống"
            )

        if page_size <= 0:
            raise ValueError(
                "page_size phải lớn hơn 0"
            )

        quote = self._get_quote(symbol)

        df = quote.intraday(
            symbol=symbol,
            page_size=page_size,
        )

        if df is None:
            return pd.DataFrame(
                columns=[
                    "time",
                    "price",
                    "volume",
                    "match_type",
                    "id",
                ]
            )

        if not isinstance(df, pd.DataFrame):
            raise TypeError(
                "VNStock intraday không trả về DataFrame"
            )

        if df.empty:
            return pd.DataFrame(
                columns=[
                    "time",
                    "price",
                    "volume",
                    "match_type",
                    "id",
                ]
            )

        return df.reset_index(
            drop=True
        )

    # ============================================================
    # LATEST TRADE
    # ============================================================

    def get_latest_trade(
        self,
        symbol: str,
    ) -> dict:
        """
        Lấy giao dịch khớp lệnh gần nhất.
        """

        symbol = symbol.upper().strip()

        df = self.get_intraday(
            symbol=symbol,
            page_size=1,
        )

        if df.empty:
            return {
                "symbol": symbol,
                "time": None,
                "price": None,
                "volume": None,
                "match_type": None,
                "id": None,
            }

        row = df.iloc[0]

        return {
            "symbol": symbol,
            "time": row.get("time"),
            "price": row.get("price"),
            "volume": row.get("volume"),
            "match_type": row.get("match_type"),
            "id": row.get("id"),
        }