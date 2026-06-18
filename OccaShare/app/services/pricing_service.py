from sqlalchemy.orm import Session
from ..db.models import MenuItem, CateringPackage

class PricingService:
    @staticmethod
    def calculate_menu_item_cost(db: Session, menu_item_id: int):
        """
        Calculates the raw cost of a menu item based on its ingredients.
        Cost = Sum(Ingredient Unit Price * Quantity)
        """
        menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
        if not menu_item:
            return 0.0

        # Cost is now manually set directly on the menu_item (Phase 1 simplification)
        return menu_item.cost_price

    @staticmethod
    def calculate_package_cost(db: Session, package_id: int):
        """
        Calculates the raw cost of a package based on its menu items.
        Cost = Sum(MenuItem Cost Price)
        """
        package = db.query(CateringPackage).filter(CateringPackage.id == package_id).first()
        if not package:
            return 0.0

        total_ingredient_cost = 0.0
        for menu_item in package.menu_items:
            item_cost = PricingService.calculate_menu_item_cost(db, menu_item.id)
            total_ingredient_cost += item_cost
        
        # Save the total ingredient cost for the entire package (based on 1 pax assumption per menu item cost, or we assume menu item cost is per pax)
        package.ingredient_total_cost = total_ingredient_cost
        
        # Base pax for costing distribution
        base_pax = package.base_pax if package.base_pax and package.base_pax > 0 else 1
        
        # Internal Overhead Costs (Total for the event, not per pax)
        overhead = (package.labor_cost or 0) + (package.utility_cost or 0) + (package.equipment_cost or 0)
        
        # If the ingredient cost is PER PAX, total internal cost for the package is:
        # (Ingredient per pax * base pax) + overhead
        total_internal_cost_for_event = (total_ingredient_cost * base_pax) + overhead
        
        # Internal Break-even Cost per Pax
        package.internal_cost_per_pax = total_internal_cost_for_event / base_pax
        
        # The overall raw cost price (backward compatibility for existing code)
        package.cost_price = total_internal_cost_for_event
        
        # Note: We NO LONGER automatically overwrite price_per_head here to ensure strict separation.
        # The Caterer sets price_per_head manually in the UI based on the computed internal_cost_per_pax and their desired margin.
        
        db.commit()
        return package.internal_cost_per_pax

    @staticmethod
    def calculate_selling_price(cost: float, markup_type: str, markup_value: float):
        """
        Computes final price: Cost + (Markup Fixed or %)
        """
        if markup_type == 'percentage':
            return cost * (1 + (markup_value / 100))
        elif markup_type == 'fixed':
            return cost + markup_value
        return cost


