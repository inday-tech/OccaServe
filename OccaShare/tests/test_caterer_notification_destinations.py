from app.services.notification import caterer_notification_destination


def test_caterer_notification_links_redirect_legacy_verification_routes():
    assert caterer_notification_destination("/caterer/verification", "warning") == (
        "/caterer/profile#verification"
    )
    assert caterer_notification_destination("/caterer/settings", "success") == (
        "/caterer/profile#verification"
    )
    assert caterer_notification_destination(
        "/caterer/profile#section-verification", "Verification"
    ) == "/caterer/profile#verification"


def test_caterer_notification_links_redirect_legacy_booking_dashboard():
    assert caterer_notification_destination(
        "/caterer/dashboard?page=bookings", "Booking"
    ) == "/caterer/bookings"


def test_caterer_notification_destination_preserves_specific_internal_link():
    link = "/caterer/profile?verification_file=verif_dti&verification_type=DTI_REGISTRATION#verification-file"
    assert caterer_notification_destination(link, "warning") == link


def test_caterer_notification_destination_uses_safe_relevant_fallbacks():
    assert caterer_notification_destination(None, "Verification") == (
        "/caterer/profile#verification"
    )
    assert caterer_notification_destination(None, "Payment") == "/caterer/payments"
    assert caterer_notification_destination("//example.com", "Booking") == (
        "/caterer/bookings"
    )
    assert caterer_notification_destination(r"/\\example.com", "Booking") == (
        "/caterer/bookings"
    )
