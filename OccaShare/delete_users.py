"""
Delete specific user accounts and ALL connected data from Railway DB.
Targets: naomicaragay654@gmail.com, caragaynaomi30@gmail.com

Run: python -m OccaShare.delete_users
"""
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.db.database import engine

EMAILS_TO_DELETE = [
    "naomicaragay654@gmail.com",
    "caragaynaomi30@gmail.com",
]

def delete_users():
    with engine.connect() as conn:
        # 1. Find user IDs
        result = conn.execute(
            text("SELECT id, email, first_name, last_name, role FROM users WHERE email = ANY(:emails)"),
            {"emails": EMAILS_TO_DELETE}
        )
        users = result.fetchall()

        if not users:
            print("❌ No users found with those emails. Nothing to delete.")
            return

        user_ids = [u[0] for u in users]
        print(f"\n{'='*60}")
        print(f"🔍 FOUND {len(users)} USER(S) TO DELETE:")
        print(f"{'='*60}")
        for u in users:
            print(f"  ID={u[0]} | {u[1]} | {u[2]} {u[3]} | role={u[4]}")

        # 2. Find all booking IDs owned by these users
        booking_result = conn.execute(
            text("SELECT id FROM bookings WHERE user_id = ANY(:uids)"),
            {"uids": user_ids}
        )
        booking_ids = [r[0] for r in booking_result.fetchall()]
        print(f"\n📦 Found {len(booking_ids)} booking(s) to cascade-delete: {booking_ids}")

        # ============================================================
        # DRY-RUN PREVIEW: Show counts before deleting
        # ============================================================
        print(f"\n{'='*60}")
        print("📋 DRY-RUN PREVIEW — Records to be deleted:")
        print(f"{'='*60}")

        # Booking-child tables (keyed by booking_id)
        booking_child_tables = [
            "booking_menu_items",
            "booking_messages",
            "booking_history",
            "booking_contracts",
            "booking_tasks",
            "booking_expenses",
            "quotations",
            "fraud_flags",
            "payout_items",
            "billing_invoices",
        ]

        for tbl in booking_child_tables:
            if booking_ids:
                cnt = conn.execute(
                    text(f"SELECT COUNT(*) FROM {tbl} WHERE booking_id = ANY(:bids)"),
                    {"bids": booking_ids}
                ).scalar()
            else:
                cnt = 0
            print(f"  {tbl}: {cnt}")

        # Tables with both booking_id and user_id (OCR, reviews, disputes, verification_attempts)
        hybrid_tables_booking = ["ocr_verification", "reviews", "dispute_reports", "verification_attempts"]
        for tbl in hybrid_tables_booking:
            cnt_b = 0
            cnt_u = 0
            if booking_ids:
                cnt_b = conn.execute(
                    text(f"SELECT COUNT(*) FROM {tbl} WHERE booking_id = ANY(:bids)"),
                    {"bids": booking_ids}
                ).scalar()
            cnt_u = conn.execute(
                text(f"SELECT COUNT(*) FROM {tbl} WHERE user_id = ANY(:uids)"),
                {"uids": user_ids}
            ).scalar()
            print(f"  {tbl}: {max(cnt_b, cnt_u)} (by booking: {cnt_b}, by user: {cnt_u})")

        # User-direct tables (keyed by user_id)
        user_direct_tables = [
            "notifications",
            "refresh_tokens",
            "audit_logs",
            "identity_verifications",
            "platform_feedback",
            "inquiries",
            "verification_sessions",
            "item_ratings",
            "profile_views",
        ]

        for tbl in user_direct_tables:
            cnt = conn.execute(
                text(f"SELECT COUNT(*) FROM {tbl} WHERE user_id = ANY(:uids)"),
                {"uids": user_ids}
            ).scalar()
            print(f"  {tbl}: {cnt}")

        # Chat messages (sender_id OR receiver_id)
        chat_cnt = conn.execute(
            text("SELECT COUNT(*) FROM chat_messages WHERE sender_id = ANY(:uids) OR receiver_id = ANY(:uids)"),
            {"uids": user_ids}
        ).scalar()
        print(f"  chat_messages: {chat_cnt}")

        # Bookings themselves
        print(f"  bookings: {len(booking_ids)}")

        # Users
        print(f"  users: {len(users)}")

        # ============================================================
        # CONFIRM
        # ============================================================
        print(f"\n{'='*60}")
        confirm = input("⚠️  TYPE 'DELETE' TO CONFIRM PERMANENT DELETION: ").strip()
        if confirm != "DELETE":
            print("❌ Aborted. No changes made.")
            return

        # ============================================================
        # EXECUTE DELETION (child → parent order)
        # ============================================================
        print("\n🗑️  Deleting...")

        # A. Booking-child tables
        if booking_ids:
            for tbl in booking_child_tables:
                r = conn.execute(
                    text(f"DELETE FROM {tbl} WHERE booking_id = ANY(:bids)"),
                    {"bids": booking_ids}
                )
                print(f"  ✓ {tbl}: {r.rowcount} deleted")

            # Hybrid tables — delete by booking_id OR user_id
            for tbl in hybrid_tables_booking:
                r = conn.execute(
                    text(f"DELETE FROM {tbl} WHERE booking_id = ANY(:bids) OR user_id = ANY(:uids)"),
                    {"bids": booking_ids, "uids": user_ids}
                )
                print(f"  ✓ {tbl}: {r.rowcount} deleted")
        else:
            # Still clean hybrid tables by user_id
            for tbl in hybrid_tables_booking:
                r = conn.execute(
                    text(f"DELETE FROM {tbl} WHERE user_id = ANY(:uids)"),
                    {"uids": user_ids}
                )
                print(f"  ✓ {tbl}: {r.rowcount} deleted")

        # B. User-direct tables
        for tbl in user_direct_tables:
            r = conn.execute(
                text(f"DELETE FROM {tbl} WHERE user_id = ANY(:uids)"),
                {"uids": user_ids}
            )
            print(f"  ✓ {tbl}: {r.rowcount} deleted")

        # C. Chat messages
        r = conn.execute(
            text("DELETE FROM chat_messages WHERE sender_id = ANY(:uids) OR receiver_id = ANY(:uids)"),
            {"uids": user_ids}
        )
        print(f"  ✓ chat_messages: {r.rowcount} deleted")

        # D. Portfolios (nullify booking_id first, then delete)
        conn.execute(
            text("UPDATE portfolios SET booking_id = NULL WHERE booking_id = ANY(:bids)"),
            {"bids": booking_ids} if booking_ids else {"bids": []}
        )

        # E. Bookings
        if booking_ids:
            r = conn.execute(
                text("DELETE FROM bookings WHERE id = ANY(:bids)"),
                {"bids": booking_ids}
            )
            print(f"  ✓ bookings: {r.rowcount} deleted")

        # F. Users
        r = conn.execute(
            text("DELETE FROM users WHERE id = ANY(:uids)"),
            {"uids": user_ids}
        )
        print(f"  ✓ users: {r.rowcount} deleted")

        conn.commit()
        print(f"\n{'='*60}")
        print("✅ ALL DATA PERMANENTLY DELETED.")
        print(f"{'='*60}")


if __name__ == "__main__":
    delete_users()
