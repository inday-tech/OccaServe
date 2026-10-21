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


def test_caterer_booking_notification_focus_opens_booking_and_relevant_tab():
    assert caterer_notification_destination(
        "/caterer/bookings?focus=42", "Payment", "Payment Reminder"
    ) == "/caterer/bookings?open_booking=42&open_tab=payment"


def test_customer_facing_booking_links_are_routed_to_caterer_workspace():
    assert caterer_notification_destination(
        "/bookings/step/payment/42", "Payment", "Payment Proof Submitted"
    ) == "/caterer/bookings?open_booking=42&open_tab=payment"
    assert caterer_notification_destination(
        "/customer/bookings/manage/42", "Booking", "Booking Request"
    ) == "/caterer/bookings?open_booking=42"


def test_contract_sign_notification_opens_booking_contract_tab():
    assert caterer_notification_destination(
        "/caterer/bookings/42/sign", "Booking", "Contract Signed"
    ) == "/caterer/bookings?open_booking=42&open_tab=contract"


def test_caterer_notification_fallbacks_open_relevant_sections():
    assert caterer_notification_destination(None, "Message", "New Consultation Message") == (
        "/caterer/messages"
    )
    assert caterer_notification_destination(None, "Customer", "New Customer") == (
        "/caterer/customers"
    )
    assert caterer_notification_destination(None, "Review", "New Review") == (
        "/caterer/reviews"
    )
