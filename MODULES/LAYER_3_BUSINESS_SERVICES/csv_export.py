"""CSV files for the administrator (opened by Excel, Google Sheets or any spreadsheet).

Two protections: every cell that could be read as a formula (it starts with = + - @ or a tab / return) gets a leading apostrophe,
so a candidate who typed a formula as their name or domain cannot run it in the admin's spreadsheet; and the file starts with a
byte-order mark so Excel shows names with accents and non-Latin letters correctly.
"""
import csv
import io
from datetime import datetime

BOM = "﻿"
RISKY_START = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value):
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    if text.startswith(RISKY_START):
        return "'" + text
    return text


def build_csv(header, rows):
    """Returns the file content (text, with the byte-order mark) for a header line and a list of rows."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow([safe_cell(h) for h in header])
    for row in rows:
        writer.writerow([safe_cell(c) for c in row])
    return BOM + out.getvalue()


def file_name(kind, filter_name=None, today=None):
    today = today or datetime.utcnow()
    part = f"-{filter_name}" if filter_name and filter_name != "all" else ""
    return f"ai-interview-{kind}{part}-{today:%Y-%m-%d}.csv"
