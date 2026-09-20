import os

from dotenv import load_dotenv
from dnse import DNSEClient


load_dotenv()


class DNSEDataClient:
    def __init__(self):
        self.api_key = os.getenv("DNSE_API_KEY")
        self.api_secret = os.getenv("DNSE_API_SECRET")

        if not self.api_key:
            raise ValueError("Missing DNSE_API_KEY in .env")

        if not self.api_secret:
            raise ValueError("Missing DNSE_API_SECRET in .env")

        self.client = DNSEClient(
            api_key=self.api_key,
            api_secret=self.api_secret,
        )

    def get_historical_ohlcv(
        self,
        symbol,
        start_timestamp,
        end_timestamp,
        resolution="1D",
    ):
        result = self.client.get_ohlc(
            "STOCK",
            {
                "symbol": symbol,
                "resolution": resolution,
                "from": start_timestamp,
                "to": end_timestamp,
            },
        )

        status_code, response_text = result

        if status_code != 200:
            raise RuntimeError(
                f"DNSE API error for stock {symbol}: "
                f"{status_code} - {response_text}"
            )

        return response_text

    def get_historical_index(
        self,
        index_symbol,
        start_timestamp,
        end_timestamp,
        resolution="1D",
    ):
        result = self.client.get_ohlc(
            "INDEX",
            {
                "symbol": index_symbol,
                "resolution": resolution,
                "from": start_timestamp,
                "to": end_timestamp,
            },
        )

        status_code, response_text = result

        if status_code != 200:
            raise RuntimeError(
                f"DNSE API error for index {index_symbol}: "
                f"{status_code} - {response_text}"
            )

        return response_text