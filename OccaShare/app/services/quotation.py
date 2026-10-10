from sqlalchemy.orm import Session
from ..db import models
from decimal import Decimal
from datetime import datetime, timedelta

class QuotationService:
    def create_quotation(self, db: Session, booking: models.Booking, downpayment_percent: int = 30) -> models.Quotation:
        """
        Dispatches to Fixed Package or Customizable Package quotation generation
        based on the package's pricing mode and booking requirements.
        """
        package = booking.package
        is_customizable = False
        if package and getattr(package, 'pricing_mode', None) == 'customizable':
            is_customizable = True
        elif booking.custom_requirements and booking.custom_requirements.get('package_type') == 'customizable':
            is_customizable = True

        # Check for existing quotation to update or preserve
        existing_quote = db.query(models.Quotation).filter(models.Quotation.booking_id == booking.id).first()
        if existing_quote and existing_quote.status in ['signed', 'awaiting_caterer', 'awaiting_customer']:
            return existing_quote

        if is_customizable:
            return self._create_customizable_quotation(db, booking, downpayment_percent, existing_quote)
        else:
            return self._create_fixed_quotation(db, booking, downpayment_percent, existing_quote)

    def _create_customizable_quotation(
        self, db: Session, booking: models.Booking, downpayment_percent: int, existing_quote: models.Quotation = None
    ) -> models.Quotation:
        """
        CUSTOMIZABLE PACKAGE QUOTATION:
        Uses ONLY the food/menu items, services, and equipment selected by the customer.
        Computes customized total directly from customer selections.
        Does NOT mix with fixed package inclusions, fixed package prices, or 0.00 base price.
        """
        package = booking.package
        guest_count = int(booking.guest_count or 1)
        
        # 1. Retrieve customization selections
        sess_cust = {}
        if booking.custom_requirements and isinstance(booking.custom_requirements, dict):
            sess_cust = booking.custom_requirements.get("customization", {}) or {}

        selected_food = []
        selected_services = []
        selected_equipment = []

        # Customizable packages still have a configured base rate.  The
        # customer's food selections carry upgrade fees on top of that rate;
        # they are not the catalog item's full selling price.
        base_price = Decimal("0")
        if sess_cust and isinstance(sess_cust, dict):
            raw_base = sess_cust.get("base_price")
            if raw_base is not None:
                try:
                    base_price = Decimal(str(raw_base))
                except (TypeError, ValueError):
                    base_price = Decimal("0")
        if base_price <= 0 and package:
            base_price = Decimal(str(getattr(package, "price_per_head", None) or getattr(package, "price", 0) or 0))
        base_total = base_price * Decimal(str(guest_count))

        # From stored customization payload
        if sess_cust and isinstance(sess_cust, dict):
            for food in sess_cust.get("selected_food", []):
                # Menu selections are included in the per-guest package rate.
                # Only services/equipment add separate charges.
                u_price = 0.0
                # Serving unit is usually per pax / guest
                unit_str = str(food.get("unit", "pax")).lower()
                qty = guest_count if ("pax" in unit_str or "guest" in unit_str or not food.get("qty") or food.get("qty") == 1) else int(food.get("qty", guest_count))
                subtotal = float(Decimal(str(u_price)) * Decimal(str(qty)))
                selected_food.append({
                    "id": food.get("id"),
                    "name": food.get("name", "Dish"),
                    "category": food.get("category", "Menu Item"),
                    "price": u_price,
                    "unit_price": u_price,
                    "unit": food.get("unit", "Per Pax / Guest"),
                    "qty": qty,
                    "quantity": qty,
                    "subtotal": subtotal
                })

            for srv in sess_cust.get("selected_services", []):
                u_price = float(srv.get("price", 0))
                qty = int(srv.get("qty", 1) or 1)
                subtotal = float(Decimal(str(u_price)) * Decimal(str(qty)))
                selected_services.append({
                    "id": srv.get("id"),
                    "name": srv.get("name", "Service"),
                    "price": u_price,
                    "unit_price": u_price,
                    "unit": srv.get("unit", "Per Event"),
                    "qty": qty,
                    "quantity": qty,
                    "subtotal": subtotal
                })

            for eq in sess_cust.get("selected_equipment", []):
                u_price = float(eq.get("price", 0))
                qty = int(eq.get("qty", 1) or 1)
                subtotal = float(Decimal(str(u_price)) * Decimal(str(qty)))
                selected_equipment.append({
                    "id": eq.get("id"),
                    "name": eq.get("name", "Equipment"),
                    "price": u_price,
                    "unit_price": u_price,
                    "unit": eq.get("unit", "Per Piece"),
                    "qty": qty,
                    "quantity": qty,
                    "subtotal": subtotal
                })

        # Fallback to BookingMenuItem if session customization payload was missing
        if not selected_food and not selected_services and not selected_equipment:
            from ..db.models import BookingMenuItem
            booking_items = db.query(BookingMenuItem).filter(BookingMenuItem.booking_id == booking.id).all()
            for b_item in booking_items:
                if b_item.menu_item:
                    u_price = float(b_item.price if b_item.price is not None else (b_item.menu_item.price or 0))
                    qty = b_item.quantity or guest_count
                    subtotal = float(Decimal(str(u_price)) * Decimal(str(qty)))
                    selected_food.append({
                        "id": b_item.menu_item_id,
                        "name": b_item.menu_item.name,
                        "category": b_item.menu_item.category or "Menu Item",
                        "price": u_price,
                        "unit_price": u_price,
                        "unit": "Per Pax / Guest",
                        "qty": qty,
                        "quantity": qty,
                        "subtotal": subtotal
                    })
                elif b_item.service:
                    u_price = float(b_item.price if b_item.price is not None else (b_item.service.price or 0))
                    qty = b_item.quantity or 1
                    subtotal = float(Decimal(str(u_price)) * Decimal(str(qty)))
                    selected_services.append({
                        "id": b_item.service_id,
                        "name": b_item.service.name,
                        "price": u_price,
                        "unit_price": u_price,
                        "unit": "Per Event",
                        "qty": qty,
                        "quantity": qty,
                        "subtotal": subtotal
                    })
                elif b_item.equipment:
                    u_price = float(b_item.price if b_item.price is not None else (b_item.equipment.price or 0))
                    qty = b_item.quantity or 1
                    subtotal = float(Decimal(str(u_price)) * Decimal(str(qty)))
                    selected_equipment.append({
                        "id": b_item.equipment_id,
                        "name": b_item.equipment.name,
                        "price": u_price,
                        "unit_price": u_price,
                        "unit": "Per Piece",
                        "qty": qty,
                        "quantity": qty,
                        "subtotal": subtotal
                    })

        food_total = sum(Decimal(str(f["subtotal"])) for f in selected_food)
        services_total = sum(Decimal(str(s["subtotal"])) for s in selected_services)
        equipment_total = sum(Decimal(str(e["subtotal"])) for e in selected_equipment)
        customized_subtotal = base_total + food_total + services_total + equipment_total

        addons = []
        travel_fee = Decimal(str(getattr(booking, 'travel_fee', 0) or 0))
        if travel_fee > 0:
            addons.append({
                "id": "travel_fee",
                "name": "Delivery & Travel Fee",
                "price": float(travel_fee),
                "unit_price": float(travel_fee),
                "quantity": 1,
                "category": "fee"
            })

        total_amount = customized_subtotal + travel_fee

        # Accept deposit choices from 30% to 100% in 10% increments.
        if downpayment_percent not in range(30, 101, 10):
            downpayment_percent = 30

        package_details = {
            "package_type": "customizable",
            "name": package.name if package else "Customizable Catering Package",
            "description": getattr(package, 'description', '') or "Customized selections chosen by customer.",
            "guest_count": guest_count,
            "pricing_mode": "customizable",
            "selected_food": selected_food,
            "selected_services": selected_services,
            "selected_equipment": selected_equipment,
            "food_total": float(food_total),
            "services_total": float(services_total),
            "equipment_total": float(equipment_total),
            "base_price": float(base_price),
            "base_package_total": float(base_total),
            "food_upgrade_total": float(food_total),
            "customized_total": float(customized_subtotal),
            "base_amount": float(customized_subtotal) # Available for backward compat
        }

        if existing_quote:
            existing_quote.package_details = package_details
            existing_quote.addons = addons
            existing_quote.total_amount = float(total_amount)
            existing_quote.downpayment_percent = downpayment_percent
            quotation = existing_quote
        else:
            quotation = models.Quotation(
                booking_id=booking.id,
                package_details=package_details,
                addons=addons,
                total_amount=float(total_amount),
                downpayment_percent=downpayment_percent,
                status="draft"
            )
            db.add(quotation)

        db.flush()

        booking.expires_at = datetime.now() + timedelta(hours=24)
        booking.reservation_fee = total_amount * Decimal(str(downpayment_percent / 100))
        booking.total_amount = float(total_amount)
        booking.total_price = float(total_amount)

        db.commit()
        db.refresh(quotation)
        return quotation

    def _create_fixed_quotation(
        self, db: Session, booking: models.Booking, downpayment_percent: int, existing_quote: models.Quotation = None
    ) -> models.Quotation:
        """
        FIXED PACKAGE QUOTATION:
        Uses fixed package name, fixed inclusions, fixed pricing, guest count, and total amount
        configured by the caterer.
        Does NOT mix with customizable selections logic.
        """
        package = booking.package
        package_details = None
        base_amount = Decimal("0.0")
        actual_unit_price = Decimal("0.0")

        if package:
            # Determine actual package price (prioritize price_per_head over legacy price)
            raw_unit_price = getattr(package, 'price_per_head', None) or getattr(package, 'price', 0) or 0
            actual_unit_price = Decimal(str(raw_unit_price))

            # Base calculation:
            p_mode = getattr(package, 'pricing_mode', 'per_pax')
            p_unit = getattr(package, 'price_unit', 'per_guest')

            if p_mode == 'fixed' or p_unit != 'per_guest':
                base_amount = Decimal(str(package.price or raw_unit_price))
                # Excess guests beyond package min_guests
                min_guests = getattr(package, 'min_guests', 0) or 0
                add_price = Decimal(str(getattr(package, 'additional_guest_price', 0) or 0))
                if booking.guest_count and booking.guest_count > min_guests and add_price > 0:
                    base_amount += Decimal(str(booking.guest_count - min_guests)) * add_price
            else:
                base_amount = actual_unit_price * Decimal(str(booking.guest_count or 1))

            package_details = {
                "package_type": "fixed",
                "name": package.name,
                "description": getattr(package, 'description', ''),
                "unit_price": float(actual_unit_price),
                "guest_count": booking.guest_count,
                "base_amount": float(base_amount),
                "pricing_mode": p_mode,
                "price_unit": p_unit
            }

        # Calculate add-ons from BookingMenuItem
        addons = []
        addon_total = Decimal("0.0")

        from ..db.models import BookingMenuItem
        booking_items = db.query(BookingMenuItem).filter(
            BookingMenuItem.booking_id == booking.id
        ).all()

        for item in booking_items:
            # Skip items already accounted for in the package base amount, UNLESS they have an upgrade fee (price > 0)
            if package and not getattr(item, 'is_add_on', False) and getattr(item, 'price', 0) <= 0:
                continue

            qty = getattr(item, 'quantity', 1) or 1
            unit_price = Decimal(str(getattr(item, 'price', 0) or 0))
            price = unit_price * Decimal(str(qty))

            name = "Item"
            category = "other"
            item_id = None
            if getattr(item, 'menu_item', None):
                name = item.menu_item.name
                item_id = item.menu_item_id
                category = "food"
            elif getattr(item, 'equipment', None):
                name = item.equipment.name
                item_id = item.equipment_id
                category = "equipment"
            elif getattr(item, 'service', None):
                name = item.service.name
                item_id = item.service_id
                category = "service"

            addons.append({
                "id": item_id,
                "name": name,
                "price": float(price),
                "unit_price": float(unit_price),
                "quantity": qty,
                "category": category
            })
            addon_total += price

        if getattr(booking, 'travel_fee', 0) and booking.travel_fee > 0:
            addons.append({
                "id": "travel_fee",
                "name": "Delivery & Travel Fee",
                "price": float(booking.travel_fee),
                "unit_price": float(booking.travel_fee),
                "quantity": 1,
                "category": "fee"
            })
            addon_total += Decimal(str(booking.travel_fee))

        total_amount = base_amount + addon_total

        # Accept deposit choices from 30% to 100% in 10% increments.
        if downpayment_percent not in range(30, 101, 10):
            downpayment_percent = 30

        if existing_quote:
            existing_quote.package_details = package_details or {}
            existing_quote.addons = addons
            existing_quote.total_amount = float(total_amount)
            existing_quote.downpayment_percent = downpayment_percent
            quotation = existing_quote
        else:
            quotation = models.Quotation(
                booking_id=booking.id,
                package_details=package_details or {},
                addons=addons,
                total_amount=float(total_amount),
                downpayment_percent=downpayment_percent,
                status="draft"
            )
            db.add(quotation)

        db.flush()

        booking.expires_at = datetime.now() + timedelta(hours=24)
        booking.reservation_fee = total_amount * Decimal(str(downpayment_percent / 100))
        booking.total_amount = float(total_amount)

        db.commit()
        db.refresh(quotation)
        return quotation

    def get_quotation_by_booking(self, db: Session, booking_id: int) -> models.Quotation:
        return db.query(models.Quotation).filter(models.Quotation.booking_id == booking_id).first()

quotation_service = QuotationService()
