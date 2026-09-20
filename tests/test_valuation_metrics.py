from data.vnstock_client import VnstockFundamentalClient


def main():
    client = VnstockFundamentalClient()

    # ------------------------------------------------------------
    # Test P/E
    # ------------------------------------------------------------

    pe = client._calculate_pe(
        current_price=17900,
        eps=2714,
    )

    assert pe is not None
    assert abs(pe - (17900 / 2714)) < 1e-9

    print("PASS: P/E calculation")

    # ------------------------------------------------------------
    # Test BVPS
    # ------------------------------------------------------------

    bvps = client._calculate_bvps(
        equity=16_796_000_000_000,
        shares_outstanding=1_606_783_948,
    )

    assert bvps is not None
    assert bvps > 0

    print("PASS: BVPS calculation")

    # ------------------------------------------------------------
    # Test P/B
    # ------------------------------------------------------------

    pb = client._calculate_pb(
        current_price=17900,
        bvps=bvps,
    )

    assert pb is not None
    assert abs(pb - (17900 / bvps)) < 1e-9

    print("PASS: P/B calculation")

    # ------------------------------------------------------------
    # Test invalid EPS
    # ------------------------------------------------------------

    assert client._calculate_pe(
        current_price=17900,
        eps=0,
    ) is None

    assert client._calculate_pe(
        current_price=17900,
        eps=-100,
    ) is None

    print("PASS: invalid P/E cases")

    # ------------------------------------------------------------
    # Test invalid BVPS
    # ------------------------------------------------------------

    assert client._calculate_pb(
        current_price=17900,
        bvps=0,
    ) is None

    assert client._calculate_pb(
        current_price=17900,
        bvps=-100,
    ) is None

    print("PASS: invalid P/B cases")

    print("\nALL VALUATION TESTS PASSED")


if __name__ == "__main__":
    main()