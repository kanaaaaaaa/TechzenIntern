"""Download places located in Da Nang from Foursquare OS Places."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Work around AWS SDK for C++ composite-checksum incompatibility. This still
# validates checksums whenever the API operation explicitly requires it.
os.environ.setdefault("AWS_RESPONSE_CHECKSUM_VALIDATION", "WHEN_REQUIRED")

import pandas as pd
from pyiceberg.catalog import load_catalog
from pyiceberg.expressions import (
    And,
    EqualTo,
    GreaterThanOrEqual,
    In,
    IsNull,
    LessThanOrEqual,
    Or,
)


CATALOG_URI = "https://catalog.h3-hub.foursquare.com/iceberg"
TABLE_NAME = "datasets.places_os"
TOKEN_ENV_VAR = "FOURSQUARE_PLACES_TOKEN"
# Include the spellings commonly found in locality/region fields.
DA_NANG_NAMES = frozenset({"Da Nang", "Danang", "\u0110\u00e0 N\u1eb5ng"})
# Broad bounds for the centrally governed municipality of Da Nang. The
# locality/region test below remains authoritative; these bounds help Parquet
# statistics skip unrelated data files and row groups.
DA_NANG_LATITUDE = (15.8, 16.3)
DA_NANG_LONGITUDE = (107.8, 108.6)
OUTPUT_COLUMNS = (
    "fsq_place_id",
    "name",
    "latitude",
    "longitude",
    "address",
    "locality",
    "region",
    "postcode",
    "country",
    "date_created",
    "date_refreshed",
    "date_closed",
    "tel",
    "website",
    "email",
    "instagram",
    "twitter",
    "fsq_category_ids",
    "fsq_category_labels",
    "placemaker_url",
    "unresolved_flags",
)
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "foursquare"
    / "danang_places.csv"
)
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Da Nang records from Foursquare OS Places."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of records to download (default: 10)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output .csv, .json, or .parquet path (default: %(default)s)",
    )
    parser.add_argument(
        "--include-closed",
        action="store_true",
        help="Include places whose date_closed field is set.",
    )
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.output.suffix.lower() not in {".csv", ".json", ".parquet"}:
        parser.error("--output must end with .csv, .json, or .parquet")
    return args


def create_catalog(token: str):
    return load_catalog(
        "default",
        **{
            "warehouse": "places",
            "uri": CATALOG_URI,
            "token": token,
            "header.content-type": "application/vnd.api+json",
            "rest-metrics-reporting-enabled": "false",
        },
    )


def read_token() -> str:
    """Read the token from the process environment, then the ignored .env file."""
    token = os.environ.get(TOKEN_ENV_VAR, "").strip()
    if token or not ENV_FILE.is_file():
        return token

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        key, separator, value = raw_line.partition("=")
        if separator and key.strip() == TOKEN_ENV_VAR:
            return value.strip().strip("\"'")
    return ""


def danang_filter(*, include_closed: bool):
    """Build a server-side filter for Da Nang, Vietnam."""
    coordinates = And(
        And(
            GreaterThanOrEqual("latitude", DA_NANG_LATITUDE[0]),
            LessThanOrEqual("latitude", DA_NANG_LATITUDE[1]),
        ),
        And(
            GreaterThanOrEqual("longitude", DA_NANG_LONGITUDE[0]),
            LessThanOrEqual("longitude", DA_NANG_LONGITUDE[1]),
        ),
    )
    location = And(
        EqualTo("country", "VN"),
        And(
            coordinates,
            Or(
                In("locality", DA_NANG_NAMES),
                In("region", DA_NANG_NAMES),
            ),
        ),
    )
    return location if include_closed else And(location, IsNull("date_closed"))


def fetch_places(catalog, *, limit: int, include_closed: bool) -> pd.DataFrame:
    table = catalog.load_table(TABLE_NAME)
    return table.scan(
        row_filter=danang_filter(include_closed=include_closed),
        selected_fields=OUTPUT_COLUMNS,
        limit=limit,
    ).to_pandas()


def save_places(df: pd.DataFrame, output: Path) -> None:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    suffix = output.suffix.lower()
    if suffix == ".csv":
        # utf-8-sig lets Windows Excel display Vietnamese text correctly.
        df.to_csv(output, index=False, encoding="utf-8-sig")
    elif suffix == ".json":
        df.to_json(
            output,
            orient="records",
            force_ascii=False,
            indent=2,
            date_format="iso",
        )
    else:
        df.to_parquet(output, index=False)


def print_preview(df: pd.DataFrame) -> None:
    preview_columns = [
        column
        for column in (
            "fsq_place_id",
            "name",
            "address",
            "locality",
            "region",
            "country",
            "latitude",
            "longitude",
            "fsq_category_labels",
        )
        if column in df.columns
    ]
    if df.empty:
        print("No matching places were found.")
        return
    with pd.option_context("display.max_colwidth", 60, "display.width", 240):
        print(df.loc[:, preview_columns].to_string(index=False))


def main() -> int:
    args = parse_args()
    token = read_token()
    if not token:
        print(
            f"Error: set your Places Portal token in {TOKEN_ENV_VAR}.",
            file=sys.stderr,
        )
        return 2

    try:
        catalog = create_catalog(token)
        places = fetch_places(
            catalog,
            limit=args.limit,
            include_closed=args.include_closed,
        )
        save_places(places, args.output)
    except Exception as exc:
        print(f"Failed to fetch Foursquare OS Places: {exc}", file=sys.stderr)
        return 1

    print_preview(places)
    print(f"\nSaved {len(places)} records to {args.output.expanduser().resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
