"""Download Foursquare places within a radius of the configured Da Nang sites."""

from __future__ import annotations

import argparse
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Must be set before PyArrow/PyIceberg initialize the AWS SDK.
os.environ.setdefault("AWS_RESPONSE_CHECKSUM_VALIDATION", "WHEN_REQUIRED")

import numpy as np
import pandas as pd
from pyiceberg.expressions import (
    And,
    EqualTo,
    GreaterThanOrEqual,
    IsNull,
    LessThanOrEqual,
    Or,
)

from fetch_danang_places import (
    OUTPUT_COLUMNS,
    TABLE_NAME,
    create_catalog,
    read_token,
    save_places,
)


EARTH_RADIUS_METERS = 6_371_008.8
DEFAULT_RADIUS_METERS = 1_000.0
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "foursquare"


@dataclass(frozen=True)
class SearchCenter:
    name: str
    slug: str
    latitude: float
    longitude: float
    address: str


SEARCH_CENTERS = (
    SearchCenter(
        name="ANFADA Hotel Danang",
        slug="anfada_hotel_danang",
        latitude=16.055124,
        longitude=108.241859,
        address="171 Nguy\u1ec5n V\u0103n Tho\u1ea1i, An H\u1ea3i, \u0110\u00e0 N\u1eb5ng",
    ),
    SearchCenter(
        name="C\u00f4ng Ty TNHH Techzen",
        slug="techzen",
        latitude=16.0772091,
        longitude=108.2195612,
        address="3F, 06 Tr\u1ea7n Ph\u00fa, H\u1ea3i Ch\u00e2u, \u0110\u00e0 N\u1eb5ng",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download places near ANFADA Hotel Danang and Techzen."
    )
    parser.add_argument(
        "--radius-meters",
        type=float,
        default=DEFAULT_RADIUS_METERS,
        help="Search radius around each site (default: 1000)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for the combined and per-site CSV files",
    )
    parser.add_argument(
        "--include-closed",
        action="store_true",
        help="Include places whose date_closed field is set.",
    )
    args = parser.parse_args()
    if args.radius_meters <= 0:
        parser.error("--radius-meters must be greater than zero")
    return args


def bounding_box_filter(center: SearchCenter, radius_meters: float):
    """Return a conservative bounding box around a search center."""
    latitude_delta = math.degrees(radius_meters / EARTH_RADIUS_METERS)
    longitude_delta = math.degrees(
        radius_meters
        / (EARTH_RADIUS_METERS * math.cos(math.radians(center.latitude)))
    )
    return And(
        And(
            GreaterThanOrEqual("latitude", center.latitude - latitude_delta),
            LessThanOrEqual("latitude", center.latitude + latitude_delta),
        ),
        And(
            GreaterThanOrEqual("longitude", center.longitude - longitude_delta),
            LessThanOrEqual("longitude", center.longitude + longitude_delta),
        ),
    )


def nearby_filter(radius_meters: float, *, include_closed: bool):
    boxes = [bounding_box_filter(center, radius_meters) for center in SEARCH_CENTERS]
    any_box = boxes[0]
    for box in boxes[1:]:
        any_box = Or(any_box, box)

    expression = And(EqualTo("country", "VN"), any_box)
    return expression if include_closed else And(expression, IsNull("date_closed"))


def fetch_candidates(catalog, radius_meters: float, *, include_closed: bool) -> pd.DataFrame:
    table = catalog.load_table(TABLE_NAME)
    return table.scan(
        row_filter=nearby_filter(radius_meters, include_closed=include_closed),
        selected_fields=OUTPUT_COLUMNS,
    ).to_pandas()


def distances_from(center: SearchCenter, places: pd.DataFrame) -> np.ndarray:
    """Calculate great-circle distances in meters with the Haversine formula."""
    latitudes = np.radians(pd.to_numeric(places["latitude"], errors="coerce"))
    longitudes = np.radians(pd.to_numeric(places["longitude"], errors="coerce"))
    center_latitude = math.radians(center.latitude)
    center_longitude = math.radians(center.longitude)

    latitude_delta = latitudes - center_latitude
    longitude_delta = longitudes - center_longitude
    haversine = (
        np.sin(latitude_delta / 2.0) ** 2
        + math.cos(center_latitude)
        * np.cos(latitudes)
        * np.sin(longitude_delta / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_METERS * np.arcsin(
        np.sqrt(np.clip(haversine, 0.0, 1.0))
    )


def places_near(
    center: SearchCenter,
    candidates: pd.DataFrame,
    radius_meters: float,
) -> pd.DataFrame:
    distances = distances_from(center, candidates)
    result = candidates.loc[distances <= radius_meters].copy()
    result.insert(0, "reference_location", center.name)
    result.insert(1, "reference_address", center.address)
    result.insert(2, "distance_meters", distances[distances <= radius_meters].round(1))
    return result.sort_values(["distance_meters", "name"], na_position="last")


def main() -> int:
    args = parse_args()
    token = read_token()
    if not token:
        print(
            "Error: set your Places Portal token in FOURSQUARE_PLACES_TOKEN.",
            file=sys.stderr,
        )
        return 2

    try:
        catalog = create_catalog(token)
        candidates = fetch_candidates(
            catalog,
            args.radius_meters,
            include_closed=args.include_closed,
        )
        output_dir = args.output_dir.expanduser().resolve()
        results = []
        for center in SEARCH_CENTERS:
            nearby = places_near(center, candidates, args.radius_meters)
            output = output_dir / f"{center.slug}_{int(args.radius_meters)}m.csv"
            save_places(nearby, output)
            results.append(nearby)
            print(f"{center.name}: {len(nearby)} places -> {output}")

        combined = pd.concat(results, ignore_index=True)
        combined = combined.sort_values(
            ["reference_location", "distance_meters", "name"],
            na_position="last",
        )
        combined_output = output_dir / f"danang_nearby_{int(args.radius_meters)}m.csv"
        save_places(combined, combined_output)
        print(f"Combined: {len(combined)} rows -> {combined_output}")
    except Exception as exc:
        print(f"Failed to fetch nearby Foursquare places: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
