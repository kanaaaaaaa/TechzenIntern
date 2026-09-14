import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from stores.models import Store, normalize

# Matches Store.latitude/longitude (decimal_places=6); see
# import_foursquare_csv.py for why rows must be rounded before matching.
COORDINATE_PRECISION = Decimal("0.000001")

# Cells with multiple categories are a numpy array repr, e.g. "['A'\n 'B']"
# (no comma between items), so this is *not* valid Python list syntax --
# pull out each quoted segment independently instead. Also matches the
# clean, comma-separated repr that normalize_fsq_categories.py now writes.
_LABEL_RE = re.compile(r"'((?:[^'\\]|\\.)*)'")


def coordinate(value, minimum, maximum):
    try:
        result = Decimal(value).quantize(COORDINATE_PRECISION, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError):
        return None
    return result if minimum <= result <= maximum else None


def first_category(raw):
    labels = _LABEL_RE.findall((raw or "").strip())
    return labels[0] if labels else ""


class Command(BaseCommand):
    help = (
        "Update Store.category for stores already in the database, using the "
        "fsq_category_labels column of a Foursquare CSV normalized by "
        "backend/scripts/normalize_fsq_categories.py. Matches rows to existing "
        "Store records the same way import_foursquare_csv.py does (normalized "
        "name/address + rounded coordinates); rows with no matching store are "
        "reported, not created."
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=Path)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change, then roll the transaction back.",
        )

    def handle(self, *args, **options):
        path = options["csv_path"]
        if not path.is_file():
            raise CommandError(f"CSV file does not exist: {path}")

        import csv

        updated = 0
        unchanged = 0
        not_found = 0
        no_category = 0

        with transaction.atomic():
            with path.open("r", encoding="utf-8-sig", newline="") as source:
                reader = csv.DictReader(source)
                required_columns = {"name", "latitude", "longitude", "fsq_category_labels"}
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
                        continue

                    category = first_category(row.get("fsq_category_labels"))
                    if not category:
                        no_category += 1
                        continue

                    address = (row.get("address") or "").strip()
                    store = Store.objects.filter(
                        normalized_name=normalize(name),
                        normalized_address=normalize(address),
                        latitude=latitude,
                        longitude=longitude,
                    ).first()

                    if store is None:
                        not_found += 1
                        continue

                    if store.category == category:
                        unchanged += 1
                        continue

                    store.category = category
                    store.save(update_fields=["category"])
                    updated += 1

            if options["dry_run"]:
                transaction.set_rollback(True)

        mode = "Dry run" if options["dry_run"] else "Sync complete"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode}: {updated} updated, {unchanged} already correct, "
                f"{not_found} had no matching store, {no_category} had no category in the CSV."
            )
        )
