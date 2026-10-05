import re
from typing import Optional, Union, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, func


def get_caterer_code(caterer: Union[object, str, int, None], db: Optional[Session] = None) -> str:
    """
    Derive standard uppercase 3-letter caterer prefix:
      REP = Replica
      DAR = Darwin
      GAB = Gab Hub
    Falls back to first 3 letters of cleaned business name if another business exists.
    """
    if caterer is None:
        return "CAT"

    # If caterer is an int (caterer_id), look up the profile
    if isinstance(caterer, int):
        if db is not None:
            from app.db import models
            cp = db.query(models.CatererProfile).filter(models.CatererProfile.id == caterer).first()
            if cp:
                return get_caterer_code(cp, db=None)
        return "CAT"

    # If caterer is a string
    if isinstance(caterer, str):
        name = caterer
    else:
        name = (
            getattr(caterer, "business_name", None)
            or getattr(caterer, "slug", None)
            or ""
        )
        # Check user fields if available
        user = getattr(caterer, "user", None)
        if user and not name:
            name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}"

    clean_lower = str(name).lower().strip()
    if "replica" in clean_lower:
        return "REP"
    if "darwin" in clean_lower:
        return "DAR"
    if "gab" in clean_lower:
        return "GAB"

    # Fallback to first 3 letters of clean business name
    clean = re.sub(r'[^A-Za-z]', '', str(name).strip())
    if len(clean) >= 3:
        return clean[:3].upper()
    elif len(clean) > 0:
        return clean.upper().ljust(3, 'X')

    return "CAT"


def _get_existing_max_seq(db: Session, caterer_id: int, record_type: str) -> int:
    """Find the highest sequence number in the database for caterer and record type."""
    from app.db import models
    max_seq = 0

    if record_type == "BK":
        rows = db.query(models.Booking.booking_ref).filter(
            models.Booking.caterer_id == caterer_id,
            models.Booking.booking_ref.isnot(None)
        ).all()
        for (ref,) in rows:
            if ref:
                match = re.search(r'-(\d+)$', str(ref).strip())
                if match:
                    try:
                        max_seq = max(max_seq, int(match.group(1)))
                    except ValueError:
                        pass

    elif record_type == "C":
        # Check caterer_customers table first
        cust_rows = db.query(models.CatererCustomer.customer_ref).filter(
            models.CatererCustomer.caterer_id == caterer_id
        ).all()
        for (ref,) in cust_rows:
            if ref:
                match = re.search(r'-(\d+)$', str(ref).strip())
                if match:
                    try:
                        max_seq = max(max_seq, int(match.group(1)))
                    except ValueError:
                        pass
        # Also check bookings.customer_ref
        b_rows = db.query(models.Booking.customer_ref).filter(
            models.Booking.caterer_id == caterer_id,
            models.Booking.customer_ref.isnot(None)
        ).all()
        for (ref,) in b_rows:
            if ref:
                match = re.search(r'-(\d+)$', str(ref).strip())
                if match:
                    try:
                        max_seq = max(max_seq, int(match.group(1)))
                    except ValueError:
                        pass

    elif record_type == "PAY":
        pay_rows = db.query(models.BookingPaymentRecord.payment_ref).join(
            models.Booking, models.BookingPaymentRecord.booking_id == models.Booking.id
        ).filter(
            models.Booking.caterer_id == caterer_id,
            models.BookingPaymentRecord.payment_ref.isnot(None)
        ).all()
        for (ref,) in pay_rows:
            if ref:
                match = re.search(r'-(\d+)$', str(ref).strip())
                if match:
                    try:
                        max_seq = max(max_seq, int(match.group(1)))
                    except ValueError:
                        pass

    elif record_type == "INV":
        inv_rows = db.query(models.BillingInvoice.invoice_ref).filter(
            models.BillingInvoice.caterer_id == caterer_id,
            models.BillingInvoice.invoice_ref.isnot(None)
        ).all()
        for (ref,) in inv_rows:
            if ref:
                match = re.search(r'-(\d+)$', str(ref).strip())
                if match:
                    try:
                        max_seq = max(max_seq, int(match.group(1)))
                    except ValueError:
                        pass

    return max_seq


def get_next_sequence_num(db: Session, caterer_id: int, record_type: str) -> int:
    """
    Atomically get and increment sequence counter for a specific caterer and record type.
    Sequence numbers are never decremented or reused even if a record is cancelled or deleted.
    """
    from app.db import models

    # Query with FOR UPDATE lock if supported
    try:
        seq_rec = db.query(models.CatererIdSequence).filter_by(
            caterer_id=caterer_id,
            record_type=record_type
        ).with_for_update().first()
    except Exception:
        seq_rec = db.query(models.CatererIdSequence).filter_by(
            caterer_id=caterer_id,
            record_type=record_type
        ).first()

    if not seq_rec:
        initial = _get_existing_max_seq(db, caterer_id, record_type)
        seq_rec = models.CatererIdSequence(
            caterer_id=caterer_id,
            record_type=record_type,
            last_seq=initial
        )
        db.add(seq_rec)
        db.flush()

    seq_rec.last_seq += 1
    db.flush()
    return seq_rec.last_seq


def generate_booking_ref(db: Session, caterer_id: int) -> str:
    """Generate standardized Booking ID: [CATERER]-BK-[001]."""
    code = get_caterer_code(caterer_id, db=db)
    seq = get_next_sequence_num(db, caterer_id, "BK")
    return f"{code}-BK-{seq:03d}"


def get_or_create_customer_ref(
    db: Session,
    caterer_id: int,
    user_id: Optional[int] = None,
    customer_name: Optional[str] = None,
    customer_email: Optional[str] = None,
    customer_contact: Optional[str] = None
) -> str:
    """
    Get existing Customer ID or generate a new sequential one: [CATERER]-C-[001].
    A customer retains the exact same ID for all bookings with this caterer.
    """
    from app.db import models

    key = None
    if user_id:
        key = f"user_{user_id}"
    elif customer_email and str(customer_email).strip() and not str(customer_email).strip().lower().startswith("walkin@"):
        key = f"email_{str(customer_email).strip().lower()}"
    elif customer_contact and str(customer_contact).strip():
        digits = re.sub(r'\D', '', str(customer_contact).strip())
        if len(digits) >= 7:
            key = f"phone_{digits[-10:]}"
    elif customer_name and str(customer_name).strip():
        key = f"name_{str(customer_name).strip().lower()}"

    if key:
        existing = db.query(models.CatererCustomer).filter_by(
            caterer_id=caterer_id,
            customer_key=key
        ).first()
        if existing and existing.customer_ref:
            return existing.customer_ref

    # Also check if existing bookings for this user with this caterer have a customer_ref
    if user_id:
        b_match = db.query(models.Booking.customer_ref).filter(
            models.Booking.caterer_id == caterer_id,
            models.Booking.user_id == user_id,
            models.Booking.customer_ref.isnot(None),
            models.Booking.customer_ref != ""
        ).first()
        if b_match and b_match[0] and "-C-" in b_match[0]:
            ref = b_match[0]
            if key:
                cat_cust = models.CatererCustomer(
                    caterer_id=caterer_id,
                    user_id=user_id,
                    customer_key=key,
                    customer_ref=ref
                )
                db.add(cat_cust)
                try:
                    db.flush()
                except Exception:
                    pass
            return ref

    code = get_caterer_code(caterer_id, db=db)
    seq = get_next_sequence_num(db, caterer_id, "C")
    ref = f"{code}-C-{seq:03d}"

    if key:
        cat_cust = models.CatererCustomer(
            caterer_id=caterer_id,
            user_id=user_id,
            customer_key=key,
            customer_ref=ref
        )
        db.add(cat_cust)
        try:
            db.flush()
        except Exception:
            pass

    return ref


def generate_payment_ref(db: Session, caterer_id: int) -> str:
    """Generate standardized Payment ID: [CATERER]-PAY-[001]."""
    code = get_caterer_code(caterer_id, db=db)
    seq = get_next_sequence_num(db, caterer_id, "PAY")
    return f"{code}-PAY-{seq:03d}"


def generate_invoice_ref(db: Session, caterer_id: int) -> str:
    """Generate standardized Invoice ID: [CATERER]-INV-[001]."""
    code = get_caterer_code(caterer_id, db=db)
    seq = get_next_sequence_num(db, caterer_id, "INV")
    return f"{code}-INV-{seq:03d}"


def sync_and_standardize_caterer_ids(db: Session, caterer_id: int) -> dict:
    """
    Standardize all Customer, Booking, Payment, and Invoice IDs for a specific
    caterer (e.g. DAR, REP, GAB) so they are strictly sequential (001, 002, 003...)
    without gaps, and harmonious between Customer, Booking, Payment, and Invoice.
    """
    from app.db import models

    code = get_caterer_code(caterer_id, db=db)
    
    # 1. Fetch only active, visible bookings (exclude drafts and archived)
    active_bookings = db.query(models.Booking).filter(
        models.Booking.caterer_id == caterer_id,
        models.Booking.status != 'draft',
        models.Booking.is_archived == False
    ).order_by(models.Booking.id.asc()).all()

    # Clear any draft bookings' refs so they don't consume sequential numbers
    draft_bookings = db.query(models.Booking).filter(
        models.Booking.caterer_id == caterer_id,
        (models.Booking.status == 'draft') | (models.Booking.is_archived == True)
    ).all()
    for db_b in draft_bookings:
        if db_b._booking_ref and "-BK-" in db_b._booking_ref:
            db_b._booking_ref = None
            try:
                db.execute(
                    text("UPDATE bookings SET booking_ref = NULL WHERE id = :bid"),
                    {"bid": db_b.id}
                )
            except Exception:
                pass

    seen_customer_keys = {}
    cust_idx = 0
    total_payments = 0
    total_invoices = 0

    # Clean existing customer mappings for this caterer to re-align cleanly
    existing_custs = db.query(models.CatererCustomer).filter_by(caterer_id=caterer_id).order_by(models.CatererCustomer.id.asc()).all()
    for ec in existing_custs:
        if ec.customer_ref and f"{code}-C-" in ec.customer_ref:
            seen_customer_keys[ec.customer_key] = ec.customer_ref
            m = re.search(r'-(\d+)$', ec.customer_ref)
            if m:
                cust_idx = max(cust_idx, int(m.group(1)))

    for idx, b in enumerate(active_bookings, start=1):
        expected_bref = f"{code}-BK-{idx:03d}"
        b._booking_ref = expected_bref
        try:
            db.execute(
                text("UPDATE bookings SET booking_ref = :bref WHERE id = :bid"),
                {"bref": expected_bref, "bid": b.id}
            )
        except Exception:
            pass

        # Identify unique customer key for this booking
        c_key = None
        if b.user_id:
            c_key = f"user_{b.user_id}"
        elif b.customer_email and str(b.customer_email).strip() and not str(b.customer_email).lower().startswith("walkin@"):
            c_key = f"email_{str(b.customer_email).strip().lower()}"
        elif b.customer_contact and str(b.customer_contact).strip():
            digits = re.sub(r'\D', '', str(b.customer_contact).strip())
            if len(digits) >= 7:
                c_key = f"phone_{digits[-10:]}"
            else:
                c_key = f"booking_{b.id}"
        elif b.customer_name and str(b.customer_name).strip():
            c_key = f"name_{str(b.customer_name).strip().lower()}"
        else:
            c_key = f"booking_{b.id}"

        if c_key not in seen_customer_keys:
            cust_idx += 1
            expected_cref = f"{code}-C-{cust_idx:03d}"
            seen_customer_keys[c_key] = expected_cref
            try:
                cat_c = db.query(models.CatererCustomer).filter_by(caterer_id=caterer_id, customer_key=c_key).first()
                if not cat_c:
                    db.add(models.CatererCustomer(
                        caterer_id=caterer_id,
                        user_id=b.user_id,
                        customer_key=c_key,
                        customer_ref=expected_cref
                    ))
                else:
                    cat_c.customer_ref = expected_cref
            except Exception:
                pass
        else:
            expected_cref = seen_customer_keys[c_key]

        b._customer_ref = expected_cref
        try:
            db.execute(
                text("UPDATE bookings SET customer_ref = :cref WHERE id = :bid"),
                {"cref": expected_cref, "bid": b.id}
            )
        except Exception:
            pass

        # Standardize payments for this booking to match booking sequence
        pay_records = db.query(models.BookingPaymentRecord).filter(
            models.BookingPaymentRecord.booking_id == b.id
        ).order_by(models.BookingPaymentRecord.id.asc()).all()

        for p_idx, prec in enumerate(pay_records, start=1):
            total_payments += 1
            expected_pref = f"{code}-PAY-{idx:03d}" if len(pay_records) == 1 else f"{code}-PAY-{idx:03d}-{p_idx}"
            prec.payment_ref = expected_pref
            try:
                db.execute(
                    text("UPDATE booking_payment_records SET payment_ref = :pref WHERE id = :pid"),
                    {"pref": expected_pref, "pid": prec.id}
                )
            except Exception:
                pass

        # Standardize invoices linked to this booking
        invoices = db.query(models.BillingInvoice).filter(
            models.BillingInvoice.booking_id == b.id
        ).order_by(models.BillingInvoice.id.asc()).all()

        for inv in invoices:
            total_invoices += 1
            expected_iref = f"{code}-INV-{idx:03d}"
            inv.invoice_ref = expected_iref
            try:
                db.execute(
                    text("UPDATE billing_invoices SET invoice_ref = :iref WHERE id = :iid"),
                    {"iref": expected_iref, "iid": inv.id}
                )
            except Exception:
                pass

    # Standardize any unlinked invoices for this caterer
    unlinked_invoices = db.query(models.BillingInvoice).filter(
        models.BillingInvoice.caterer_id == caterer_id,
        (models.BillingInvoice.booking_id.is_(None)) | (~models.BillingInvoice.booking_id.in_([b.id for b in active_bookings]))
    ).order_by(models.BillingInvoice.id.asc()).all()

    inv_counter = len(active_bookings)
    for u_inv in unlinked_invoices:
        inv_counter += 1
        total_invoices += 1
        expected_iref = f"{code}-INV-{inv_counter:03d}"
        u_inv.invoice_ref = expected_iref
        try:
            db.execute(
                text("UPDATE billing_invoices SET invoice_ref = :iref WHERE id = :iid"),
                {"iref": expected_iref, "iid": u_inv.id}
            )
        except Exception:
            pass

    # Update atomic sequences table
    b_count = len(active_bookings)
    p_count = max(b_count, total_payments)
    i_count = max(b_count, total_invoices, inv_counter)

    for r_type, s_val in [("BK", b_count), ("C", cust_idx), ("PAY", p_count), ("INV", i_count)]:
        try:
            db.execute(
                text("""
                    INSERT INTO caterer_id_sequences (caterer_id, record_type, last_seq, updated_at)
                    VALUES (:cid, :rtype, :seq, NOW())
                    ON CONFLICT (caterer_id, record_type) 
                    DO UPDATE SET last_seq = EXCLUDED.last_seq, updated_at = NOW()
                """),
                {"cid": caterer_id, "rtype": r_type, "seq": s_val}
            )
        except Exception:
            pass

    try:
        db.commit()
    except Exception:
        db.rollback()

    return {
        "caterer_id": caterer_id,
        "code": code,
        "bookings_count": b_count,
        "customers_count": cust_idx,
        "payments_count": p_count,
        "invoices_count": i_count
    }


def sync_and_standardize_all_ids(db: Session) -> dict:
    """
    Standardize all existing Customer, Booking, Payment, and Invoice IDs
    across all caterers (REP, DAR, GAB, etc.) while strictly preserving
    all database relational foreign keys and connections.
    """
    from app.db import models

    results = {
        "caterers_processed": 0,
        "customers_standardized": 0,
        "bookings_standardized": 0,
        "payments_standardized": 0,
        "invoices_standardized": 0
    }

    try:
        caterers = db.query(models.CatererProfile).order_by(models.CatererProfile.id.asc()).all()
        for cp in caterers:
            cat_res = sync_and_standardize_caterer_ids(db, cp.id)
            results["caterers_processed"] += 1
            results["bookings_standardized"] += cat_res["bookings_count"]
            results["customers_standardized"] += cat_res["customers_count"]
            results["payments_standardized"] += cat_res["payments_count"]
            results["invoices_standardized"] += cat_res["invoices_count"]
    except Exception as e:
        print(f"[ID_SERVICE SYNC ERROR] {e}")

    return results
