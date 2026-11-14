# Virtual columns in a pandas DataFrame

A function that adds a calculated column to a pandas DataFrame
(`add_virtual_column`), and a pipeline that uses it to get revenue per region
from a messy sales export (`sales.csv`).

## Files

- `solution.py`: the `add_virtual_column` function (part 1)
- `pipeline.py`: cleans `sales.csv` and writes `revenue_by_region.csv` (part 2)
- `revenue_by_region.csv`: output of the pipeline
- `sales.csv`: the raw export, not modified
- `test_virtual_column.py`: the sample tests that came with the task, not modified
- `test_solution.py`: my tests for part 1
- `test_pipeline.py`: my tests for part 2
- `README.md`: this file

## Setup

I used Python 3.13. The only dependencies are pandas and pytest.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux

python -m pip install pandas pytest
```

The virtual environment is optional.

## Running

Pipeline (run it from the project folder, `solution.py` and `sales.csv` have to be next to it):

```bash
python pipeline.py
```

It prints a short report of what it fixed and writes `revenue_by_region.csv`.

Tests:

```bash
python -m pytest
```
At the moment this ends with `74 passed`.

## Part 1: `add_virtual_column(df, role, new_column)`

Returns a copy of `df` with one extra column called `new_column`. The values
come from the expression in `role`, which can use column names and `+`, `-`,
`*`. The original DataFrame is not changed.

```python
>>> add_virtual_column(fruits_sales, "quantity * price", "total")
     name  quantity  price  total
0  banana        10     10    100
1   apple         3      1      3
```

It returns an empty DataFrame (`pandas.DataFrame([])`) instead of raising an
error when something is wrong: `new_column` is not made only of letters and
underscores, the expression is empty or broken (`"quantity *"`, unbalanced
parentheses), it uses anything other than column names, `+`, `-`, `*` and
parentheses (for example `/`), a column in it has a name with anything but
letters and underscores, a column is missing from `df` or is not numeric, or
`df` is not a DataFrame. The expression is checked before it is calculated,
so nothing from `role` is ever executed as code.

Where the task was not clear I decided this:

- The example in the task shows a column called `price_total` and the value
  `32` for apple, but the call uses `"total"` and 3 * 1 is 3. I took it as a
  typo. The column gets exactly the name from `new_column`.
- Parentheses are allowed, `(a + b) * c` works, and `*` goes before `+` and `-`.
- Numbers inside the expression are not allowed (`"quantity * 2"` gives an
  empty DataFrame), and neither is a minus in front of a column (`"-quantity"`).
  The task only talks about columns combined with `+`, `-`, `*`.
- Only the columns used in `role` are checked for the "letters and underscores"
  rule. Other columns in `df` can be named anything and are left alone.
- Spaces in `role` do not matter: `"a+b"` and `"  a + b "` are the same.
- If `new_column` already exists in `df`, it is overwritten in the returned copy.
- A text column in the expression gives an empty DataFrame. Otherwise `+` and
  `*` would glue or repeat strings instead of failing.

## Part 2: `pipeline.py`

The pipeline reads `sales.csv` with everything as text (so nothing gets
converted behind my back), cleans it in `clean_sales`, and then adds a
`revenue` column with `add_virtual_column(df, "quantity * unit_price - discount", "revenue")`.
Revenue per region is the sum of that column, rounded to 2 decimals, and the
result goes to `revenue_by_region.csv` sorted by region. The discount in the
file is an amount of money for the whole line, so it is subtracted as is.

Before writing any cleaning code I read the file with everything as text and
looked at each column on its own: empty values, stray spaces, how many
different values there are, and what shape the values have. I looked at the
distributions (how often each region and product shows up, the range of the
quantities, discounts and dates, which price each product has) and at the
outliers. That is how I found the four quantities far above the rest, which
are all between 1 and 40, and that every discount is 5% or 10% of its line.
The table below comes from that.

The file has 1507 data rows. After cleaning there are 1500, and the 7 rows
that are gone are listed below.

### What was wrong with the file

| # | Problem | Rows | What I did |
|---|---------|------|------------|
| 1 | The column name `Quantity ` has a space at the end | 1 column | Stripped, and all names changed to lowercase with underscores (`unit_price`), because `add_virtual_column` does not accept spaces in names |
| 2 | The header is repeated in the middle of the data (line 753) | 1 | Removed, it is not an order |
| 3 | A `TOTAL` line at the end of the file (line 1508) | 1 | Removed, it is not an order |
| 4 | Region with extra spaces or the wrong case (`" South"`, `EAST`, `west `) | 15 (8 with spaces, 10 with wrong case, some have both) | Spaces stripped, case fixed. After that there are exactly five regions: Central, East, North, South, West |
| 5 | Quantity written with a space inside (`1 762`) | 4 | Read as 1762, see decisions below |
| 6 | Negative quantity | 6 | Left as they are, see decisions below |
| 7 | Unit price with a decimal comma (`59,00`) | 7 | Comma changed to a dot |
| 8 | Unit price missing | 4 | Filled in with the price of that product from the other rows |
| 9 | Discount empty | 963 | Set to 0 |
| 10 | The same line twice (same `Order ID` and every other column the same) | 5 | The first one is kept, the copy is removed |

I also checked the dates (all valid, from 2026-01-02 to 2026-09-29), the
format of the discounts, product names and the region names after cleaning.
Nothing was wrong there. No row was dropped because it could not be fixed, and
after removing the duplicates no `Order ID` appears twice.


> **Note:** When I write "the `1 762` lines" I mean all four lines whose
quantity has a space inside, not only the one that is exactly `1 762`. They are
SO-10251 (`1 762`), SO-10734 (`1 745`), SO-11088 (`1 371`) and SO-11312
(`1 427`).

### Decisions

- **`1 762` is 1762, not 762.** Every other quantity in the file is between 1
  and 40, so these four stand out, but the `TOTAL` line at the end of the file
  agrees with the 1762 reading: its quantity (37150) and discount (65924.67)
  are exactly the sums of the raw rows when `1 762` is read as 1762. These four
  lines are about 12.6% of the total revenue, so this decision matters. They
  have no discount.
- **Negative quantities are kept.** I assumed they are returns, so they lower
  the revenue (together they are -913.00). Nothing in the file says whether
  they are returns or mistakes, so this is a guess.
- **Duplicates.** A line is only a duplicate if everything in it is the same,
  `Order ID` included. All five pairs are right next to each other in the
  file. If two lines had the same `Order ID` but different data the pipeline
  would keep both and count them in the report (there are none here).
- **Missing prices.** Every product has exactly one price in the file, so a
  missing one is taken from the other rows of that product. In one of the four
  cases the discount lets me check it: 164.65 is 5% of 37 * 89.00. If a product
  had more than one price the pipeline would not guess.
- **Empty discount means no discount.** Where a discount is filled in it is
  always 5% or 10% of the line value, which is consistent with it being an
  amount for the whole line.
- **Dates are not used.** Revenue does not depend on them, so a bad date would
  not remove a row (there are none).
- **Rounding.** Totals are rounded to 2 decimals, and the CSV always has 2.
- 
### How much the decisions change the result

To see which decisions matter I ran the pipeline again with the other choice
and compared the total revenue (2,570,247.03 with the choices above):

| If I had... | Total revenue | Change |
|---|---|---|
| dropped the 6 negative lines | 2,571,160.03 | +913.00 (+0.04%) |
| turned the negative quantities into positive ones | 2,572,073.03 | +1,826.00 (+0.07%) |
| kept the 5 duplicate lines | 2,575,543.43 | +5,296.40 (+0.21%) |
| read `1 762` as 762 | 2,350,247.03 | -220,000.00 (-8.56%) |
| dropped the 4 lines with `1 762` | 2,245,898.03 | -324,349.00 (-12.62%) |

The negative quantities and the duplicates hardly matter. The `1 762` lines are
the one decision that changes the picture. They are in North (two lines),
Central and South, and without them South would be the top region instead of
North. If someone can say what these four quantities should be, that is the
one thing worth checking.
### Result

| region | revenue |
|--------|---------|
| Central | 515824.67 |
| East | 442219.91 |
| North | 665897.52 |
| South | 504036.04 |
| West | 442268.89 |

## Part 3: tests

`python -m pytest` runs all of these with one command:

- `test_virtual_column.py`: the sample tests from the task.
- `test_solution.py`: my tests for `add_virtual_column`. Normal expressions,
  the order of operations and parentheses, the original DataFrame staying
  unchanged, and a long list of bad input that has to give an empty DataFrame
  (broken or unsupported expressions, bad column names, text columns, wrong
  types).
- `test_pipeline.py`: my tests for the pipeline. `clean_sales` has a small test
  for every problem in the table above, using tiny hand-made tables. Then the
  revenue calculation (discount as an amount, returns lowering the revenue)
  and a few checks on the real `sales.csv`: the row counts, the totals from
  this README, and that the `revenue_by_region.csv` in the repository is the
  same as what the pipeline gives now. The test that runs `main()` writes to a
  temporary folder, so it does not touch the real output file.

The tests on the real file have the numbers from this README written into
them. If the cleaning rules change, those numbers and the README have to be
updated together.
