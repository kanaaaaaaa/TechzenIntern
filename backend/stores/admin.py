from django.contrib import admin

from .models import PaymentMethod, Store, StorePaymentMethod

from .models import UserPoints, PointHistory


class StorePaymentMethodInline(admin.TabularInline):
    model = StorePaymentMethod
    extra = 0
    fields = ["payment_method", "status", "confirmed_at"]

    def get_formset(self, request, obj=None, **kwargs):
        """Show one row per active payment method, so every method can be set at once."""
        missing = PaymentMethod.objects.filter(is_active=True)
        if obj is not None:
            missing = missing.exclude(stores__store=obj)
        missing = list(missing)
        kwargs["extra"] = len(missing)
        parent = super().get_formset(request, obj, **kwargs)

        class PrefilledFormSet(parent):
            def __init__(self, *args, **formset_kwargs):
                formset_kwargs["initial"] = [
                    {"payment_method": method.pk, "status": StorePaymentMethod.Status.UNKNOWN}
                    for method in missing
                ]
                super().__init__(*args, **formset_kwargs)

            def add_fields(self, form, index):
                super().add_fields(form, index)
                if form.initial and form.instance.pk is None:
                    # A prefilled row looks unchanged, so the formset would skip
                    # saving it. Force it through to keep every method on record.
                    form.empty_permitted = False
                    form.has_changed = lambda: True

        return PrefilledFormSet


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ["name", "address", "latitude", "longitude", "updated_at"]
    search_fields = ["name", "address"]
    inlines = [StorePaymentMethodInline]


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "category", "display_order", "is_active"]
    list_filter = ["category", "is_active"]
    list_editable = ["display_order", "is_active"]


@admin.register(StorePaymentMethod)
class StorePaymentMethodAdmin(admin.ModelAdmin):
    list_display = ["store", "payment_method", "status", "confirmed_at"]
    list_filter = ["status", "payment_method__category"]
    search_fields = ["store__name", "payment_method__name"]

@admin.register(UserPoints)
class UserPointsAdmin(admin.ModelAdmin):
    list_display = ['user', 'points', 'updated_at']
    search_fields = ['user__username']
    readonly_fields = ['user', 'created_at', 'updated_at']

@admin.register(PointHistory)
class PointHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'action_type', 'points', 'store', 'created_at']
    list_filter = ['action_type', 'created_at']
    search_fields = ['user__username', 'store__name']
    readonly_fields = ['user', 'store', 'action_type', 'points', 'created_at']
