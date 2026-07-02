import sys

f = r'c:\OccaServe\OccaShare\templates\caterer\index.html'
with open(f, 'r', encoding='utf-8') as file:
    content = file.read()

target = """</div>

<div class="dashboard-main-layout">"""

replacement = """</div>

<!-- Verification Actions Row -->
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
    <a href="/caterer/bookings?filter=pending_review" style="text-decoration: none; display: block;">
        <div class="c-card-premium" style="background: white; border: 1px solid #f1f5f9; padding: 1.5rem; border-radius: 12px; border-left: 4px solid var(--accent-color); transition: all 0.2s;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h4 style="margin: 0; color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Pending Reviews</h4>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #0f172a; margin-top: 0.5rem;"><i class="fas fa-search" style="color: var(--accent-color); margin-right: 10px;"></i> Bookings Waiting</div>
                </div>
            </div>
            <p style="margin: 0.5rem 0 0 0; font-size: 0.8rem; color: #94a3b8;">Review customer details and approve bookings.</p>
        </div>
    </a>
    
    <a href="/caterer/bookings?filter=pending_payment" style="text-decoration: none; display: block;">
        <div class="c-card-premium" style="background: white; border: 1px solid #f1f5f9; padding: 1.5rem; border-radius: 12px; border-left: 4px solid #10b981; transition: all 0.2s;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h4 style="margin: 0; color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Payment Verifications</h4>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #0f172a; margin-top: 0.5rem;"><i class="fas fa-money-bill-wave" style="color: #10b981; margin-right: 10px;"></i> Awaiting Confirmation</div>
                </div>
            </div>
            <p style="margin: 0.5rem 0 0 0; font-size: 0.8rem; color: #94a3b8;">Verify uploaded reservation proofs.</p>
        </div>
    </a>
    
    <a href="/caterer/bookings?filter=pending_docs" style="text-decoration: none; display: block;">
        <div class="c-card-premium" style="background: white; border: 1px solid #f1f5f9; padding: 1.5rem; border-radius: 12px; border-left: 4px solid #f59e0b; transition: all 0.2s;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h4 style="margin: 0; color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Documents Pending Review</h4>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #0f172a; margin-top: 0.5rem;"><i class="fas fa-id-card" style="color: #f59e0b; margin-right: 10px;"></i> Awaiting Documents</div>
                </div>
            </div>
            <p style="margin: 0.5rem 0 0 0; font-size: 0.8rem; color: #94a3b8;">Review customer IDs and permits.</p>
        </div>
    </a>
</div>

<div class="dashboard-main-layout">"""

content = content.replace(target, replacement)

with open(f, 'w', encoding='utf-8') as out:
    out.write(content)
print('Updated index.html with Verification cards')
