import re

f = r'c:\OccaServe\OccaShare\templates\caterer\bookings.html'
with open(f, 'r', encoding='utf-8') as file:
    content = file.read()

# Add Verification Tab Button
overview_btn = """<button class="mtab-btn-pro active" onclick="switchBookingTab('overview', this)" style="padding: 1rem 1.2rem; background: transparent; border: none; border-bottom: 2px solid var(--primary-color); color: var(--primary-color); font-weight: 700; cursor: pointer; transition: all 0.2s; outline: none; font-size: 0.85rem;"><i class="fas fa-info-circle" style="margin-right: 6px;"></i>Event Overview</button>"""
verification_btn = """<button class="mtab-btn-pro" onclick="switchBookingTab('verification', this)" style="padding: 1rem 1.2rem; background: transparent; border: none; border-bottom: 2px solid transparent; color: #64748b; font-weight: 700; cursor: pointer; transition: all 0.2s; outline: none; font-size: 0.85rem;"><i class="fas fa-shield-halved" style="margin-right: 6px;"></i>Verification</button>"""

content = content.replace(overview_btn, overview_btn + "\n                " + verification_btn)

# Add Verification Tab Pane
overview_pane_start = """            <!-- Overview Tab -->"""

verification_pane = """            <!-- Verification Tab -->
            <div id="btab-verification" class="mtab-pane-pro" style="padding: 1.5rem 2rem; background: #f8fafc;">
                
                <div style="display: flex; flex-direction: column; gap: 1.5rem; max-width: 900px; margin: 0 auto;">
                    
                    <!-- Section 1: Customer Information -->
                    <div style="background: white; border-radius: var(--border-radius, 12px); border: 1px solid #e2e8f0; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                        <h4 style="margin: 0 0 1rem 0; font-size: 1.1rem; color: #1e293b; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.5rem;"><i class="fas fa-user" style="color: var(--primary-color); margin-right: 8px;"></i> Customer Information</h4>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                            <div><strong style="color:#64748b; font-size:0.8rem; text-transform:uppercase;">Full Name</strong><div id="vCustomerName" style="font-weight: 600;"></div></div>
                            <div><strong style="color:#64748b; font-size:0.8rem; text-transform:uppercase;">Contact Number</strong><div id="vCustomerContact" style="font-weight: 600;"></div></div>
                            <div><strong style="color:#64748b; font-size:0.8rem; text-transform:uppercase;">Email Address</strong><div id="vCustomerEmail" style="font-weight: 600;"></div></div>
                            <div><strong style="color:#64748b; font-size:0.8rem; text-transform:uppercase;">Delivery Address</strong><div id="vCustomerAddress" style="font-weight: 600;"></div></div>
                        </div>
                        <div style="margin-top: 1rem; display: flex; gap: 10px;">
                            <button type="button" class="btn-secondary-pro" style="padding: 6px 12px; font-size: 0.8rem;"><i class="fas fa-external-link-alt"></i> View Profile</button>
                            <button type="button" class="btn-primary-pro" style="padding: 6px 12px; font-size: 0.8rem;"><i class="fas fa-comment"></i> Contact Customer</button>
                        </div>
                    </div>

                    <!-- Section 2: Booking Information -->
                    <div style="background: white; border-radius: var(--border-radius, 12px); border: 1px solid #e2e8f0; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                        <h4 style="margin: 0 0 1rem 0; font-size: 1.1rem; color: #1e293b; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.5rem;"><i class="fas fa-calendar-alt" style="color: var(--primary-color); margin-right: 8px;"></i> Booking Information</h4>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                            <div><strong style="color:#64748b; font-size:0.8rem; text-transform:uppercase;">Booking Type</strong><div id="vBookingType" style="font-weight: 600;"></div></div>
                            <div><strong style="color:#64748b; font-size:0.8rem; text-transform:uppercase;">Event Date & Time</strong><div id="vEventDate" style="font-weight: 600;"></div></div>
                            <div><strong style="color:#64748b; font-size:0.8rem; text-transform:uppercase;">Venue</strong><div id="vVenue" style="font-weight: 600;"></div></div>
                            <div><strong style="color:#64748b; font-size:0.8rem; text-transform:uppercase;">Guest Count</strong><div id="vGuestCount" style="font-weight: 600;"></div></div>
                        </div>
                    </div>

                    <!-- Section 3: Verification Documents -->
                    <div style="background: white; border-radius: var(--border-radius, 12px); border: 1px solid #e2e8f0; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                        <h4 style="margin: 0 0 1rem 0; font-size: 1.1rem; color: #1e293b; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.5rem;"><i class="fas fa-id-card" style="color: var(--primary-color); margin-right: 8px;"></i> Verification Documents</h4>
                        <div id="vDocsContainer" style="color: #64748b; font-size: 0.9rem;">
                            No verification documents required for this booking type.
                        </div>
                    </div>

                    <!-- Section 4: Payment Verification -->
                    <div style="background: white; border-radius: var(--border-radius, 12px); border: 1px solid #e2e8f0; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                        <h4 style="margin: 0 0 1rem 0; font-size: 1.1rem; color: #1e293b; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.5rem;"><i class="fas fa-money-bill-wave" style="color: var(--primary-color); margin-right: 8px;"></i> Payment Verification</h4>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                            <div><strong style="color:#64748b; font-size:0.8rem; text-transform:uppercase;">Amount Paid</strong><div id="vAmountPaid" style="font-weight: 600;">₱0.00</div></div>
                            <div><strong style="color:#64748b; font-size:0.8rem; text-transform:uppercase;">Reference Number</strong><div id="vRefNumber" style="font-weight: 600;">N/A</div></div>
                            <div><strong style="color:#64748b; font-size:0.8rem; text-transform:uppercase;">Payment Status</strong><div id="vPaymentStatus" style="font-weight: 600;"><span class="badge" style="background: #fef3c7; color: #d97706;">Pending</span></div></div>
                        </div>
                        <div style="margin-top: 1rem; display: flex; gap: 10px;">
                            <button type="button" class="btn-primary-pro" style="background:#10b981; border:none; padding: 6px 12px; font-size: 0.8rem;"><i class="fas fa-check"></i> Approve Payment</button>
                            <button type="button" class="btn-secondary-pro" style="color:#ef4444; border-color:#ef4444; padding: 6px 12px; font-size: 0.8rem;"><i class="fas fa-times"></i> Reject Payment</button>
                        </div>
                    </div>

                    <!-- Section 5 & 6: Checklist & Internal Notes -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
                        <div style="background: white; border-radius: var(--border-radius, 12px); border: 1px solid #e2e8f0; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                            <h4 style="margin: 0 0 1rem 0; font-size: 1.1rem; color: #1e293b; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.5rem;"><i class="fas fa-tasks" style="color: var(--primary-color); margin-right: 8px;"></i> Internal Checklist</h4>
                            <div style="display: flex; flex-direction: column; gap: 8px; font-size: 0.9rem;">
                                <label style="display:flex; align-items:center; gap:8px; cursor:pointer;"><input type="checkbox"> Customer information verified</label>
                                <label style="display:flex; align-items:center; gap:8px; cursor:pointer;"><input type="checkbox"> Reservation payment received</label>
                                <label style="display:flex; align-items:center; gap:8px; cursor:pointer;"><input type="checkbox"> Event schedule available</label>
                            </div>
                        </div>
                        <div style="background: white; border-radius: var(--border-radius, 12px); border: 1px solid #e2e8f0; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                            <h4 style="margin: 0 0 1rem 0; font-size: 1.1rem; color: #1e293b; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.5rem;"><i class="fas fa-sticky-note" style="color: var(--primary-color); margin-right: 8px;"></i> Internal Notes</h4>
                            <textarea class="control-pro" rows="4" placeholder="Add private notes about this booking here..." style="width:100%; border:1px solid #e2e8f0; border-radius: 8px; padding: 8px; font-size: 0.9rem;"></textarea>
                        </div>
                    </div>

                    <!-- Section 7: Verification Decision -->
                    <div style="background: white; border-radius: var(--border-radius, 12px); border: 1px solid #e2e8f0; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02); text-align: center;">
                        <h4 style="margin: 0 0 1rem 0; font-size: 1.1rem; color: #1e293b; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.5rem;"><i class="fas fa-gavel" style="color: var(--primary-color); margin-right: 8px;"></i> Booking Decision</h4>
                        <div style="display: flex; justify-content: center; gap: 15px; margin-top: 1.5rem;">
                            <button type="button" class="btn-primary-pro" style="background: #10b981; border: none; padding: 10px 24px;"><i class="fas fa-check-circle" style="margin-right:8px;"></i> Approve Booking</button>
                            <button type="button" class="btn-secondary-pro" style="padding: 10px 24px;"><i class="fas fa-question-circle" style="margin-right:8px;"></i> Request Info</button>
                            <button type="button" class="btn-secondary-pro" style="color: #ef4444; border-color: #fca5a5; padding: 10px 24px;"><i class="fas fa-times-circle" style="margin-right:8px;"></i> Reject</button>
                        </div>
                    </div>

                </div>
            </div>\n\n"""

content = content.replace(overview_pane_start, verification_pane + overview_pane_start)

with open(f, 'w', encoding='utf-8') as out:
    out.write(content)
print('Added Verification Tab to bookings.html')
