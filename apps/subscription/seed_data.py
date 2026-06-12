from decimal import Decimal


def seed_subscription_plans():
    """Seed three preset plans (7, 14, 30 days) with feature rows.

    Features' `include` field follows the screenshot: a cross means include=False.
    """

    # Import models lazily to avoid "Apps aren't loaded yet" when module is imported
    from apps.subscription.models import SubscriptionPackage, Features

    plans = [
        {
            "billing_cycle": "7_days",
            "price": Decimal("24.00"),
            "features": [
                {"text": "Standard visibility boost", "include": True},
                {"text": "Standard Reach", "include": True},
                {"text": "Maximum_exposures", "include": False},
                {"text": "priority", "include": False},
            ],
        },
        {
            "billing_cycle": "14_days",
            "price": Decimal("88.00"),
            "features": [
                {"text": "Extend visibility boost", "include": True},
                {"text": "Extend Reach", "include": True},
                {"text": "Extend_exposures", "include": False},
                {"text": "Extend_priority", "include": False},
            ],
        },
        {
            "billing_cycle": "30_days",
            "price": Decimal("149.00"),
            "features": [
                {"text": "Maximum visibility boost", "include": True},
                {"text": "Maximum Reach", "include": True},
                {"text": "maximum_exposures", "include": False},
                {"text": "maximum_priority", "include": False},
            ],
        },
    ]

    for plan_data in plans:
        plan, created = SubscriptionPackage.objects.get_or_create(
            billing_cycle_type="preset",
            billing_cycle=plan_data["billing_cycle"],
            defaults={"price": plan_data["price"]},
        )

        # Update price if different
        if not created and plan.price != plan_data["price"]:
            plan.price = plan_data["price"]
            plan.save()

        # Create features; keep ordering consistent
        for idx, feat in enumerate(plan_data["features"], start=1):
            Features.objects.update_or_create(
                subscriptionpackage=plan,
                text=feat["text"],
                defaults={"include": feat["include"], "order": idx},
            )

    print("✅ Subscription plans seeded successfully.")
