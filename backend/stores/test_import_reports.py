import tempfile
from decimal import Decimal
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from .models import PaymentMethod, Store, StorePaymentMethod


class ImportReportsCsvTests(TestCase):
    def write_csv(self, rows):
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", delete=False)
        with handle:
            handle.write("\n".join(rows))
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return handle.name

    def test_imports_coordinates_and_latest_statuses(self):
        path = self.write_csv([
            "1,Cafe,16.081259,108.222577,19,2026-09-03 02:20:00+00,unknown,unknown,unknown,unknown,2026-09-03 02:20:16+00",
            "2,Cafe,16.081259,108.222577,19,2026-09-03 03:20:00+00,accepted,not_accepted,unknown,accepted,2026-09-03 03:20:16+00",
            "3,Cafe,16.081300,108.222600,22,2026-09-03 04:20:00+00,unknown,accepted,accepted,unknown,2026-09-03 04:20:16+00",
        ])

        call_command("import_reports_csv", path)

        self.assertEqual(Store.objects.count(), 2)
        first = Store.objects.get(latitude=Decimal("16.081259"))
        self.assertEqual(first.address, "")
        statuses = {
            item.payment_method.code: item.status
            for item in first.payment_methods.select_related("payment_method")
        }
        self.assertEqual(statuses["cash"], StorePaymentMethod.Status.ACCEPTED)
        self.assertEqual(statuses["credit-card"], StorePaymentMethod.Status.NOT_ACCEPTED)
        self.assertEqual(statuses["qr"], StorePaymentMethod.Status.ACCEPTED)

        call_command("import_reports_csv", path)

        self.assertEqual(Store.objects.count(), 2)
        self.assertEqual(StorePaymentMethod.objects.count(), 8)

    def test_dry_run_does_not_write(self):
        path = self.write_csv([
            "1,Cafe,16.081259,108.222577,19,2026-09-03 02:20:00+00,unknown,unknown,unknown,unknown,2026-09-03 02:20:16+00",
        ])

        call_command("import_reports_csv", path, dry_run=True)

        self.assertFalse(Store.objects.exists())
