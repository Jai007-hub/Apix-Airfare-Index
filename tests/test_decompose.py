from pipeline.decompose import decompose_fare


def test_decompose_from_total_only():
    result = decompose_fare(
        origin="DEL", destination="BOM", source_name="indigo", base_fare=None, total_fare=8428.53
    )
    assert result["base_fare"] > 0
    assert result["taxes"] >= 0
    assert result["udf"] == 1030.0  # DEL(550) + BOM(480)
    assert result["convenience_fee"] == 0.0  # direct airline source
    assert round(result["base_fare"] + result["taxes"] + result["udf"] + result["convenience_fee"], 2) == round(
        result["total_fare"], 2
    )


def test_decompose_with_base_and_total():
    result = decompose_fare(
        origin="DEL", destination="BOM", source_name="makemytrip", base_fare=5000, total_fare=6580
    )
    assert result["udf"] == 1030.0
    assert result["convenience_fee"] == 300.0  # makemytrip fee
    assert result["taxes"] == 250.0  # 6580 - 5000 - 1030 - 300
    assert result["total_fare"] == 6580


def test_decompose_from_taxes_and_fees_lump():
    result = decompose_fare(
        origin="BLR", destination="HYD", source_name="yatra", base_fare=3000, total_fare=None,
        taxes_and_fees_lump=750,
    )
    # BLR(400) + HYD(430) UDF = 830, yatra convenience fee = 250
    assert result["udf"] == 830.0
    assert result["convenience_fee"] == 250.0
    assert result["taxes"] == 0.0  # 750 - 830 - 250 would be negative -> clipped to 0
    assert result["total_fare"] == round(3000 + 0.0 + 830.0 + 250.0, 2)


def test_decompose_no_data_returns_all_none():
    result = decompose_fare(origin="DEL", destination="BOM", source_name="indigo", base_fare=None, total_fare=None)
    assert all(v is None for v in result.values())
