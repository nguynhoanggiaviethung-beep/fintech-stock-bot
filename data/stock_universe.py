from __future__ import annotations

import json

from data.dnse_client import DNSEDataClient


class StockUniverse:
    """
    Quản lý danh sách cổ phiếu từ DNSE.

    Nguồn:
        DNSE /market/instruments

    Chỉ lấy instrument có:
        securityGroupId = "ST"

    Các instrument khác như:
        - FU: hợp đồng tương lai
        - các nhóm sản phẩm khác

    sẽ không được đưa vào stock universe.
    """

    def __init__(
        self,
        page_size: int = 100,
    ):
        self.dnse = DNSEDataClient()
        self.page_size = page_size

    def get_instruments(self) -> list[dict]:
        """
        Lấy toàn bộ instruments từ DNSE.

        DNSE API hỗ trợ phân trang nên method này
        sẽ tiếp tục gọi API cho đến khi lấy đủ total.
        """

        instruments = []

        page = 1

        while True:
            status_code, response_text = (
                self.dnse.client.get_instruments(
                    limit=self.page_size,
                    page=page,
                )
            )

            if status_code != 200:
                raise RuntimeError(
                    "DNSE instruments API error: "
                    f"{status_code} - {response_text}"
                )

            response = json.loads(response_text)

            data = response.get("data", [])

            if not data:
                break

            instruments.extend(data)

            total = response.get("total")

            if total is not None:
                if len(instruments) >= total:
                    break

            if len(data) < self.page_size:
                break

            page += 1

        return instruments

    def get_stock_instruments(self) -> list[dict]:
        """
        Lấy các instrument thuộc nhóm cổ phiếu.
        """

        instruments = self.get_instruments()

        stocks = [
            instrument
            for instrument in instruments
            if instrument.get("securityGroupId") == "ST"
        ]

        return stocks

    def get_symbols(self) -> list[str]:
        """
        Trả về danh sách mã cổ phiếu.
        """

        stocks = self.get_stock_instruments()

        symbols = [
            stock.get("symbol")
            for stock in stocks
            if stock.get("symbol")
        ]

        return sorted(set(symbols))