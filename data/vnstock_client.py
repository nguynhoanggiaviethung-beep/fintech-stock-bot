from __future__ import annotations

import pandas as pd

from vnstock.api.company import Company
from vnstock.api.financial import Finance


class VnstockFundamentalClient:
    def __init__(
        self,
        source: str = "VCI",
        period: str = "year",
        show_log: bool = False,
    ):
        self.source = source
        self.period = period
        self.show_log = show_log

    # ============================================================
    # BASIC HELPERS
    # ============================================================

    @staticmethod
    def _get_row(df: pd.DataFrame, item_id: str):
        rows = df[df["item_id"] == item_id]

        if rows.empty:
            return None

        return rows.iloc[0]

    @classmethod
    def _get_first_available_row(
        cls,
        df: pd.DataFrame,
        item_ids: list[str],
    ):
        for item_id in item_ids:
            row = cls._get_row(df, item_id)

            if row is not None:
                return row, item_id

        return None, None

    @staticmethod
    def _get_period_columns(df: pd.DataFrame):
        metadata_columns = {
            "item",
            "item_en",
            "item_id",
            "note",
        }

        return [
            col
            for col in df.columns
            if col not in metadata_columns
        ]

    @staticmethod
    def _to_number(value):
        return pd.to_numeric(
            pd.Series([value]),
            errors="coerce",
        ).iloc[0]

    @staticmethod
    def _calculate_growth(
        current_value,
        previous_value,
    ):
        if pd.isna(current_value):
            return None

        if pd.isna(previous_value):
            return None

        if previous_value == 0:
            return None

        return (
            (current_value / previous_value) - 1
        ) * 100

    # ============================================================
    # FINANCE API
    # ============================================================

    def _get_finance(
        self,
        symbol: str,
    ) -> Finance:
        return Finance(
            source=self.source,
            symbol=symbol.upper(),
            period=self.period,
            get_all=True,
            show_log=self.show_log,
        )

    # ============================================================
    # COMPANY OVERVIEW
    # ============================================================

    def _get_company_overview(
        self,
        symbol: str,
    ):
        """
        Lấy dữ liệu thị trường hiện tại từ Company.overview().

        Dữ liệu sử dụng:
        - current_price
        - market_cap
        - issue_share

        Các dữ liệu này dùng để tính:
        - P/E
        - BVPS
        - P/B
        """

        company = Company(
            source=self.source,
            symbol=symbol.upper(),
            show_log=self.show_log,
        )

        overview = company.overview()

        if overview is None:
            return None

        if not isinstance(overview, pd.DataFrame):
            return None

        if overview.empty:
            return None

        return overview.iloc[0]

    # ============================================================
    # VALUATION
    # ============================================================

    @classmethod
    def _calculate_pe(
        cls,
        current_price,
        eps,
    ):
        """
        P/E = Market Price / EPS

        current_price và EPS đều được sử dụng theo
        đơn vị VND/cổ phiếu.
        """

        current_price = cls._to_number(current_price)
        eps = cls._to_number(eps)

        if pd.isna(current_price):
            return None

        if pd.isna(eps):
            return None

        if eps <= 0:
            return None

        return current_price / eps

    @classmethod
    def _calculate_bvps(
        cls,
        equity,
        shares_outstanding,
    ):
        """
        BVPS = Equity / Shares Outstanding

        Với dữ liệu VNStock đang sử dụng:
        - Equity: VND
        - Shares outstanding: số cổ phiếu
        - BVPS: VND/cổ phiếu

        Không nhân thêm 1e9 vì equity đã ở đơn vị VND.
        """

        equity = cls._to_number(equity)

        shares_outstanding = cls._to_number(
            shares_outstanding
        )

        if pd.isna(equity):
            return None

        if pd.isna(shares_outstanding):
            return None

        if shares_outstanding <= 0:
            return None

        return equity / shares_outstanding

    @classmethod
    def _calculate_pb(
        cls,
        current_price,
        bvps,
    ):
        """
        P/B = Market Price / BVPS

        current_price và BVPS đều ở đơn vị VND/cổ phiếu.
        Vì vậy không cần quy đổi thêm đơn vị.
        """

        current_price = cls._to_number(current_price)
        bvps = cls._to_number(bvps)

        if pd.isna(current_price):
            return None

        if pd.isna(bvps):
            return None

        if bvps <= 0:
            return None

        return current_price / bvps

    # ============================================================
    # MAIN FUNDAMENTAL METHOD
    # ============================================================

    def get_annual_fundamentals(
        self,
        symbol: str,
    ) -> pd.DataFrame:

        symbol = symbol.upper()

        finance = self._get_finance(symbol)

        income = finance.income_statement()
        balance = finance.balance_sheet()

        # ========================================================
        # REVENUE
        # ========================================================

        revenue_row, revenue_item_id = (
            self._get_first_available_row(
                income,
                [
                    "net_sales",
                    "total_operating_income",
                    "net_sales_from_insurance_business",
                ],
            )
        )

        if revenue_row is None:
            raise ValueError(
                f"Không tìm thấy chỉ tiêu Revenue phù hợp cho {symbol}"
            )

        # ========================================================
        # NET INCOME
        # ========================================================

        net_income_row, net_income_item_id = (
            self._get_first_available_row(
                income,
                [
                    "net_profit_loss_after_tax",
                    "profit_after_tax",
                    "net_profit_attributable_to_shareholders_of_the_group",
                ],
            )
        )

        if net_income_row is None:
            raise ValueError(
                f"Không tìm thấy Net Income cho {symbol}"
            )

        # ========================================================
        # EPS
        # ========================================================

        eps_row = self._get_row(
            income,
            "eps_basic_vnd",
        )

        if eps_row is None:
            raise ValueError(
                f"Không tìm thấy EPS cho {symbol}"
            )

        # ========================================================
        # LIABILITIES
        # ========================================================

        liabilities_row, liabilities_item_id = (
            self._get_first_available_row(
                balance,
                [
                    "liabilities",
                    "total_liabilities",
                ],
            )
        )

        if liabilities_row is None:
            raise ValueError(
                f"Không tìm thấy Liabilities cho {symbol}"
            )

        # ========================================================
        # EQUITY
        # ========================================================

        equity_row, equity_item_id = (
            self._get_first_available_row(
                balance,
                [
                    "owners_equity",
                    "owner_equity",
                    "equity",
                ],
            )
        )

        if equity_row is None:
            raise ValueError(
                f"Không tìm thấy Owner's Equity cho {symbol}"
            )

        # ========================================================
        # COMPANY OVERVIEW
        # ========================================================

        overview = self._get_company_overview(symbol)

        current_price = None
        market_cap = None
        shares_outstanding = None

        if overview is not None:

            if "current_price" in overview.index:
                current_price = self._to_number(
                    overview["current_price"]
                )

            if "market_cap" in overview.index:
                market_cap = self._to_number(
                    overview["market_cap"]
                )

            # Company.overview() có thể trả về nhiều cột
            # "issue_share" trùng tên.
            #
            # Lấy issue_share đầu tiên làm số cổ phiếu lưu hành.
            if "issue_share" in overview.index:

                issue_share_positions = [
                    index
                    for index, column in enumerate(overview.index)
                    if column == "issue_share"
                ]

                if issue_share_positions:
                    shares_outstanding = self._to_number(
                        overview.iloc[
                            issue_share_positions[0]
                        ]
                    )

        # ========================================================
        # PERIODS
        # ========================================================

        periods = self._get_period_columns(
            income
        )

        try:
            periods = sorted(
                periods,
                key=lambda x: int(str(x)),
            )

        except (ValueError, TypeError):
            pass

        # ========================================================
        # BUILD RECORDS
        # ========================================================

        records = []

        previous_revenue = None
        previous_net_income = None
        previous_equity = None

        for period in periods:

            revenue = self._to_number(
                revenue_row[period]
            )

            net_income = self._to_number(
                net_income_row[period]
            )

            eps = self._to_number(
                eps_row[period]
            )

            equity = self._to_number(
                equity_row[period]
            )

            liabilities = self._to_number(
                liabilities_row[period]
            )

            # ----------------------------------------------------
            # GROWTH
            # ----------------------------------------------------

            revenue_growth = (
                self._calculate_growth(
                    revenue,
                    previous_revenue,
                )
            )

            net_income_growth = (
                self._calculate_growth(
                    net_income,
                    previous_net_income,
                )
            )

            # ----------------------------------------------------
            # ROE
            # ----------------------------------------------------

            roe = None

            if (
                pd.notna(net_income)
                and pd.notna(equity)
                and previous_equity is not None
                and pd.notna(previous_equity)
            ):

                average_equity = (
                    equity + previous_equity
                ) / 2

                if average_equity != 0:

                    roe = (
                        net_income
                        / average_equity
                        * 100
                    )

            # ----------------------------------------------------
            # DEBT / EQUITY
            # ----------------------------------------------------

            debt_equity = None

            if (
                pd.notna(liabilities)
                and pd.notna(equity)
                and equity != 0
            ):

                debt_equity = (
                    liabilities / equity
                )

            # ----------------------------------------------------
            # VALUATION
            #
            # Chỉ sử dụng current market data.
            # Không đưa P/E và P/B vào historical backtest.
            # ----------------------------------------------------

            pe = self._calculate_pe(
                current_price,
                eps,
            )

            bvps = self._calculate_bvps(
                equity,
                shares_outstanding,
            )

            pb = self._calculate_pb(
                current_price,
                bvps,
            )

            # ----------------------------------------------------
            # RECORD
            # ----------------------------------------------------

            records.append(
                {
                    "symbol": symbol,
                    "report_period": str(period),

                    # ------------------------------
                    # FUNDAMENTALS
                    # ------------------------------

                    "revenue": revenue,
                    "revenue_item_id": revenue_item_id,
                    "revenue_growth": revenue_growth,

                    "net_income": net_income,
                    "net_income_item_id": net_income_item_id,
                    "net_income_growth": net_income_growth,

                    "eps": eps,

                    "roe": roe,

                    "debt_equity": debt_equity,

                    # ------------------------------
                    # VALUATION
                    # ------------------------------

                    "current_price": current_price,
                    "market_cap": market_cap,
                    "shares_outstanding": shares_outstanding,
                    "bvps": bvps,
                    "pe": pe,
                    "pb": pb,

                    # ------------------------------
                    # SOURCE
                    # ------------------------------

                    "source": "VNStock-VCI",
                }
            )

            previous_revenue = revenue
            previous_net_income = net_income
            previous_equity = equity

        result = pd.DataFrame(records)

        if not result.empty:

            result = (
                result
                .sort_values(
                    "report_period",
                    ascending=False,
                )
                .reset_index(drop=True)
            )

        return result