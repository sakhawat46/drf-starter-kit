from django.contrib import admin
from .models import SubscriptionPackage, Features, Subscription, PaymentHistory
from unfold.admin import ModelAdmin, TabularInline


# Subscription Package Features
class FeaturesInline(TabularInline):
    model = Features
    extra = 1
    ordering_field = "order" # enables drag-and-drop sorting
    hide_ordering_field = False
    fields = ("text", "include", "order")  # keep order included (required)

    class Media:
        js = ("admin/js/feature_order_autofill.js",)

# Subscription Package
@admin.register(SubscriptionPackage)
class SubscriptionPackageAdmin(ModelAdmin):
    list_display = ('billing_cycle', 'price', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'billing_cycle')
    search_fields = ('billing_cycle', 'price')
    inlines = [FeaturesInline]

    fieldsets = (
        (None, {
            'fields': (
                'billing_cycle_type', 
                'billing_cycle', 
                'custom_days', 
                'price', 
                'is_active',
                )
        }),
    )

    class Media:
        js = ("admin/js/planitem_billing_toggle.js",)


# Subscribed users admin
@admin.register(Subscription)
class SubscriptionAdmin(ModelAdmin):
    list_display = ('user_email', 'subscriptionpackage', 'status', 'start_date', 'end_date', 'stripe_subscription_id', 'created_at')
    list_filter = ('status', 'subscriptionpackage')
    search_fields = ('user__email', 'stripe_subscription_id')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'subscriptionpackage')
    ordering = ('-start_date',)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(ModelAdmin):
    list_display = ('user', 'subscriptionpackage', 'amount', 'payment_gateway', 'payment_status', 'transaction_id', 'paid_at')
    list_filter = ('payment_gateway', 'payment_status')
    search_fields = ('user__email', 'transaction_id')
    readonly_fields = ('paid_at',)
