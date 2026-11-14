import pandas as pd
import pytest

import pipeline

# same header as in sales.csv, including the space after "Quantity"
COLUMNS = ["Order ID", "Region", "Product", "Quantity ", "Unit Price", "Discount", "Order Date"]


def make_raw(*rows):
    return pd.DataFrame(list(rows), columns=COLUMNS)


def line(order_id="SO-1", region="East", product="Mouse", quantity="2",
         price="10.00", discount="", date="2026-01-02"):
    return [order_id, region, product, quantity, price, discount, date]


def clean(*rows):
    return pipeline.clean_sales(make_raw(*rows))


def test_column_names():
    df, stats = clean(line())
    assert list(df.columns) == [
        "order_id", "region", "product", "quantity", "unit_price", "discount", "order_date",
    ]
    assert stats["column_names_with_stray_whitespace"] == 1


def test_region_spaces_and_case():
    df, stats = clean(
        line("SO-1", region=" south"),
        line("SO-2", region="EAST"),
        line("SO-3", region="West "),
        line("SO-4", region="North"),
    )
    assert list(df["region"]) == ["South", "East", "West", "North"]
    assert stats["region_any_fix"] == 3
    assert stats["region_stray_whitespace"] == 2
    assert stats["region_wrong_case"] == 2


def test_quantity_with_space_is_a_thousands_separator():
    df, stats = clean(line(quantity="1 762"))
    assert df["quantity"].iloc[0] == 1762
    assert stats["quantity_thousands_space"] == 1


def test_negative_quantity_is_kept():
    df, stats = clean(line(quantity="-3"))
    assert df["quantity"].iloc[0] == -3
    assert stats["quantity_negative_kept"] == 1


def test_quantity_is_an_integer():
    df, _ = clean(line(quantity="5"))
    assert str(df["quantity"].dtype) == "int64"


def test_decimal_comma_in_price():
    df, stats = clean(line(price="59,00"))
    assert df["unit_price"].iloc[0] == 59.0
    assert stats["unit_price_decimal_comma"] == 1


def test_missing_price_is_taken_from_the_same_product():
    df, stats = clean(
        line("SO-1", product="Mouse", price="29,50"),
        line("SO-2", product="Mouse", price=""),
        line("SO-3", product="Desk lamp", price="39.90"),
    )
    assert list(df["unit_price"]) == [29.5, 29.5, 39.9]
    assert stats["unit_price_missing_filled"] == 1


def test_missing_price_is_not_guessed_when_product_has_two_prices():
    df, stats = clean(
        line("SO-1", product="Mouse", price="10.00"),
        line("SO-2", product="Mouse", price="12.00"),
        line("SO-3", product="Mouse", price=""),
    )
    assert list(df["order_id"]) == ["SO-1", "SO-2"]
    assert stats["rows_dropped_unfixable"] == 1


def test_missing_price_for_unknown_product_drops_the_row():
    df, stats = clean(line("SO-1", product="Mouse", price=""), line("SO-2", product="Desk lamp"))
    assert list(df["order_id"]) == ["SO-2"]
    assert stats["rows_dropped_unfixable"] == 1


def test_empty_discount_is_zero():
    df, stats = clean(line("SO-1", discount=""), line("SO-2", discount="5.50"))
    assert list(df["discount"]) == [0.0, 5.5]
    assert stats["discount_empty_set_to_zero"] == 1


def test_unreadable_discount_drops_the_row():
    df, stats = clean(line("SO-1", discount="abc"), line("SO-2"))
    assert list(df["order_id"]) == ["SO-2"]
    assert stats["rows_dropped_unfixable"] == 1


def test_repeated_header_and_total_rows_are_removed():
    df, stats = clean(
        line("SO-1"),
        COLUMNS[:],
        line("SO-2"),
        ["TOTAL", "", "", "37150", "", "65924.67", ""],
    )
    assert list(df["order_id"]) == ["SO-1", "SO-2"]
    assert stats["repeated_header_rows"] == 1
    assert stats["total_footer_rows"] == 1


def test_exact_duplicate_is_removed_and_first_one_stays():
    df, stats = clean(line("SO-1"), line("SO-1"), line("SO-2"))
    assert list(df["order_id"]) == ["SO-1", "SO-2"]
    assert stats["duplicate_rows_dropped"] == 1


def test_same_order_id_with_different_data_is_not_a_duplicate():
    df, stats = clean(line("SO-1", quantity="2"), line("SO-1", quantity="3"))
    assert len(df) == 2
    assert stats["duplicate_rows_dropped"] == 0
    assert stats["order_id_conflicts_left"] == 1


def test_duplicates_are_found_after_cleaning():
    df, stats = clean(line("SO-1", region="East"), line("SO-1", region=" east "))
    assert len(df) == 1
    assert stats["duplicate_rows_dropped"] == 1


def test_bad_date_does_not_drop_the_row():
    df, stats = clean(line("SO-1", date="not a date"))
    assert len(df) == 1
    assert pd.isna(df["order_date"].iloc[0])
    assert stats["order_date_invalid"] == 1


def test_raw_data_is_not_modified():
    raw = make_raw(line(region=" south", quantity="1 762", price="59,00"))
    before = raw.copy()
    pipeline.clean_sales(raw)
    pd.testing.assert_frame_equal(raw, before)


def test_revenue_by_region_uses_discount_as_an_amount():
    df, _ = clean(
        line("SO-1", region="East", quantity="2", price="10.00", discount="5"),
        line("SO-2", region="East", quantity="1", price="10.00"),
        line("SO-3", region="West", quantity="3", price="20.00", discount="10"),
    )
    totals = pipeline.revenue_by_region(df)
    assert list(totals["region"]) == ["East", "West"]
    assert list(totals["revenue"]) == [25.0, 50.0]


def test_returns_lower_the_revenue():
    df, _ = clean(
        line("SO-1", region="East", quantity="4", price="10.00"),
        line("SO-2", region="East", quantity="-1", price="10.00"),
    )
    totals = pipeline.revenue_by_region(df)
    assert list(totals["revenue"]) == [30.0]


# tests on the real file

@pytest.fixture(scope="module")
def real_result():
    raw = pd.read_csv(pipeline.INPUT_PATH, dtype=str, keep_default_na=False)
    df, stats = pipeline.clean_sales(raw)
    return df, stats, pipeline.revenue_by_region(df)


def test_real_file_counts(real_result):
    _, stats, _ = real_result
    assert stats["rows_in_file"] == 1507
    assert stats["rows_out"] == 1500
    assert stats["repeated_header_rows"] == 1
    assert stats["total_footer_rows"] == 1
    assert stats["region_any_fix"] == 15
    assert stats["quantity_thousands_space"] == 4
    assert stats["quantity_negative_kept"] == 6
    assert stats["unit_price_decimal_comma"] == 7
    assert stats["unit_price_missing_filled"] == 4
    assert stats["discount_empty_set_to_zero"] == 963
    assert stats["duplicate_rows_dropped"] == 5
    assert stats["rows_dropped_unfixable"] == 0
    assert stats["order_id_conflicts_left"] == 0


def test_real_file_is_clean(real_result):
    df, _, _ = real_result
    assert sorted(df["region"].unique()) == ["Central", "East", "North", "South", "West"]
    assert not df[["quantity", "unit_price", "discount", "order_date"]].isna().any().any()
    assert df["order_id"].is_unique


def test_real_file_totals(real_result):
    _, _, totals = real_result
    expected = {
        "Central": 515824.67,
        "East": 442219.91,
        "North": 665897.52,
        "South": 504036.04,
        "West": 442268.89,
    }
    assert dict(zip(totals["region"], totals["revenue"])) == pytest.approx(expected)


def test_main_writes_the_csv(tmp_path, monkeypatch):
    out = tmp_path / "out.csv"
    monkeypatch.setattr(pipeline, "OUTPUT_PATH", out)
    pipeline.main()
    lines = out.read_text().splitlines()
    assert lines[0] == "region,revenue"
    assert lines[1] == "Central,515824.67"
    assert len(lines) == 6


def test_committed_csv_is_up_to_date(real_result):
    _, _, totals = real_result
    committed = pd.read_csv(pipeline.BASE_DIR / "revenue_by_region.csv")
    assert list(committed["region"]) == list(totals["region"])
    assert list(committed["revenue"]) == pytest.approx(list(totals["revenue"]))
