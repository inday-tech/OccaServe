import re

filepath = r'c:\OccaServe\OccaShare\templates\customer\dashboard.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace the huge stat cards with kpi-grid-clean style cards
new_stats = '''    <!-- Stat Cards (Premium Clean) -->
    <div class="kpi-grid-clean">
        <div class="kpi-card-clean">
            <div class="kpi-icon-box" style="background: rgba(249,115,22,0.1); color: #f97316;">
                <i class="fas fa-calendar-clock"></i>
            </div>
            <div class="kpi-info">
                <h4>Upcoming</h4>
                <span class="kpi-value" style="color: #f97316;">{{ upcoming_count }}</span>
            </div>
        </div>
        
        <div class="kpi-card-clean">
            <div class="kpi-icon-box" style="background: rgba(59,130,246,0.1); color: #3b82f6;">
                <i class="fas fa-receipt"></i>
            </div>
            <div class="kpi-info">
                <h4>Bookings</h4>
                <span class="kpi-value" style="color: #3b82f6;">{{ total_bookings }}</span>
            </div>
        </div>
        
        <div class="kpi-card-clean">
            <div class="kpi-icon-box" style="background: rgba(16,185,129,0.1); color: #10b981;">
                <i class="fas fa-star"></i>
            </div>
            <div class="kpi-info">
                <h4>Reviews</h4>
                <span class="kpi-value" style="color: #10b981;">{{ reviews_count }}</span>
            </div>
        </div>
        
        <div class="kpi-card-clean">
            <div class="kpi-icon-box" style="background: rgba(139,92,246,0.1); color: #8b5cf6;">
                <i class="fas fa-wallet"></i>
            </div>
            <div class="kpi-info">
                <h4>Amount Spent</h4>
                <span class="kpi-value" style="color: #8b5cf6;">?{{ "{:,.0f}".format(total_spent) }}</span>
            </div>
        </div>
    </div>'''

content = re.sub(r'<div class="stats-row">.*?</div>\s*</div>\s*</div>\s*</div>\s*</div>', new_stats, content, flags=re.DOTALL)

# 2. Add the CSS for kpi-grid-clean
css_to_add = '''
    /* KPI Cards - Admin Style */
    .kpi-grid-clean {
        display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1.25rem; margin-bottom: 1.25rem;
    }
    .kpi-card-clean {
        background: #fff; 
        padding: 1.25rem;
        border-radius: 1.25rem;
        border: 1px solid var(--dm-slate-100); 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.04);
        display: flex;
        align-items: center; gap: 1rem; 
        transition: all 0.3s ease; 
    }
    .kpi-card-clean:hover { 
        transform: translateY(-4px); 
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
        border-color: var(--primary-color);
    }
    .kpi-icon-box {
        width: 48px; height: 48px; border-radius: 12px; display: flex;
        align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0;
    }
    .kpi-info h4 {
        font-size: 0.7rem; font-weight: 700; color: var(--dm-slate-400);
        text-transform: uppercase; letter-spacing: 0.06em; margin: 0 0 0.2rem 0;
    }
    .kpi-value { font-size: 1.5rem; font-weight: 800; line-height: 1.1; display: block; }
'''
content = content.replace('/* -- STAT CARDS -- */', css_to_add + '\n    /* -- STAT CARDS -- */')

# 3. Remove "Recent Messages" panel entirely
content = re.sub(r'<!-- Recent Messages -->.*?</div>\s*</div>\s*</div>', '</div>\n</div>', content, flags=re.DOTALL)

# 4. Fix top margin for header overlap
content = content.replace('.dash-header {', '.dash-header { margin-top: 3rem;')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
