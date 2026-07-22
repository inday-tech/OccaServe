import os
import re

backend_path = r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py'

with open(backend_path, 'r', encoding='utf-8') as f:
    backend_content = f.read()

# We'll just inject the new variables into the return dict of _get_caterer_stats
# We need to find the `return {` at the end of `_get_caterer_stats` and add the new variables
target = '''    return {
        "total_revenue": total_realized_revenue, 
        "projected_revenue": total_projected_revenue,
        "net_profit": realized_net_profit,
        "projected_profit": projected_net_profit,
        "estimated_expenses": total_projected_expenses,
        "actual_expenses": total_actual_expenses,
        "roi_percentage": round(realized_roi, 1),
        "projected_roi": round(projected_roi, 1),
        "total_customers": len(unique_customers),
        "chart_data": chart_data,
        "roi_trend_data": roi_trend_data,
        "bookings_chart_data": bookings_chart_data,
        "upcoming_events": upcoming_events,
        "popular_packages": popular_packages[:4],
        "recent_orders": sorted([b for b in bookings if b.event_date and b.event_date >= stats_start and b.event_date <= stats_end], key=lambda x: x.id, reverse=True)[:5],
        "top_spenders": top_spenders,
        "revenue_by_event": revenue_by_event_list,
        "timeframe": timeframe
    }'''

replacement = '''    
    # Calculate Pending Actions
    pending_approvals = sum(1 for b in bookings if b.status in ['pending_quotation', 'pending_review'])
    pending_payments = sum(1 for b in bookings if b.payment_status == 'pending_verification')
    identity_requests = sum(1 for b in bookings if not getattr(b.user, 'is_verified', True))
    pending_contracts = sum(1 for b in bookings if getattr(b, 'contract_status', '') == 'awaiting_signature')
    
    # Count unread messages (assuming message relation exists, or we just mock/query it, here we mock it to 0 as we don't have direct access in bookings list)
    customer_messages = 0
    for b in bookings:
        for m in getattr(b, 'messages', []):
            if not getattr(m, 'is_read', True) and getattr(m, 'sender_id') != profile.user_id:
                customer_messages += 1

    pending_actions = {
        "approvals": pending_approvals,
        "payments": pending_payments,
        "identity": identity_requests,
        "contracts": pending_contracts,
        "messages": customer_messages,
        "total": pending_approvals + pending_payments + identity_requests + pending_contracts + customer_messages
    }

    # Today's Schedule
    today_schedule = [b for b in bookings if b.event_date == today and b.status not in ['cancelled', 'draft']]
    today_schedule.sort(key=lambda x: x.event_time.hour if x.event_time else 0)
    
    return {
        "total_revenue": total_realized_revenue, 
        "projected_revenue": total_projected_revenue,
        "net_profit": realized_net_profit,
        "projected_profit": projected_net_profit,
        "estimated_expenses": total_projected_expenses,
        "actual_expenses": total_actual_expenses,
        "roi_percentage": round(realized_roi, 1),
        "projected_roi": round(projected_roi, 1),
        "total_customers": len(unique_customers),
        "chart_data": chart_data,
        "roi_trend_data": roi_trend_data,
        "bookings_chart_data": bookings_chart_data,
        "upcoming_events": upcoming_events,
        "popular_packages": popular_packages[:4],
        "recent_orders": sorted([b for b in bookings if b.event_date and b.event_date >= stats_start and b.event_date <= stats_end], key=lambda x: x.id, reverse=True)[:5],
        "top_spenders": top_spenders,
        "revenue_by_event": revenue_by_event_list,
        "timeframe": timeframe,
        "active_bookings": active_bookings,
        "upcoming_events_count": len([b for b in bookings if b.event_date and today < b.event_date <= today + timedelta(days=7)]),
        "pending_actions": pending_actions,
        "today_schedule": today_schedule
    }'''

if target in backend_content:
    backend_content = backend_content.replace(target, replacement)
    with open(backend_path, 'w', encoding='utf-8') as f:
        f.write(backend_content)
    print("Backend stats updated successfully.")
else:
    print("Could not find backend target!")
    
