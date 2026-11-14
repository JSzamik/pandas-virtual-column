import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from solution import add_virtual_column


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "name": ["banana", "apple"],
            "quantity": [10, 3],
            "price": [10, 1],
            "discount": [5, 0],
        }
    )


def test_example_from_the_task(df):
    result = add_virtual_column(df, "quantity * price", "total")
    expected = df.copy()
    expected["total"] = [100, 3]
    assert_frame_equal(result, expected)


def test_three_columns(df):
    result = add_virtual_column(df, "quantity * price - discount", "x")
    assert list(result["x"]) == [95, 3]


def test_multiplication_goes_first(df):
    result = add_virtual_column(df, "quantity + price * discount", "x")
    assert list(result["x"]) == [60, 3]


def test_parentheses(df):
    result = add_virtual_column(df, "(quantity + price) * discount", "x")
    assert list(result["x"]) == [100, 0]
    result = add_virtual_column(df, "quantity - (price - discount)", "x")
    assert list(result["x"]) == [5, 2]


@pytest.mark.parametrize("role", ["quantity*price", "  quantity * price  ", "quantity\t*  price"])
def test_spaces_do_not_matter(df, role):
    result = add_virtual_column(df, role, "total")
    assert list(result["total"]) == [100, 3]


def test_float_columns():
    df = pd.DataFrame({"a": [1.5, 2.0], "b": [2, 4]})
    result = add_virtual_column(df, "a * b", "c")
    assert list(result["c"]) == [3.0, 8.0]


def test_original_is_not_changed(df):
    before = df.copy()
    add_virtual_column(df, "quantity * price", "total")
    assert_frame_equal(df, before)


def test_existing_column_is_overwritten_in_the_copy(df):
    result = add_virtual_column(df, "quantity + price", "price")
    assert list(result["price"]) == [20, 4]
    assert list(df["price"]) == [10, 1]


def test_unused_column_with_a_strange_label_is_fine(df):
    df = df.rename(columns={"name": "name 2"})
    result = add_virtual_column(df, "quantity * price", "total")
    assert list(result["total"]) == [100, 3]


@pytest.mark.parametrize(
    "role",
    [
        "quantity *",
        "* quantity",
        "quantity price",
        "quantity quantity",
        "quantity + + price",
        "(quantity + price",
        "quantity + price)",
        "()",
        "",
        "   ",
        "quantity / price",
        "quantity ** price",
        "quantity // price",
        "quantity * 2",
        "-quantity",
        "nope * price",
        "name * price",
        "name + price",
        "quantity & price",
        "__import__('os')",
    ],
)
def test_bad_role_gives_empty_df(df, role):
    assert add_virtual_column(df, role, "x").empty


def test_column_label_with_a_digit_gives_empty_df(df):
    df = df.rename(columns={"price": "price2"})
    assert add_virtual_column(df, "quantity * price2", "x").empty
    assert add_virtual_column(df, "quantity * price", "x").empty


@pytest.mark.parametrize("new_column", ["total1", "my-total", "my total", "", None, 5])
def test_bad_new_column_gives_empty_df(df, new_column):
    assert add_virtual_column(df, "quantity * price", new_column).empty


@pytest.mark.parametrize("role", [None, 5, ["quantity"]])
def test_role_must_be_a_string(df, role):
    assert add_virtual_column(df, role, "x").empty


@pytest.mark.parametrize("bad_df", [None, [1, 2], {"a": [1]}])
def test_df_must_be_a_dataframe(bad_df):
    assert add_virtual_column(bad_df, "a + a", "x").empty
