"""Sanity-checks Database/Database.xlsx before it gets pushed.

Run standalone: python validate_xlsx.py
Exit code 0 = safe to push. Exit code 1 = problems found, do not push.
"""
import sys
from pathlib import Path

import pandas as pd

XLSX_PATH = Path(__file__).resolve().parent / "Database" / "Database.xlsx"
SHEET_NAME = "Database"

REQUIRED_COLS = ["Month", "Year", "NUMBER", "CLASS", "REGION", "COUNTRY"]
KNOWN_CLASSES = {
    "1. Tiny", "2.1 Small-1", "2.2 Small-2", "2. Small", "3. Large", "4. Mature",
    "5. Ripe", "6. Insect", "7. Forced", "8. Damaged", "9. Black", "TOTAL",
}
ATOMIC_CLASSES = [
    "1. Tiny", "2.1 Small-1", "2.2 Small-2", "3. Large", "4. Mature",
    "5. Ripe", "6. Insect", "7. Forced", "8. Damaged", "9. Black",
]
KNOWN_COUNTRIES = {"GH", "IVC"}
LTA_YEAR = 1950  # sentinel: Year=1950 means "this row is the Long-Term Average for that Month"
YEAR_MIN, YEAR_MAX = LTA_YEAR, 2035

TOTAL_TOLERANCE_ABS = 0.5  # rounding slack (K bags-style units, small counts)


def main():
    errors = []
    warnings = []

    if not XLSX_PATH.exists():
        print(f"FAIL: {XLSX_PATH} does not exist.")
        return 1

    try:
        df = pd.read_excel(XLSX_PATH, sheet_name=SHEET_NAME)
    except Exception as e:
        print(f"FAIL: could not parse '{SHEET_NAME}' sheet - {e}")
        return 1

    for col in REQUIRED_COLS:
        if col not in df.columns:
            errors.append(f"Missing required column '{col}'.")
    if errors:
        _report(errors, warnings)
        return 1

    # Year / Month sanity
    bad_year = df[~df["Year"].apply(lambda v: pd.notna(v) and float(v).is_integer()
                                     and YEAR_MIN <= int(v) <= YEAR_MAX)]
    for _, r in bad_year.iterrows():
        errors.append(f"Row with bad Year value: {r['Year']!r} "
                       f"(Class={r.get('CLASS')}, Country={r.get('COUNTRY')}).")

    bad_month = df[~df["Month"].apply(lambda v: pd.notna(v) and float(v).is_integer()
                                       and 1 <= int(v) <= 12)]
    for _, r in bad_month.iterrows():
        errors.append(f"Row with bad Month value: {r['Month']!r} "
                       f"(Year={r.get('Year')}, Class={r.get('CLASS')}, Country={r.get('COUNTRY')}).")

    # Vocabulary checks
    bad_classes = set(df["CLASS"].dropna().unique()) - KNOWN_CLASSES
    if bad_classes:
        errors.append(f"Unexpected CLASS value(s): {sorted(bad_classes)} — typo? "
                       f"Expected only {sorted(KNOWN_CLASSES)}.")

    bad_countries = set(df["COUNTRY"].dropna().unique()) - KNOWN_COUNTRIES
    if bad_countries:
        errors.append(f"Unexpected COUNTRY value(s): {sorted(bad_countries)} — "
                       f"typo? Expected only {sorted(KNOWN_COUNTRIES)}.")

    unknown_region = set(df["REGION"].dropna().unique()) - {"ALL"}
    if unknown_region:
        warnings.append(f"REGION value(s) other than 'ALL' found (new region breakdown? "
                         f"fine if intentional, typo otherwise): {sorted(unknown_region)}")

    # Duplicate (Month, Year, CLASS, REGION, COUNTRY) rows
    dupes = df[df.duplicated(subset=["Month", "Year", "CLASS", "REGION", "COUNTRY"], keep=False)]
    if not dupes.empty:
        for _, row in dupes.iterrows():
            errors.append(f"Duplicate row: Month={row['Month']}, Year={row['Year']}, "
                           f"CLASS='{row['CLASS']}', Country='{row['COUNTRY']}'.")

    # Numeric parseability of NUMBER
    non_blank = df["NUMBER"].dropna()
    non_numeric = non_blank[pd.to_numeric(non_blank, errors="coerce").isna()]
    if not non_numeric.empty:
        bad_rows = df.loc[non_numeric.index, ["Month", "Year", "CLASS", "COUNTRY"]]
        for _, r in bad_rows.iterrows():
            errors.append(f"Non-numeric NUMBER value for Month={r['Month']}, Year={r['Year']}, "
                           f"CLASS='{r['CLASS']}', Country='{r['COUNTRY']}'.")

    if errors:
        # Reconciliation checks below assume clean rows — skip until fixed.
        _report(errors, warnings)
        return 1

    # Reconciliation checks below only apply to real survey data. The Year=1950
    # LTA rows are a static, externally pre-computed benchmark — each component
    # class was averaged independently, so small rounding drift between '2. Small'
    # and its parts (or TOTAL and the atomic classes) is expected there, not an error.
    real_df = df[df["Year"] != LTA_YEAR]

    # Reconciliation 1: '2. Small' should equal '2.1 Small-1' + '2.2 Small-2' exactly
    # (verified as an exact identity in the historical data).
    for (month, year, region, country), group in real_df.groupby(["Month", "Year", "REGION", "COUNTRY"]):
        by_class = group.set_index("CLASS")["NUMBER"]
        if "2. Small" in by_class.index:
            small1 = by_class.get("2.1 Small-1", 0.0)
            small2 = by_class.get("2.2 Small-2", 0.0)
            small_agg = by_class["2. Small"]
            if pd.notna(small_agg) and abs(small_agg - (small1 + small2)) > TOTAL_TOLERANCE_ABS:
                errors.append(
                    f"'2. Small' mismatch: Month={month}, Year={year}, Country='{country}' — "
                    f"'2. Small' = {small_agg:,.2f} but Small-1 + Small-2 = {small1 + small2:,.2f}."
                )

    # Reconciliation 2: TOTAL should be >= the sum of the 10 atomic classes present
    # that period (some early periods only report TOTAL with no class breakdown —
    # that's expected, not an error, so this only fires when atomic rows exist).
    for (month, year, region, country), group in real_df.groupby(["Month", "Year", "REGION", "COUNTRY"]):
        by_class = group.set_index("CLASS")["NUMBER"]
        if "TOTAL" not in by_class.index:
            continue
        present_atomic = [c for c in ATOMIC_CLASSES if c in by_class.index]
        if not present_atomic:
            continue  # this period only has a TOTAL row, no breakdown yet — fine
        atomic_sum = by_class[present_atomic].sum(skipna=True)
        total_val = by_class["TOTAL"]
        if pd.notna(total_val) and atomic_sum > total_val + TOTAL_TOLERANCE_ABS:
            errors.append(
                f"TOTAL too small: Month={month}, Year={year}, Country='{country}' — "
                f"atomic classes sum to {atomic_sum:,.2f} but TOTAL = {total_val:,.2f}."
            )

    # Flag a Country whose most recent (Year, Month) has zero data at all.
    for country, group in df[df["Year"] != LTA_YEAR].groupby("COUNTRY"):
        latest = group[["Year", "Month"]].drop_duplicates().sort_values(["Year", "Month"]).iloc[-1]
        latest_rows = group[(group["Year"] == latest["Year"]) & (group["Month"] == latest["Month"])]
        if latest_rows["NUMBER"].notna().sum() == 0:
            warnings.append(f"'{country}' has zero values for its most recent period "
                             f"({int(latest['Year'])}-{int(latest['Month']):02d}) — "
                             f"fine if that month genuinely hasn't been surveyed yet, worth a second look otherwise.")

    return _report(errors, warnings)


def _report(errors, warnings):
    if warnings:
        print("Warnings (won't block the push):")
        for w in warnings:
            print(f"  - {w}")
        print()
    if errors:
        print("FAIL - fix these before pushing:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASS - Database.xlsx looks good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
