import csv
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from stores.models import PaymentMethod, Store, StorePaymentMethod, normalize

# Matches Store.latitude/longitude (decimal_places=6). Foursquare's raw
# coordinates carry far more precision, so rows for the same place round to
# the same value here that they will once saved -- otherwise the duplicate
# check below misses matches that the database's unique constraint still
# catches, and the second insert fails instead of being skipped.
COORDINATE_PRECISION = Decimal("0.000001")


def coordinate(value, minimum, maximum):
    try:
        result = Decimal(value).quantize(COORDINATE_PRECISION, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError):
        return None
    return result if minimum <= result <= maximum else None


class Command(BaseCommand):
    help = (
        "Import store locations from a Foursquare places CSV "
        "(see backend/scripts/fetch_danang_places.py and fetch_nearby_places.py) into Store. "
        "Payment method statuses are left as 'unknown' since Foursquare has no such data."
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=Path)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and process the file, then roll the transaction back.",
        )

    def handle(self, *args, **options):
        path = options["csv_path"]
        if not path.is_file():
            raise CommandError(f"CSV file does not exist: {path}")

        methods = list(PaymentMethod.objects.filter(is_active=True))
        if not methods:
            raise CommandError("No active payment methods found; seed PaymentMethod first.")

        created = 0
        skipped_duplicate = 0
        skipped_invalid = 0

        with transaction.atomic():
            with path.open("r", encoding="utf-8-sig", newline="") as source:
                reader = csv.DictReader(source)
                required_columns = {"name", "latitude", "longitude"}
                missing_columns = required_columns - set(reader.fieldnames or [])
                if missing_columns:
                    raise CommandError(
                        f"CSV is missing required columns: {', '.join(sorted(missing_columns))}"
                    )

                for row in reader:
                    name = (row.get("name") or "").strip()
                    latitude = coordinate(row.get("latitude"), Decimal("-90"), Decimal("90"))
                    longitude = coordinate(row.get("longitude"), Decimal("-180"), Decimal("180"))
                    if not name or latitude is None or longitude is None:
                        skipped_invalid += 1
                        continue

                    address = (row.get("address") or "").strip()

                    already_exists = Store.objects.filter(
                        normalized_name=normalize(name),
                        normalized_address=normalize(address),
                        latitude=latitude,
                        longitude=longitude,
                    ).exists()
                    if already_exists:
                        skipped_duplicate += 1
                        continue

                    store = Store.objects.create(
                        name=name,
                        address=address,
                        latitude=latitude,
                        longitude=longitude,
                    )
                    StorePaymentMethod.objects.bulk_create(
                        [
                            StorePaymentMethod(store=store, payment_method=method)
                            for method in methods
                        ]
                    )
                    created += 1

            if options["dry_run"]:
                transaction.set_rollback(True)

        mode = "Dry run" if options["dry_run"] else "Import complete"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode}: {created} created, {skipped_duplicate} duplicates skipped, "
                f"{skipped_invalid} invalid rows skipped."
            )
        )
