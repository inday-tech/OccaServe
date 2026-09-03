import re
import os

file_path = "templates/caterer/calendar.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update Booking Details Modal HTML
new_event_modal = """<!-- EVENT DETAILS MODAL -->
<div id="eventModal" class="occ-modal-overlay">
    <div class="occ-modal-box sz-md occ-content-pop">
        <div class="occ-modal-header glass-header" style="flex-direction: column; align-items: flex-start; padding-bottom: 0;">
            <div style="display: flex; justify-content: space-between; width: 100%; margin-bottom: 12px;">
                <h3 id="calModalTitle" class="occ-modal-title" style="font-size: 1.25rem;">Booking #<span id="detBookingId">--</span></h3>
                <button onclick="closeModal('eventModal')" class="occ-modal-close" title="Close" aria-label="Close modal"><i class="fas fa-times"></i></button>
            </div>
            <div style="display: flex; gap: 8px; margin-bottom: 16px;">
                <span id="detBookingStatusBadge" class="ps-badge-confirmed" style="padding: 4px 10px; font-size: 0.8rem; font-weight: 700; border-radius: 12px;"><i class="fas fa-circle" style="font-size: 0.5rem; margin-right: 4px;"></i> Confirmed</span>
                <span id="detPaymentStatusBadge" class="ps-badge-payment" style="padding: 4px 10px; font-size: 0.8rem; font-weight: 700; border-radius: 12px;"><i class="fas fa-money-bill" style="margin-right: 4px;"></i> Unpaid</span>
            </div>
            <div class="occ-modal-subtitle" style="font-size: 0.95rem; font-weight: 600; color: #334155; margin-bottom: 16px;">
                <span id="detEventHeader">Wedding • September 15, 2026 • 5:00 PM</span>
            </div>
        </div>
        
        <div class="compact-body" style="background: #f1f5f9; padding: 1.25rem;">
            <!-- Next Action Banner -->
            <div id="nextActionBanner" style="background: white; border-left: 4px solid var(--primary-color); border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="display: flex; gap: 12px; align-items: flex-start;">
                    <i class="fas fa-bell" style="color: var(--primary-color); margin-top: 2px;"></i>
                    <div style="flex: 1;">
                        <div style="font-weight: 800; color: #0f172a; margin-bottom: 4px; font-size: 0.9rem;">Next Action</div>
                        <div id="nextActionText" style="color: #475569; font-size: 0.85rem; margin-bottom: 12px;">Collect remaining balance of ₱0.00.</div>
                        <button id="nextActionButton" onclick="sendPaymentReminder()" class="btn-primary-pro" style="padding: 6px 12px; font-size: 0.75rem; border-radius: 6px;">Send Payment Reminder</button>
                    </div>
                </div>
            </div>

            <div class="calendar-detail-list" style="background: white; border: none; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                
                <!-- Customer Section -->
                <div style="padding: 1rem 1.25rem; border-bottom: 1px solid #e2e8f0;">
                    <h5 style="margin: 0 0 12px 0; font-size: 0.9rem; color: #0f172a; font-weight: 800;"><i class="fas fa-user" style="color: #64748b; margin-right: 8px;"></i> Customer</h5>
                    <div id="detCustomer" style="font-weight: 700; color: #1e293b; margin-bottom: 4px;">---</div>
                    <div id="detCustomerType" style="font-size: 0.8rem; color: #64748b; font-weight: 600; margin-bottom: 8px;">Walk-in Customer</div>
                    <div style="font-size: 0.85rem; color: #475569; display: flex; flex-direction: column; gap: 4px;">
                        <div><i class="fas fa-phone" style="width: 16px; text-align: center; color: #94a3b8;"></i> <span id="detCustomerPhone">---</span></div>
                        <div><i class="fas fa-envelope" style="width: 16px; text-align: center; color: #94a3b8;"></i> <span id="detCustomerEmail">---</span></div>
                    </div>
                </div>

                <!-- Event Section -->
                <div style="padding: 1rem 1.25rem; border-bottom: 1px solid #e2e8f0;">
                    <h5 style="margin: 0 0 12px 0; font-size: 0.9rem; color: #0f172a; font-weight: 800;"><i class="fas fa-calendar-alt" style="color: #64748b; margin-right: 8px;"></i> Event Details</h5>
                    <div style="font-weight: 700; color: #1e293b; margin-bottom: 4px;" id="detType">---</div>
                    <div style="font-weight: 600; color: var(--primary-color); margin-bottom: 8px; font-size: 0.9rem;" id="detPackage">---</div>
                    <div style="font-size: 0.85rem; color: #475569; display: flex; flex-direction: column; gap: 4px;">
                        <div><i class="fas fa-users" style="width: 16px; text-align: center; color: #94a3b8;"></i> <span id="detGuests">---</span></div>
                        <div><i class="fas fa-map-marker-alt" style="width: 16px; text-align: center; color: #94a3b8;"></i> <span id="detVenue">---</span></div>
                    </div>
                </div>

                <!-- Payment Section -->
                <div style="padding: 1rem 1.25rem; border-bottom: 1px solid #e2e8f0;">
                    <h5 style="margin: 0 0 12px 0; font-size: 0.9rem; color: #0f172a; font-weight: 800;"><i class="fas fa-wallet" style="color: #64748b; margin-right: 8px;"></i> Payment</h5>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 0.85rem; color: #475569;">
                        <span>Total</span> <span style="font-weight: 700; color: #0f172a;" id="detTotal">₱0.00</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 0.85rem; color: #475569;">
                        <span>Paid</span> <span style="font-weight: 700; color: var(--success-bg, #10b981);" id="detPaid">₱0.00</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding-top: 8px; border-top: 1px dashed #cbd5e1; font-size: 0.95rem;">
                        <span style="font-weight: 700; color: #0f172a;">Balance</span> <span style="font-weight: 800; color: #b91c1c;" id="detBalance">₱0.00</span>
                    </div>
                    <div style="margin-top: 12px; display: flex; gap: 8px;">
                        <button onclick="recordOfflinePayment()" class="btn-secondary-pro" style="flex: 1; padding: 6px; font-size: 0.75rem;"><i class="fas fa-cash-register"></i> Record Payment</button>
                        <button onclick="sendPaymentLink()" class="btn-secondary-pro" style="flex: 1; padding: 6px; font-size: 0.75rem;"><i class="fas fa-link"></i> Send Link</button>
                    </div>
                </div>

                <!-- Preparation Section -->
                <div style="padding: 1rem 1.25rem;">
                    <h5 style="margin: 0 0 12px 0; font-size: 0.9rem; color: #0f172a; font-weight: 800;"><i class="fas fa-tasks" style="color: #64748b; margin-right: 8px;"></i> Preparation</h5>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-weight: 700; color: #1e293b; font-size: 0.9rem;" id="detPrepStatus">Not Started</div>
                            <div style="font-size: 0.8rem; color: #64748b;" id="detPrepDate">Scheduled: ---</div>
                        </div>
                        <button onclick="managePreparation()" class="btn-primary-pro" style="padding: 6px 12px; font-size: 0.75rem; border-radius: 6px;">Manage Preparation</button>
                    </div>
                </div>

            </div>
        </div>
        <div class="occ-modal-footer" style="display: flex; justify-content: space-between; gap: 12px; padding: 1.25rem;">
            <input type="hidden" id="evModalBookingId">
            <button onclick="window.location.href='/caterer/dashboard?page=bookings'" class="btn-secondary-pro" style="flex: 1;"><i class="fas fa-edit"></i> Edit Booking</button>
            <button onclick="setReminder()" class="btn-secondary-pro" style="flex: 1;"><i class="fas fa-bell"></i> Reminder</button>
            <button onclick="closeModal('eventModal')" class="btn-secondary-pro" style="width: auto; px-4">Close</button>
        </div>
    </div>
</div>"""

event_modal_pattern = re.compile(r'<!-- EVENT DETAILS MODAL -->.*?</div>\s*</div>\s*</div>', re.DOTALL)
content = event_modal_pattern.sub(new_event_modal, content)

# 2. Update Walk-in Wizard HTML
new_walkin_modal = """<!-- WALK-IN BOOKING MODAL -->
<div id="manualBookingModal" class="occ-modal-overlay">
    <div class="occ-modal-box sz-lg occ-content-pop" style="display: flex; flex-direction: column; max-height: 90vh; overflow: hidden;">
        <div class="occ-modal-header glass-header" style="flex-shrink: 0; z-index: 10;">
            <div>
                <h3 class="occ-modal-title"><i class="fas fa-calendar-check"></i> Walk-in Booking</h3>
                <div class="occ-modal-subtitle">Follow the steps below to register a new offline booking</div>
            </div>
            <button type="button" onclick="closeModal('manualBookingModal')" class="occ-modal-close"><i class="fas fa-times"></i></button>
        </div>

        <style>
            .booking-stepper-pro { position: relative; padding: 1.5rem 1rem; background: #f8fafc; border-bottom: 1px solid #e2e8f0; flex-shrink: 0; z-index: 5; }
            .stepper-track-pro { position: absolute; top: 38px; left: 2.5rem; right: 2.5rem; height: 3px; background: #e2e8f0; z-index: 1; }
            .progress-fill-pro { height: 100%; background: var(--primary-color); transition: width 0.3s ease; }
            .stepper-steps-pro { position: relative; display: flex; justify-content: space-between; z-index: 2; padding: 0 0.5rem; }
            .step-pro { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; width: 60px; }
            .step-dot { width: 30px; height: 30px; background: white; border: 3px solid #e2e8f0; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 800; color: #94a3b8; transition: all 0.3s; }
            .step-label { font-size: 0.6rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; text-align: center; white-space: nowrap; }
            .step-pro.active .step-dot { border-color: var(--primary-color); color: var(--primary-color); transform: scale(1.1); }
            .step-pro.active .step-label { color: var(--primary-color); }
            .step-pro.completed .step-dot { background: var(--primary-color); border-color: var(--primary-color); color: white; }
            .step-pro.completed .step-label { color: #334155; }
            .step-content { display: none; animation: slideInRight 0.3s ease-out; }
            .step-content.active { display: block; }
            .btn-step { border-radius: 8px; padding: 10px 24px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; font-weight: 700; transition: all 0.2s; }
            @media (max-width: 768px) { .btn-step .step-btn-text { display: none; } .btn-step { width: 50px; height: 50px; padding: 0; border-radius: 50%; } }
        </style>

        <form id="manualBookingForm" onsubmit="submitManualEvent(event)" style="display: flex; flex-direction: column; flex: 1; min-height: 0;">
            
            <div class="booking-stepper-pro">
                <div class="stepper-track-pro">
                    <div class="progress-fill-pro" id="stepProgress" style="width: 0%;"></div>
                </div>
                <div class="stepper-steps-pro">
                    <div class="step-pro active" id="step-nav-1"><div class="step-dot">1</div><div class="step-label">Event</div></div>
                    <div class="step-pro" id="step-nav-2"><div class="step-dot">2</div><div class="step-label">Package</div></div>
                    <div class="step-pro" id="step-nav-3"><div class="step-dot">3</div><div class="step-label">Customer</div></div>
                    <div class="step-pro" id="step-nav-4"><div class="step-dot">4</div><div class="step-label">Payment</div></div>
                    <div class="step-pro" id="step-nav-5"><div class="step-dot">5</div><div class="step-label">Review</div></div>
                </div>
            </div>

            <div class="compact-body" style="padding: 1.5rem; flex: 1; overflow-y: auto;">
                <div id="manualBookingFormError" style="display: none; background: #fef2f2; border: 1px solid #fecaca; color: #ef4444; padding: 12px 16px; border-radius: 8px; margin-bottom: 1.5rem; font-weight: 600; font-size: 0.9rem; align-items: center; gap: 8px;"></div>

                <!-- STEP 1: EVENT DETAILS -->
                <div class="step-content active" id="step-1">
                    <h4 style="font-size: 1.25rem; font-weight: 800; color: #0f172a; margin-bottom: 1.5rem;">Step 1: Event Information</h4>
                    <div class="occ-form-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem;">
                        <div class="form-group-pro">
                            <label>Event Type <span style="color: #ef4444;">*</span></label>
                            <select id="manEventType" name="event_type" class="control-pro" required onchange="toggleOtherEventType(); validateEventType()">
                                <option value="" disabled selected>Select Type</option>
                                <option value="Wedding">Wedding</option>
                                <option value="Birthday">Birthday</option>
                                <option value="Debut">Debut</option>
                                <option value="Christening">Christening</option>
                                <option value="Corporate">Corporate Event</option>
                                <option value="Reunion">Reunion</option>
                                <option value="Fiesta">Fiesta</option>
                                <option value="Other">Other</option>
                            </select>
                            <div class="field-error-msg" id="error-manEventType"></div>
                        </div>
                        <div class="form-group-pro">
                            <label>Event Name <span style="color: #ef4444;">*</span></label>
                            <input type="text" id="manEventName" name="event_name" class="control-pro" placeholder="e.g. Maria's 18th Birthday" required oninput="validateEventName()">
                            <div class="field-error-msg" id="error-manEventName"></div>
                        </div>
                        <div id="otherEventTypeDiv" class="form-group-pro" style="display: none; grid-column: span 2;">
                            <label>Specify Event Type <span style="color: #ef4444;">*</span></label>
                            <input type="text" id="manOtherType" class="control-pro" oninput="validateOtherType()">
                            <div class="field-error-msg" id="error-manOtherType"></div>
                        </div>
                        
                        <div class="form-group-pro">
                            <label>Event Date <span style="color: #ef4444;">*</span></label>
                            <input type="date" id="manDate" name="event_date" class="control-pro" required min="{{ min_booking_date.strftime('%Y-%m-%d') }}" max="{{ max_booking_date.strftime('%Y-%m-%d') }}" onchange="validateEventDate(); checkDateConflict(this.value)">
                            <div class="field-error-msg" id="error-manDate"></div>
                        </div>
                        <div class="form-group-pro">
                            <label>Event Time <span style="color: #ef4444;">*</span></label>
                            <input type="time" id="manTime" name="event_time" class="control-pro" required min="{{ business_open }}" max="{{ business_close }}" onchange="validateEventTime()">
                            <div class="field-error-msg" id="error-manTime"></div>
                        </div>
                        
                        <div class="form-group-pro" style="grid-column: span 2;">
                            <label>Number of Guests (Pax) <span style="color: #ef4444;">*</span></label>
                            <input type="number" id="manGuests" name="guest_count" class="control-pro" required min="{{ min_pax }}" placeholder="Enter estimated number of guests (Min {{ min_pax }})" oninput="validateGuestCount()">
                            <div class="field-error-msg" id="error-manGuests"></div>
                        </div>
                    </div>
                    
                    <h5 style="font-size: 1rem; font-weight: 700; color: #334155; margin: 1.5rem 0 1rem 0; border-top: 1px solid #e2e8f0; padding-top: 1.5rem;">Venue Details</h5>
                    <div class="occ-form-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem;">
                        <div class="form-group-pro">
                            <label>Province <span style="color: #ef4444;">*</span></label>
                            <select id="manProvince" class="control-pro" required onchange="validateProvince()">
                                <option value="" disabled selected>Select Province</option>
                            </select>
                            <input type="hidden" id="manProvinceText" name="province">
                            <div class="field-error-msg" id="error-manProvince"></div>
                        </div>
                        <div class="form-group-pro">
                            <label>Municipality / City <span style="color: #ef4444;">*</span></label>
                            <select id="manMunicipality" class="control-pro" required onchange="validateMunicipality()">
                                <option value="" disabled selected>Municipality / City</option>
                            </select>
                            <input type="hidden" id="manMunicipalityText" name="municipality">
                            <div class="field-error-msg" id="error-manMunicipality"></div>
                        </div>
                        <div class="form-group-pro">
                            <label>Barangay <span style="color: #ef4444;">*</span></label>
                            <select id="manBarangay" class="control-pro" required onchange="validateBarangay()">
                                <option value="" disabled selected>Barangay</option>
                            </select>
                            <input type="hidden" id="manBarangayText" name="barangay">
                            <div class="field-error-msg" id="error-manBarangay"></div>
                        </div>
                        <div class="form-group-pro">
                            <label>Venue Name / Landmark <span style="color: #ef4444;">*</span></label>
                            <input type="text" id="manLandmark" name="landmark" class="control-pro" required placeholder="e.g. ABC Resort, 123 Main St">
                        </div>
                    </div>
                </div>

                <!-- STEP 2: QUOTATION BUILDER -->
                <div class="step-content" id="step-2">
                    <h4 style="font-size: 1.25rem; font-weight: 800; color: #0f172a; margin-bottom: 0.5rem;">Step 2: Package & Menu</h4>
                    <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 1.5rem;">Select the booking package and review the quotation.</p>
                    
                    <div class="form-group-pro" style="margin-bottom: 1.5rem;">
                        <label>Base Package / Booking Type <span style="color: #ef4444;">*</span></label>
                        <select id="manPackageMode" class="control-pro" onchange="initializeQuotation()">
                            <option value="custom">Fully Custom Booking (Start from scratch)</option>
                            <optgroup label="Fixed Packages">
                                {% for pkg in packages %}
                                <option value="{{ pkg.id }}" data-price="{{ pkg.price or 0 }}" data-unit="{{ pkg.price_unit or 'fixed' }}" data-name="{{ pkg.name }}">{{ pkg.name }}</option>
                                {% endfor %}
                            </optgroup>
                        </select>
                    </div>

                    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; margin-bottom: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.02);">
                        <div style="background: #f8fafc; padding: 12px 16px; border-bottom: 1px solid #e2e8f0; font-weight: 800; color: #334155; font-size: 0.9rem; display: flex; justify-content: space-between; align-items: center;">
                            <span><i class="fas fa-list-ul"></i> Itemized Breakdown</span>
                        </div>
                        <div style="overflow-x: auto;">
                            <table style="width: 100%; text-align: left; border-collapse: collapse; min-width: 500px;">
                                <thead style="background: #f1f5f9; border-bottom: 2px solid #e2e8f0;">
                                    <tr>
                                        <th style="padding: 12px 16px; font-size: 0.75rem; color: #64748b; text-transform: uppercase;">Description</th>
                                        <th style="padding: 12px 16px; font-size: 0.75rem; color: #64748b; text-transform: uppercase; width: 80px;">Qty</th>
                                        <th style="padding: 12px 16px; font-size: 0.75rem; color: #64748b; text-transform: uppercase; width: 120px;">Unit Price (₱)</th>
                                        <th style="padding: 12px 16px; font-size: 0.75rem; color: #64748b; text-transform: uppercase; width: 120px; text-align: right;">Amount (₱)</th>
                                        <th style="padding: 12px; width: 50px;"></th>
                                    </tr>
                                </thead>
                                <tbody id="quotationItems"></tbody>
                                <tfoot style="border-top: 2px solid #e2e8f0;">
                                    <tr>
                                        <td colspan="5" style="padding: 12px; text-align: center;">
                                            <button type="button" onclick="addQuotationRow('', 1, 0)" style="background: none; border: 1px dashed #cbd5e1; width: 100%; padding: 10px; border-radius: 8px; color: var(--primary-color); font-weight: 700; cursor: pointer; transition: all 0.2s;">
                                                <i class="fas fa-plus"></i> Add Line Item (e.g., Extra Pax, Setup Fee)
                                            </button>
                                        </td>
                                    </tr>
                                    <tr style="background: #f8fafc;">
                                        <td colspan="3" style="padding: 12px 16px; text-align: right; font-weight: 700; color: #475569;">Subtotal</td>
                                        <td colspan="2" style="padding: 12px 16px; text-align: right; font-weight: 800; font-size: 1.1rem; color: #0f172a;" id="quoteSubtotal">₱0.00</td>
                                    </tr>
                                    <tr>
                                        <td colspan="3" style="padding: 12px 16px; text-align: right; font-weight: 700; color: #ef4444; vertical-align: middle;">Discount / Adjustment</td>
                                        <td colspan="2" style="padding: 12px 16px; text-align: right;">
                                            <input type="number" id="quoteDiscount" class="control-pro" style="text-align: right; padding: 6px 12px; height: auto; max-width: 140px; margin-left: auto;" value="0" min="0" oninput="calculateQuotationTotal()">
                                        </td>
                                    </tr>
                                    <tr style="background: #f0f9ff; border-top: 2px solid #bae6fd;">
                                        <td colspan="3" style="padding: 16px; text-align: right; font-weight: 800; color: #0369a1; font-size: 1.1rem;">Total Required Payment</td>
                                        <td colspan="2" style="padding: 16px; text-align: right; font-weight: 900; color: #0369a1; font-size: 1.25rem;" id="quoteTotal">₱0.00</td>
                                        <input type="hidden" id="manAmount" name="total_amount">
                                    </tr>
                                </tfoot>
                            </table>
                        </div>
                    </div>
                    <div class="form-group-pro">
                        <label>Special Requests & Notes</label>
                        <textarea id="manSpecialNotes" name="special_notes" class="control-pro" rows="2" placeholder="Dietary restrictions, venue instructions, etc..."></textarea>
                    </div>
                </div>

                <!-- STEP 3: CUSTOMER INFO -->
                <div class="step-content" id="step-3">
                    <h4 style="font-size: 1.25rem; font-weight: 800; color: #0f172a; margin-bottom: 0.5rem;">Step 3: Customer Information</h4>
                    <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 1.5rem;">Enter contact details for the walk-in customer.</p>
                    
                    <div class="occ-form-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-bottom: 1.5rem;">
                        <div class="form-group-pro">
                            <label>First Name <span style="color: #ef4444;">*</span></label>
                            <input type="text" id="manFirstName" name="first_name" class="control-pro" required oninput="validateFirstName()">
                            <div class="field-error-msg" id="error-manFirstName"></div>
                        </div>
                        <div class="form-group-pro">
                            <label>Last Name <span style="color: #ef4444;">*</span></label>
                            <input type="text" id="manLastName" name="last_name" class="control-pro" required oninput="validateLastName()">
                            <div class="field-error-msg" id="error-manLastName"></div>
                        </div>
                        
                        <div class="form-group-pro">
                            <label>Contact Number <span style="color: #ef4444;">*</span></label>
                            <input type="text" id="manCustContact" name="customer_contact" class="control-pro" required placeholder="09XX XXX XXXX" oninput="validateContact()">
                            <div class="field-error-msg" id="error-manCustContact"></div>
                        </div>
                        <div class="form-group-pro">
                            <label>Email Address <span style="color: #64748b; font-weight:normal; font-size: 0.8rem;">(Highly Recommended)</span></label>
                            <input type="email" id="manCustEmail" name="customer_email" class="control-pro" placeholder="Required for digital links/reminders" oninput="validateEmail()">
                            <div class="field-error-msg" id="error-manCustEmail"></div>
                            <small id="emailWarning" style="color: #f59e0b; font-size: 0.75rem; font-weight: 600; margin-top: 4px; display: none;"><i class="fas fa-exclamation-triangle"></i> No email provided. Automated reminders and digital payment links will be disabled.</small>
                        </div>

                        <div class="form-group-pro" style="grid-column: span 2;">
                            <label>Customer Type</label>
                            <select id="manBookingSource" name="booking_source" class="control-pro" required>
                                <option value="Walk-in" selected>Walk-in Guest (In-Person)</option>
                                <option value="Phone Call">Phone Call / SMS</option>
                                <option value="Facebook">Facebook / Messenger</option>
                            </select>
                        </div>
                    </div>
                </div>
                
                <!-- STEP 4: PAYMENT & TERMS -->
                <div class="step-content" id="step-4">
                    <h4 style="font-size: 1.25rem; font-weight: 800; color: #0f172a; margin-bottom: 0.5rem;">Step 4: Payment & Terms</h4>
                    <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 1.5rem;">Record the initial deposit and calculate the remaining balance.</p>
                    
                    <div class="occ-form-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem;">
                        <div class="form-group-pro" style="grid-column: span 2;">
                            <label>Booking Total</label>
                            <div id="manTotalDisplay4" style="padding: 0.85rem 1rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; font-weight: 700; color: #0f172a; font-size: 1.2rem;">₱0.00</div>
                        </div>
                        <div class="form-group-pro">
                            <label>Initial Deposit Received <span style="color: #ef4444;">*</span></label>
                            <input type="number" id="manAmountPaid" name="amount_paid" class="control-pro" value="0" min="0" oninput="calculateBalance()">
                            <small style="color: #64748b; font-size: 0.75rem;">Enter 0 if no payment received yet.</small>
                        </div>
                        <div class="form-group-pro">
                            <label>Remaining Balance</label>
                            <div id="manBalanceDisplay" style="padding: 0.85rem 1rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; font-weight: 700; color: #ef4444; font-size: 1.1rem;">₱0.00</div>
                            <input type="hidden" id="manBalance" name="balance" value="0">
                        </div>
                        <div class="form-group-pro">
                            <label>Payment Method (Deposit)</label>
                            <select id="manPaymentMethod" name="payment_method" class="control-pro">
                                <option value="None" selected>None yet</option>
                                <option value="Cash">Cash</option>
                                <option value="GCash">GCash / Maya</option>
                                <option value="Bank Transfer">Bank Transfer</option>
                            </select>
                        </div>
                        <div class="form-group-pro">
                            <label>Calculated Payment Status</label>
                            <select id="manPaymentStatus" name="payment_status" class="control-pro" readonly style="background-color: #f1f5f9; pointer-events: none;">
                                <option value="unpaid" selected>Unpaid</option>
                                <option value="partially_paid">Partially Paid</option>
                                <option value="fully_paid">Fully Paid</option>
                            </select>
                        </div>
                    </div>
                </div>

                <!-- STEP 5: SUMMARY & CONFIRMATION -->
                <div class="step-content" id="step-5">
                    <h4 style="font-size: 1.25rem; font-weight: 800; color: #0f172a; margin-bottom: 1.5rem;">Step 5: Review Booking</h4>
                    
                    <div class="summary-box" style="margin-bottom: 1.5rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.5rem;">
                        <h5 style="margin: 0 0 1rem 0; font-size: 1rem; color: #334155;"><i class="fas fa-file-invoice"></i> Booking Overview</h5>
                        <div style="display: flex; justify-content: space-between; padding: 0.75rem 0; border-bottom: 1px dashed #cbd5e1;">
                            <span style="color: #64748b; font-weight: 600; font-size: 0.85rem;">Client Name</span>
                            <span style="color: #0f172a; font-weight: 700; font-size: 0.9rem;" id="sumClientName">-</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 0.75rem 0; border-bottom: 1px dashed #cbd5e1;">
                            <span style="color: #64748b; font-weight: 600; font-size: 0.85rem;">Event</span>
                            <span style="color: #0f172a; font-weight: 700; font-size: 0.9rem;" id="sumEventDetails">-</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 0.75rem 0; border-bottom: 1px dashed #cbd5e1;">
                            <span style="color: #64748b; font-weight: 600; font-size: 0.85rem;">Venue</span>
                            <span style="color: #0f172a; font-weight: 700; font-size: 0.9rem;" id="sumVenue">-</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 0.75rem 0; border-bottom: 1px dashed #cbd5e1;">
                            <span style="color: #64748b; font-weight: 600; font-size: 0.85rem;">Package</span>
                            <span style="color: #0f172a; font-weight: 700; font-size: 0.9rem;" id="sumPackage">-</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; border-top: 2px solid #cbd5e1; padding-top: 1rem; margin-top: 0.5rem;">
                            <span style="font-size: 1.1rem; color: #0f172a; font-weight: 600;">Booking Total</span>
                            <span id="sumTotalAmount" style="font-size: 1.3rem; color: #0f172a; font-weight: 700;">₱0.00</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding-top: 0.5rem;">
                            <span style="color: #64748b; font-weight: 600; font-size: 0.85rem;">Deposit Paid</span>
                            <span id="sumDepositPaid" style="color: var(--primary-color); font-weight: 700;">₱0.00</span>
                        </div>
                        <div style="background: #fef2f2; padding: 1rem; border-radius: 8px; margin-top: 1rem; display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 1.1rem; color: #b91c1c; font-weight: 800;">Remaining Balance</span>
                            <span id="sumBalanceFinal" style="font-size: 1.5rem; color: #b91c1c; font-weight: 900;">₱0.00</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="occ-modal-footer" style="flex-shrink: 0; padding: 1.25rem 2rem; background: #fff; border-top: 1px solid #e2e8f0; display: flex; justify-content: center; gap: 1.5rem; box-shadow: 0 -4px 10px rgba(0,0,0,0.02);">
                <button type="button" id="btnPrevStep" class="btn-secondary-pro btn-step" style="visibility: hidden;" onclick="changeStep(-1)" title="Go Back">
                    <i class="fas fa-arrow-left"></i> <span class="step-btn-text">Previous</span>
                </button>
                <button type="button" id="btnNextStep" class="btn-primary-pro btn-step" onclick="changeStep(1)" title="Next Step">
                    <span class="step-btn-text">Next Step</span> <i class="fas fa-arrow-right"></i>
                </button>
                <button type="submit" id="btnSubmitManual" class="btn-primary-pro btn-step" style="display:none; background: var(--success-bg, #10b981); border-color: var(--success-bg, #10b981);" title="Submit Booking">
                    <span class="step-btn-text">Create Walk-in Booking</span> <i class="fas fa-check"></i>
                </button>
            </div>
        </form>
    </div>
</div>"""

walkin_modal_pattern = re.compile(r'<!-- WALK-IN BOOKING MODAL -->.*?</div>\s*</div>\s*<script>', re.DOTALL)
content = walkin_modal_pattern.sub(new_walkin_modal + "\n\n<script>", content)

# 3. Fix JS logic for totalSteps = 5, calculateBalance payment status update, and sum updates
js_fixes = [
    ("const totalSteps = 4;", "const totalSteps = 5;"),
    (
        "const statusSelect = document.getElementById('manPaymentStatus');\\s*if \\(paid === 0\\) {\\s*statusSelect\\.value = 'pending';\\s*} else if \\(paid >= total && total > 0\\) {\\s*statusSelect\\.value = 'paid';\\s*} else {\\s*statusSelect\\.value = 'deposit_paid';\\s*}",
        "const statusSelect = document.getElementById('manPaymentStatus');\n        if (paid === 0) {\n            statusSelect.value = 'unpaid';\n        } else if (paid >= total && total > 0) {\n            statusSelect.value = 'fully_paid';\n        } else {\n            statusSelect.value = 'partially_paid';\n        }\n        document.getElementById('manTotalDisplay4').textContent = '₱' + total.toLocaleString('en-US', {minimumFractionDigits:2});"
    ),
    (
        "document.getElementById\\('manCustEmail'\\).addEventListener\\('input'",
        """document.getElementById('manCustEmail').addEventListener('input', function() {
        if (!this.value) {
            document.getElementById('emailWarning').style.display = 'block';
        } else {
            document.getElementById('emailWarning').style.display = 'none';
        }
    });
    // Fallback if not found initially"""
    )
]

for old, new in js_fixes:
    content = re.sub(old, new, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("calendar.html patched successfully.")
