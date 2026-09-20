import json

import pandas as pd


class DNSENormalizer:
    @staticmethod
    def ohlcv_to_dataframe(response_text, symbol):
        data = json.loads(response_text)

        required_fields = ["t", "o", "h", "l", "c", "v"]

        for field in required_fields:
            if field not in data:
                raise ValueError(
                    f"Missing field '{field}' in DNSE response"
                )

        lengths = {
            len(data["t"]),
            len(data["o"]),
            len(data["h"]),
            len(data["l"]),
            len(data["c"]),
            len(data["v"]),
        }

        if len(lengths) != 1:
            raise ValueError("OHLCV arrays have different lengths")

        df = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    data["t"],
                    unit="s",
                    utc=True,
                ),
                "symbol": symbol.upper(),
                "open": data["o"],
                "high": data["h"],
                "low": data["l"],
                "close": data["c"],
                "volume": data["v"],
                "source": "DNSE",
            }
        )
    @staticmethod
    def index_to_dataframe(response_text, index_symbol):
        data = json.loads(response_text)

        required_fields = ["t", "o", "h", "l", "c", "v"]

        for field in required_fields:
            if field not in data:
                raise ValueError(
                    f"Missing field '{field}' in DNSE index response"
                )

        lengths = {
            len(data["t"]),
            len(data["o"]),
            len(data["h"]),
            len(data["l"]),
            len(data["c"]),
            len(data["v"]),
        }

        if len(lengths) != 1:
            raise ValueError(
                "Index OHLCV arrays have different lengths"
            )

        df = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    data["t"],
                    unit="s",
                    utc=True
                ),
                "symbol": index_symbol.upper(),
                "open": data["o"],
                "high": data["h"],
                "low": data["l"],
                "close": data["c"],
                "volume": data["v"],
                "source": "DNSE",
            }
        )
        return df