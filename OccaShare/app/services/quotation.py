from sqlalchemy.orm import Session
from ..db import models
from decimal import Decimal
from datetime import datetime, timedelta

class QuotationService:
    def create_quotation(self, db: Session, booking: models.Booking, downpayment_percent: int = 30) -> models.Quotation:
        """
        Calculates total cost and creates a Quotation record for a booking.
        """
        package = booking.package
        package_details = None
        base_amount = Decimal("0.0")
        
        if package:
            # Determine actual package price (prioritize price_per_head over legacy price)
            actual_unit_price = getattr(package, 'price_per_head', None) or getattr(package, 'price', 0)
            
            # Base calculation: actual_unit_price * guest_count (only if per_pax)
            if getattr(package, 'pricing_mode', None) == 'fixed' or getattr(package, 'price_unit', None) != 'per_guest':
                base_amount = Decimal(str(actual_unit_price))
            else:
                base_amount = Decimal(str(actual_unit_price)) * Decimal(str(booking.guest_count or 1))
            package_details = {
                "name": package.name,
                "description": getattr(package, 'description', ''),
                "unit_price": float(actual_unit_price),
                "guest_count": booking.guest_count,
                "base_amount": float(base_amount)
            }
        
        # Calculate add-ons / itemized components from BookingMenuItem
        addons = []
        addon_total = Decimal("0.0")
        
        from ..db.models import BookingMenuItem
        booking_items = db.query(BookingMenuItem).filter(
            BookingMenuItem.booking_id == booking.id
        ).all()

        for item in booking_items:
            # Skip items already accounted for in the package base amount
            if package and not getattr(item, 'is_add_on', False):
                continue
                
            qty = getattr(item, 'quantity', 1) or 1
            unit_price = Decimal(str(getattr(item, 'price', 0)))
            price = unit_price * Decimal(str(qty))
            
            # Determine the name based on which item type is attached
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

        # Note: Security deposits are tracked independently in booking.security_deposit_amount
        # to prevent them from increasing the reservation fee percentage computation.

        total_amount = base_amount + addon_total
        
        # Ensure downpayment is within 30-50%
        if not (30 <= downpayment_percent <= 50):
            downpayment_percent = 30

        quotation = models.Quotation(
            booking_id=booking.id,
            package_details=package_details or {},
            addons=addons,
            total_amount=float(total_amount),
            downpayment_percent=downpayment_percent,
            status="draft"
        )
        
        db.add(quotation)
        db.flush() # Get ID
        
        # Update booking expiration (24h)
        booking.expires_at = datetime.now() + timedelta(hours=24)
        
        # Calculate reservation fee based only on revenue totals
        booking.reservation_fee = total_amount * Decimal(str(downpayment_percent / 100))
        booking.total_amount = float(total_amount)
        
        db.commit()
        db.refresh(quotation)
        return quotation


    def get_quotation_by_booking(self, db: Session, booking_id: int) -> models.Quotation:
        return db.query(models.Quotation).filter(models.Quotation.booking_id == booking_id).first()

quotation_service = QuotationService()
