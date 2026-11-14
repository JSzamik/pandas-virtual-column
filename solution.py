import re

import pandas as pd
from pandas.api.types import is_numeric_dtype

LABEL = re.compile(r"[A-Za-z_]+")
FLAT = re.compile(r"N(\s*[-+*]\s*N)*")           # N + N * N ...
GROUP = re.compile(r"\(\s*(N(\s*[-+*]\s*N)*)\s*\)")  # (N + N ...)


def _is_valid_role(role: str) -> bool:
    """Valid = column names, + - *, optional balanced parentheses."""
    shape = LABEL.sub("N", role.strip())
    while True:                      # collapse innermost (...) groups to N
        shape, changes = GROUP.subn("N", shape)
        if not changes:
            break
    return bool(FLAT.fullmatch(shape))


def add_virtual_column(df: pd.DataFrame, role: str, new_column: str) -> pd.DataFrame:
    empty = pd.DataFrame([])
    if not isinstance(df, pd.DataFrame):
        return empty
    if not isinstance(role, str) or not isinstance(new_column, str):
        return empty
    if not LABEL.fullmatch(new_column) or not _is_valid_role(role):
        return empty
    used = LABEL.findall(role)
    if not all(c in df.columns and is_numeric_dtype(df[c]) for c in used):
        return empty
    return df.assign(**{new_column: df.eval(role.strip())})
