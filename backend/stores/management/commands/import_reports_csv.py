import csv
from dataclasses import dataclass
from datetime import datetime, timezone as datetime_timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from stores.models import PaymentMethod, Store, StorePaymentMethod, normalize


FIELD_COUNT = 11
VALID_STATUSES = {choice for choice, _ in StorePaymentMethod.Status.choices}
METHOD_COLUMNS = {
    "cash": 6,
    "credit-card": 7,
    "e-money": 8,
    "qr": 9,
}


@dataclass(frozen=True)
class Report:
    source_id: int
    name: str
    latitude: Decimal
    longitude: Decimal
    reported_at: datetime
    statuses: dict[str, str]
    updated_at: datetime


def coordinate(value, minimum, maximum, row_number, field_name):
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise CommandError(f"Row {row_number}: invalid {field_name}: {value!r}") from error
    if not minimum <= result <= maximum:
        raise CommandError(f"Row {row_number}: {field_name} is outside {minimum}..{maximum}")
    return result


def timestamp(value, row_number, field_name):
    result = parse_datetime(value)
    if result is None:
        raise CommandError(f"Row {row_number}: invalid {field_name}: {value!r}")
    if timezone.is_naive(result):
        result = timezone.make_aware(result, datetime_timezone.utc)
    return result


def read_reports(path):
    latest = {}
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        for row_number, row in enumerate(csv.reader(source), start=1):
            if len(row) != FIELD_COUNT:
                raise CommandError(
                    f"Row {row_number}: expected {FIELD_COUNT} columns, found {len(row)}"
                )
            name = row[1].strip()
            if not name:
                raise CommandError(f"Row {row_number}: store name is empty")
            statuses = {code: row[index].strip() for code, index in METHOD_COLUMNS.items()}
            invalid = sorted(set(statuses.values()) - VALID_STATUSES)
            if invalid:
                raise CommandError(f"Row {row_number}: invalid payment status: {', '.join(invalid)}")
            report = Report(
                source_id=int(row[0]),
                name=name,
                latitude=coordinate(row[2], Decimal("-90"), Decimal("90"), row_number, "latitude"),
                longitude=coordinate(
                    row[3], Decimal("-180"), Decimal("180"), row_number, "longitude"
                ),
                reported_at=timestamp(row[5], row_number, "reported_at"),
                statuses=statuses,
                updated_at=timestamp(row[10], row_number, "updated_at"),
            )
            key = (normalize(name), report.latitude, report.longitude)
            previous = latest.get(key)
            if previous is None or (report.updated_at, report.source_id) > (
                previous.updated_at,
                previous.source_id,
            ):
                latest[key] = report
    return latest


class Command(BaseCommand):
    help = "Import the legacy headerless reports.csv into Store and StorePaymentMethod."

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

        reports = read_reports(path)
        methods = {method.code: method for method in PaymentMethod.objects.all()}
        missing = sorted(set(METHOD_COLUMNS) - set(methods))
        if missing:
            raise CommandError(f"Missing payment methods: {', '.join(missing)}")

        created = 0
        updated = 0
        with transaction.atomic():
            for report in sorted(reports.values(), key=lambda item: item.source_id):
                store = Store.objects.filter(
                    normalized_name=normalize(report.name),
                    normalized_address="",
                    latitude=report.latitude,
                    longitude=report.longitude,
                ).first()
                if store is None:
                    store = Store.objects.create(
                        name=report.name,
                        address="",
                        latitude=report.latitude,
                        longitude=report.longitude,
                    )
                    created += 1
                else:
                    store.name = report.name
                    store.save(update_fields=["name", "normalized_name", "updated_at"])
                    updated += 1

                for code, status in report.statuses.items():
                    relation, _ = StorePaymentMethod.objects.update_or_create(
                        store=store,
                        payment_method=methods[code],
                        defaults={
                            "status": status,
                            "confirmed_at": (
                                None
                                if status == StorePaymentMethod.Status.UNKNOWN
                                else report.updated_at
                            ),
                        },
                    )
                    StorePaymentMethod.objects.filter(pk=relation.pk).update(
                        created_at=report.reported_at,
                        updated_at=report.updated_at,
                    )
                Store.objects.filter(pk=store.pk).update(
                    created_at=report.reported_at,
                    updated_at=report.updated_at,
                )

            if options["dry_run"]:
                transaction.set_rollback(True)

        duplicate_rows = 0
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            duplicate_rows = sum(1 for _ in csv.reader(source)) - len(reports)
        mode = "Dry run" if options["dry_run"] else "Import complete"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode}: {created} created, {updated} updated, "
                f"{duplicate_rows} older duplicate rows ignored."
            )
        )
