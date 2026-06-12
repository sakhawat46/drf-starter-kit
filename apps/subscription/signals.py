import logging
import stripe
from django.conf import settings
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from django.db.models.signals import post_save, pre_delete

from .models import SubscriptionPackage, Subscription, PaymentHistory, IncomeReport

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

# Recurring billing
def _stripe_recurring_dict(pkg: SubscriptionPackage):
    days = pkg.get_billing_days() or 30
    return {"interval": "day", "interval_count": int(days)}

# Product name
def _product_name(pkg: SubscriptionPackage):
    if pkg.billing_cycle_type == "custom":
        label = f"{pkg.custom_days}-day Custom Plan"
    else:
        label = f"{pkg.billing_cycle} Plan"
    return f"{label} — ${pkg.price}"

# Signal to create/update Stripe Product and Price on SubscriptionPackage save
@receiver(post_save, sender=SubscriptionPackage)
def create_or_update_stripe_package(sender, instance, created, **kwargs):
    try:
        recurring = _stripe_recurring_dict(instance)
        name = _product_name(instance)

        # Create product if missing
        if not instance.stripe_product_id:
            product = stripe.Product.create(name=name)
            instance.stripe_product_id = product.id
            instance.save()

        # Create price if missing
        if not instance.stripe_price_id:
            price = stripe.Price.create(
                product=instance.stripe_product_id,
                currency=getattr(settings, "STRIPE_CURRENCY", "usd"),
                unit_amount=int(instance.price * 100),
                recurring=recurring,
            )
            instance.stripe_price_id = price.id
            instance.save()
            return

        # Update existing product/price if necessary
        product = stripe.Product.retrieve(instance.stripe_product_id)
        price = stripe.Price.retrieve(instance.stripe_price_id)

        # Update product name if changed
        if product.get("name") != name:
            stripe.Product.modify(instance.stripe_product_id, name=name)

        # Update price if unit_amount changed: deactivate old price and create a new one
        if price.get("unit_amount") != int(instance.price * 100):
            stripe.Price.modify(instance.stripe_price_id, active=False)
            new_price = stripe.Price.create(
                product=instance.stripe_product_id,
                currency=getattr(settings, "STRIPE_CURRENCY", "usd"),
                unit_amount=int(instance.price * 100),
                recurring=recurring,
            )
            instance.stripe_price_id = new_price.id
            instance.save()

    except Exception as exc:  # pragma: no cover - external API
        logger.exception("Stripe sync failed for SubscriptionPackage(id=%s): %s", instance.pk, exc)

# Safely deactivate Stripe product and price when a package is deleted.
@receiver(pre_delete, sender=SubscriptionPackage)
def deactivate_stripe_package(sender, instance, **kwargs):
    try:
        if instance.stripe_price_id:
            stripe.Price.modify(instance.stripe_price_id, active=False)
        if instance.stripe_product_id:
            stripe.Product.modify(instance.stripe_product_id, active=False)
    except Exception as exc:  # pragma: no cover - external API
        logger.exception("Failed to deactivate Stripe objects for SubscriptionPackage(id=%s): %s", instance.pk, exc)

# On successful payment, create or extend a Subscription for the user.
@receiver(post_save, sender=PaymentHistory)
def handle_successful_payment(sender, instance, created, **kwargs):
    # Only act on successful payments with an associated package
    if not created:
        return

    if instance.payment_status != "success":
        return

    pkg = instance.subscriptionpackage
    if not pkg:
        logger.debug("PaymentHistory(id=%s) has no subscription package; skipping subscription update.", instance.pk)
        return

    try:
        now = timezone.now()
        days = pkg.get_billing_days() or 30

        sub, _ = Subscription.objects.get_or_create(user=instance.user, subscriptionpackage=pkg, defaults={
            "start_date": now,
            "end_date": now + timedelta(days=days),
            "status": "active",
            "stripe_subscription_id": instance.transaction_id or None,
        })

        # If subscription already existed, extend if active or set new period if expired
        if sub.pk and sub.end_date:
            if sub.end_date > now and sub.status == "active":
                sub.end_date = sub.end_date + timedelta(days=days)
            else:
                sub.start_date = now
                sub.end_date = now + timedelta(days=days)
                sub.status = "active"
            # Update stripe_subscription_id if we have a transaction id
            if instance.transaction_id:
                sub.stripe_subscription_id = instance.transaction_id
            sub.save()

            # Update IncomeReport total income
            try:
                income_report = IncomeReport.objects.first()
                if income_report is None:
                    income_report = IncomeReport.objects.create(total_income=0)
                income_report.total_income += instance.amount
                income_report.save()
            except Exception as exc2:
                logger.exception("Failed to update IncomeReport for PaymentHistory(id=%s): %s", instance.pk, exc2)

    except Exception as exc:
        logger.exception("Failed to update Subscription for PaymentHistory(id=%s): %s", instance.pk, exc)

