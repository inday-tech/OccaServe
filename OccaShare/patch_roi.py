import re

path = 'app/routers/caterer_dashboard.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update caterer_roi_analytics
target1 = """        # Calculate stats for this month
        month_bookings = db.query(models.Booking).filter(
            models.Booking.caterer_id == user.caterer_profile.id,
            models.Booking.status == 'completed',
            func.extract('month', models.Booking.event_date) == target_month.month,
            func.extract('year', models.Booking.event_date) == target_month.year
        ).all()
        
        rev = sum(b.total_price or 0 for b in month_bookings)
        act_cost = sum(b.actual_cost or 0 for b in month_bookings)
        
        proj_cost = 0"""

replacement1 = """        # Calculate stats for this month
        month_bookings = db.query(models.Booking).filter(
            models.Booking.caterer_id == user.caterer_profile.id,
            models.Booking.status == 'completed',
            func.extract('month', models.Booking.event_date) == target_month.month,
            func.extract('year', models.Booking.event_date) == target_month.year
        ).all()
        
        config = db.query(models.WebsiteConfig).first()
        comm_rate = config.commission_rate if config else 10.0
        comm_fixed = config.commission_fixed_amount if config else 20.0

        gross_rev = sum(b.total_amount or b.total_price or 0 for b in month_bookings)
        
        total_commission = 0
        for b in month_bookings:
            b_total = b.total_amount or b.total_price or 0
            total_commission += (b_total * (comm_rate / 100.0)) + comm_fixed

        net_rev = gross_rev - total_commission

        act_cost = sum(b.actual_cost or 0 for b in month_bookings)

        month_expenses = db.query(models.BusinessExpense).filter(
            models.BusinessExpense.caterer_id == user.caterer_profile.id,
            func.extract('month', models.BusinessExpense.date_incurred) == target_month.month,
            func.extract('year', models.BusinessExpense.date_incurred) == target_month.year
        ).all()
        overhead_cost = sum(e.amount for e in month_expenses)
        
        total_act_cost = act_cost + overhead_cost
        
        proj_cost = 0"""
content = content.replace(target1, replacement1)

target1b = """        projected_revenue.append(float(rev))
        actual_costs.append(float(act_cost))"""
replacement1b = """        projected_revenue.append(float(net_rev))
        actual_costs.append(float(total_act_cost))"""
content = content.replace(target1b, replacement1b)

# 2. Update financials_page
target2 = """    monthly_expenses = sum(e.amount for e in expenses if e.date_incurred and e.date_incurred.month == current_month and e.date_incurred.year == current_year)
    total_expenses = sum(e.amount for e in expenses)
    
    return templates.TemplateResponse("caterer/financials.html", {"""
replacement2 = """    monthly_expenses = sum(e.amount for e in expenses if e.date_incurred and e.date_incurred.month == current_month and e.date_incurred.year == current_year)
    total_expenses = sum(e.amount for e in expenses)
    
    config = db.query(models.WebsiteConfig).first()
    comm_rate = config.commission_rate if config else 10.0
    comm_fixed = config.commission_fixed_amount if config else 20.0

    all_completed_bookings = db.query(models.Booking).filter(
        models.Booking.caterer_id == profile.id,
        models.Booking.status == 'completed'
    ).all()
    
    total_rev = 0
    total_event_costs = 0
    total_comm = 0
    for b in all_completed_bookings:
        amt = float(b.total_amount or b.total_price or 0)
        total_rev += amt
        total_comm += (amt * (comm_rate / 100.0)) + comm_fixed
        total_event_costs += float(b.actual_cost or 0)
        
    net_profit = (total_rev - total_comm) - (total_event_costs + total_expenses)
    
    return templates.TemplateResponse("caterer/financials.html", {"""
content = content.replace(target2, replacement2)

target2b = """        "expenses": expenses,
        "monthly_overhead": monthly_expenses,
        "total_overhead": total_expenses
    })"""
replacement2b = """        "expenses": expenses,
        "monthly_overhead": monthly_expenses,
        "total_overhead": total_expenses,
        "net_profit": net_profit
    })"""
content = content.replace(target2b, replacement2b)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Backend patched for ROI and Financials!")
