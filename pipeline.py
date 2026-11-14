from pathlib import Path

import pandas as pd

from solution import add_virtual_column

BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "sales.csv"
OUTPUT_PATH = BASE_DIR / "revenue_by_region.csv"

# discount is an amount taken off the whole line, not a percentage
REVENUE_ROLE = "quantity * unit_price - discount"


def clean_sales(raw):
    stats = {"rows_in_file": len(raw)}
    df = raw.copy()

    # "Quantity " and "Unit Price" -> quantity, unit_price
    # (add_virtual_column doesn't accept spaces in column labels)
    stats["column_names_with_stray_whitespace"] = sum(c != c.strip() for c in raw.columns)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # repeated header row and the TOTAL line at the bottom are not orders
    order_id = df["order_id"].str.strip().str.lower()
    is_header = order_id == "order id"
    is_footer = order_id == "total"
    stats["repeated_header_rows"] = int(is_header.sum())
    stats["total_footer_rows"] = int(is_footer.sum())
    df = df[~(is_header | is_footer)].copy()
    df["order_id"] = df["order_id"].str.strip()

    # region: stray spaces and mixed case
    region_raw = df["region"]
    region_trimmed = region_raw.str.strip()
    region_clean = region_trimmed.str.title()
    stats["region_stray_whitespace"] = int((region_raw != region_trimmed).sum())
    stats["region_wrong_case"] = int((region_trimmed != region_clean).sum())
    stats["region_any_fix"] = int((region_raw != region_clean).sum())
    df["region"] = region_clean
    df["product"] = df["product"].str.strip()

    # quantity: "1 762" means 1762 (the TOTAL line only adds up that way)
    qty_raw = df["quantity"].str.strip()
    qty_text = qty_raw.str.replace(r"\s+", "", regex=True)
    stats["quantity_thousands_space"] = int((qty_raw != qty_text).sum())
    df["quantity"] = pd.to_numeric(qty_text, errors="coerce")
    # negative quantities stay, I treat them as returns
    stats["quantity_negative_kept"] = int((df["quantity"] < 0).sum())

    # unit price: decimal comma
    price_raw = df["unit_price"].str.strip()
    price_text = price_raw.str.replace(",", ".", regex=False)
    stats["unit_price_decimal_comma"] = int((price_raw != price_text).sum())
    df["unit_price"] = pd.to_numeric(price_text, errors="coerce")

    # blank price: take the product's price from the other rows,
    # but only if the product has just one price
    known = df.dropna(subset=["unit_price"]).groupby("product")["unit_price"]
    product_price = known.agg(lambda s: s.iloc[0] if s.nunique() == 1 else float("nan"))
    missing_price = df["unit_price"].isna()
    df.loc[missing_price, "unit_price"] = df.loc[missing_price, "product"].map(product_price)
    stats["unit_price_missing_filled"] = int((missing_price & df["unit_price"].notna()).sum())

    # discount: empty means no discount
    discount_raw = df["discount"].str.strip()
    discount_num = pd.to_numeric(discount_raw.str.replace(",", ".", regex=False), errors="coerce")
    stats["discount_empty_set_to_zero"] = int((discount_raw == "").sum())
    discount_unreadable = discount_num.isna() & (discount_raw != "")
    df["discount"] = discount_num.fillna(0.0)

    # date isn't used for revenue, so a bad date never drops a row
    df["order_date"] = pd.to_datetime(df["order_date"].str.strip(), format="%Y-%m-%d", errors="coerce")
    stats["order_date_invalid"] = int(df["order_date"].isna().sum())

    # rows that still can't be calculated
    unfixable = df["quantity"].isna() | df["unit_price"].isna() | discount_unreadable
    stats["rows_dropped_unfixable"] = int(unfixable.sum())
    df = df[~unfixable].copy()
    df["quantity"] = df["quantity"].astype("int64")

    # same line twice (every column equal), keep the first
    duplicated = df.duplicated(keep="first")
    stats["duplicate_rows_dropped"] = int(duplicated.sum())
    df = df[~duplicated]
    stats["order_id_conflicts_left"] = int(df["order_id"].duplicated().sum())

    df = df.reset_index(drop=True)
    stats["rows_out"] = len(df)
    return df, stats


def revenue_by_region(clean):
    with_revenue = add_virtual_column(clean, REVENUE_ROLE, "revenue")
    if with_revenue.empty:
        raise RuntimeError(f"add_virtual_column rejected the expression: {REVENUE_ROLE!r}")
    totals = with_revenue.groupby("region", as_index=False)["revenue"].sum()
    totals["revenue"] = totals["revenue"].round(2)
    return totals.sort_values("region").reset_index(drop=True)


def main():
    raw = pd.read_csv(INPUT_PATH, dtype=str, keep_default_na=False)
    clean, stats = clean_sales(raw)
    totals = revenue_by_region(clean)
    totals.to_csv(OUTPUT_PATH, index=False, float_format="%.2f")

    print("Cleaning report:")
    for name, value in stats.items():
        print(f"  {name}: {value}")
    print(f"\nWrote {OUTPUT_PATH.name}:")
    print(totals.to_string(index=False))


if __name__ == "__main__":
    main()