from sqlalchemy.orm import Session
from ..db.models import Ingredient, MenuItem, CateringPackage, MenuItemIngredient

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

        total_cost = 0.0
        for mi_ingredient in menu_item.ingredients:
            # mi_ingredient is a MenuItemIngredient instance
            ingredient = mi_ingredient.ingredient
            if ingredient:
                total_cost += (ingredient.unit_price * mi_ingredient.quantity)
        
        # Update the cost_price of the menu item
        menu_item.cost_price = total_cost
        db.commit()
        return total_cost

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

    @staticmethod
    def cascade_update_from_ingredient(db: Session, ingredient_id: int):
        """
        When an ingredient price changes, update all related menu items and packages.
        """
        # Find all menu items using this ingredient
        mi_ingredients = db.query(MenuItemIngredient).filter(MenuItemIngredient.ingredient_id == ingredient_id).all()
        
        affected_menu_items = set([mi.menu_item_id for mi in mi_ingredients])
        affected_packages = set()

        # Update each menu item
        for mi_id in affected_menu_items:
            PricingService.calculate_menu_item_cost(db, mi_id)
            
            # Find packages using this menu item
            menu_item = db.query(MenuItem).filter(MenuItem.id == mi_id).first()
            if menu_item:
                for pkg in menu_item.packages:
                    affected_packages.add(pkg.id)

        # Update each package
        for pkg_id in affected_packages:
            PricingService.calculate_package_cost(db, pkg_id)
        
        return {
            "updated_menu_items": len(affected_menu_items),
            "updated_packages": len(affected_packages)
        }
