import re

with open("templates/caterer/calendar.html", "r", encoding="utf-8") as f:
    content = f.read()

start_tag = '<div id="manualBookingModal" class="occ-modal-overlay">'
end_tag = '<!-- FullCalendar JS -->'

if start_tag in content and end_tag in content:
    start_idx = content.find(start_tag)
    end_idx = content.find(end_tag)

    new_modal = """
<div id="externalBookingModal" class="occ-modal-overlay">
    <div class="occ-modal-box sz-lg occ-content-pop" style="display: flex; flex-direction: column; max-height: 90vh; overflow: hidden;">
        <div class="occ-modal-header glass-header" style="flex-shrink: 0; z-index: 10;">
            <div>
                <h3 class="occ-modal-title"><i class="fas fa-calendar-plus"></i> Add External Booking</h3>
                <div class="occ-modal-subtitle">Record an inquiry or booking from external sources (Facebook, Call, Walk-in)</div>
            </div>
            <button type="button" onclick="closeModal('externalBookingModal')" class="occ-modal-close"><i class="fas fa-times"></i></button>
        </div>

        <style>
            .booking-stepper-pro { position: relative; padding: 1.5rem; background: #f8fafc; border-bottom: 1px solid #e2e8f0; flex-shrink: 0; z-index: 5; }
            .stepper-track-pro { position: absolute; top: 38px; left: 3rem; right: 3rem; height: 3px; background: #e2e8f0; z-index: 1; }
            .progress-fill-pro { height: 100%; background: var(--primary-color); transition: width 0.3s ease; }
            .stepper-steps-pro { position: relative; display: flex; justify-content: space-between; z-index: 2; }
            .step-pro { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; width: 80px; }
            .step-dot { width: 32px; height: 32px; background: white; border: 3px solid #e2e8f0; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; font-weight: 800; color: #94a3b8; transition: all 0.3s; }
            .step-label { font-size: 0.65rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; text-align: center; }
            .step-pro.active .step-dot { border-color: var(--primary-color); color: var(--primary-color); transform: scale(1.1); }
            .step-pro.active .step-label { color: var(--primary-color); }
            .step-pro.completed .step-dot { background: var(--primary-color); border-color: var(--primary-color); color: white; }
            .step-pro.completed .step-label { color: #334155; }
            .step-content { display: none; animation: slideInRight 0.3s ease-out; }
            .step-content.active { display: block; }
        </style>

        <form id="externalBookingForm" onsubmit="submitExternalBooking(event)" style="display: flex; flex-direction: column; flex: 1; min-height: 0;">
            <div class="booking-stepper-pro">
                <div class="stepper-track-pro">
                    <div class="progress-fill-pro" id="extStepProgress" style="width: 0%;"></div>
                </div>
                <div class="stepper-steps-pro">
                    <div class="step-pro active" id="ext-nav-1"><div class="step-dot">1</div><div class="step-label">Source</div></div>
                    <div class="step-pro" id="ext-nav-2"><div class="step-dot">2</div><div class="step-label">Event</div></div>
                    <div class="step-pro" id="ext-nav-3"><div class="step-dot">3</div><div class="step-label">Package</div></div>
                    <div class="step-pro" id="ext-nav-4"><div class="step-dot">4</div><div class="step-label">Confirm</div></div>
                </div>
            </div>

            <div class="compact-body" style="padding: 1.5rem; flex: 1; overflow-y: auto;">
                <div id="extBookingFormError" style="display: none; background: #fef2f2; border: 1px solid #fecaca; color: #ef4444; padding: 12px 16px; border-radius: 8px; margin-bottom: 1.5rem; font-weight: 600; text-align: center;"></div>

                <!-- STEP 1: SOURCE & CUSTOMER -->
                <div class="step-content active" id="ext-step-1">
                    <h4 style="font-size: 1.25rem; font-weight: 800; color: #0f172a; margin-bottom: 1.5rem;">Step 1: Source & Customer</h4>
                    <div class="occ-form-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem;">
                        <div class="form-group-pro" style="grid-column: span 2;">
                            <label>Booking Source <span style="color: #ef4444;">*</span></label>
                            <select id="extSource" name="booking_source" class="control-pro" required>
                                <option value="Facebook Messenger">Facebook Messenger</option>
                                <option value="Phone Call">Phone Call</option>
                                <option value="SMS/Text">SMS / Text</option>
                                <option value="Walk-in" selected>Walk-in</option>
                                <option value="Other">Other</option>
                            </select>
                        </div>
                        <div class="form-group-pro" style="grid-column: span 2;">
                            <label>Customer Name <span style="color: #ef4444;">*</span></label>
                            <input type="text" id="extCustomerName" name="customer_name" class="control-pro" placeholder="e.g. Juan Dela Cruz" required oninput="window.clearFieldError('extCustomerName')">
                            <div class="field-error-msg" id="error-extCustomerName"></div>
                        </div>
                        <div class="form-group-pro">
                            <label>Contact Number <span style="color: #ef4444;">*</span></label>
                            <input type="text" id="extCustomerContact" name="customer_contact" class="control-pro" placeholder="e.g. 09123456789" required oninput="window.clearFieldError('extCustomerContact')">
                            <div class="field-error-msg" id="error-extCustomerContact"></div>
                        </div>
                        <div class="form-group-pro">
                            <label>Email Address</label>
                            <input type="email" id="extCustomerEmail" name="customer_email" class="control-pro" placeholder="Optional">
                        </div>
                    </div>
                </div>

                <!-- STEP 2: EVENT DETAILS -->
                <div class="step-content" id="ext-step-2">
                    <h4 style="font-size: 1.25rem; font-weight: 800; color: #0f172a; margin-bottom: 1.5rem;">Step 2: Event Details</h4>
                    <div class="occ-form-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem;">
                        <div class="form-group-pro">
                            <label>Event Type <span style="color: #ef4444;">*</span></label>
                            <select id="extEventType" name="event_type" class="control-pro" required>
                                <option value="" disabled selected>Select Type</option>
                                <option value="Wedding">Wedding</option>
                                <option value="Birthday">Birthday</option>
                                <option value="Corporate">Corporate Event</option>
                                <option value="Other">Other</option>
                            </select>
                        </div>
                        <div class="form-group-pro">
                            <label>Event Name <span style="color: #ef4444;">*</span></label>
                            <input type="text" id="extEventName" name="event_name" class="control-pro" required>
                            <div class="field-error-msg" id="error-extEventName"></div>
                        </div>
                        <div class="form-group-pro">
                            <label>Event Date <span style="color: #ef4444;">*</span></label>
                            <input type="date" id="extEventDate" name="event_date" class="control-pro" required min="{{ min_booking_date.strftime('%Y-%m-%d') }}">
                            <div class="field-error-msg" id="error-extEventDate"></div>
                        </div>
                        <div class="form-group-pro">
                            <label>Event Time <span style="color: #ef4444;">*</span></label>
                            <input type="time" id="extEventTime" name="event_time" class="control-pro" required>
                        </div>
                        <div class="form-group-pro">
                            <label>Number of Guests (Pax) <span style="color: #ef4444;">*</span></label>
                            <input type="number" id="extGuests" name="guest_count" class="control-pro" required min="1">
                        </div>
                        <div class="form-group-pro">
                            <label>Venue / Location</label>
                            <input type="text" id="extVenue" name="venue_address" class="control-pro" placeholder="e.g. ABC Resort">
                        </div>
                    </div>
                </div>

                <!-- STEP 3: PACKAGE & ADD-ONS -->
                <div class="step-content" id="ext-step-3">
                    <h4 style="font-size: 1.25rem; font-weight: 800; color: #0f172a; margin-bottom: 1.5rem;">Step 3: Package & Quotation</h4>
                    <div class="form-group-pro" style="margin-bottom: 1.5rem;">
                        <label>Base Package / Pricing <span style="color: #ef4444;">*</span></label>
                        <select id="extPackageMode" class="control-pro" onchange="calcExtTotal()">
                            <option value="custom">Manual / Custom Quotation</option>
                            <optgroup label="System Packages">
                                {% for pkg in packages %}
                                <option value="{{ pkg.id }}" data-price="{{ pkg.price or 0 }}">{{ pkg.name }} (₱{{ pkg.price or 0 }})</option>
                                {% endfor %}
                            </optgroup>
                        </select>
                    </div>

                    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; margin-bottom: 1.5rem;">
                        <table style="width: 100%; text-align: left; border-collapse: collapse;">
                            <thead style="background: #f1f5f9; border-bottom: 2px solid #e2e8f0;">
                                <tr>
                                    <th style="padding: 12px; font-size: 0.75rem;">Description</th>
                                    <th style="padding: 12px; font-size: 0.75rem; width: 150px;">Amount (₱)</th>
                                </tr>
                            </thead>
                            <tbody id="extQuotationItems">
                                <tr>
                                    <td style="padding: 12px;"><input type="text" class="control-pro ext-item-name" value="Base Package / Food" placeholder="Item Name"></td>
                                    <td style="padding: 12px;"><input type="number" class="control-pro ext-item-price" value="0" min="0" oninput="calcExtTotal()"></td>
                                </tr>
                            </tbody>
                            <tfoot>
                                <tr>
                                    <td colspan="2" style="padding: 12px; text-align: center;">
                                        <button type="button" onclick="addExtRow()" style="background: none; border: 1px dashed #cbd5e1; width: 100%; padding: 10px; border-radius: 8px; color: var(--primary-color); cursor: pointer;"><i class="fas fa-plus"></i> Add Line Item / Add-on</button>
                                    </td>
                                </tr>
                                <tr style="background: #f8fafc; font-weight: 800;">
                                    <td style="padding: 12px; text-align: right;">Total Amount:</td>
                                    <td style="padding: 12px;" id="extQuoteTotal">₱0.00</td>
                                    <input type="hidden" id="extTotalAmount" value="0">
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>

                <!-- STEP 4: CONFIRMATION -->
                <div class="step-content" id="ext-step-4">
                    <h4 style="font-size: 1.25rem; font-weight: 800; color: #0f172a; margin-bottom: 1.5rem;">Step 4: Save & Confirm</h4>
                    
                    <div class="form-group-pro" style="margin-bottom: 1.5rem;">
                        <label>Save Booking As <span style="color: #ef4444;">*</span></label>
                        <select id="extSaveStatus" name="status" class="control-pro" required>
                            <option value="inquiry" selected>Inquiry (Just asking/discussing)</option>
                            <option value="tentative">Tentative (Reserved but pending requirements)</option>
                        </select>
                        <small style="color: #64748b; font-size: 0.8rem; margin-top: 5px; display: block;">Note: External bookings must start as Inquiry or Tentative before they can be officially Confirmed.</small>
                    </div>

                    <div class="form-group-pro" style="margin-bottom: 1.5rem;">
                        <label>Initial Communication Note / Remarks</label>
                        <textarea id="extCommNote" name="notes" class="control-pro" rows="3" placeholder="e.g. Customer called to ask for rates..."></textarea>
                    </div>
                </div>
            </div>

            <div class="occ-modal-footer" style="flex-shrink: 0; padding: 1.25rem 2rem; background: #fff; border-top: 1px solid #e2e8f0; display: flex; justify-content: center; gap: 1.5rem;">
                <button type="button" id="extBtnPrev" class="btn-secondary-pro" style="visibility: hidden;" onclick="changeExtStep(-1)">
                    <i class="fas fa-arrow-left"></i> Previous
                </button>
                <button type="button" id="extBtnNext" class="btn-primary-pro" onclick="changeExtStep(1)">
                    Next Step <i class="fas fa-arrow-right"></i>
                </button>
                <button type="submit" id="extBtnSubmit" class="btn-primary-pro" style="display:none; background: #10b981; border-color: #10b981;">
                    Save External Booking <i class="fas fa-check"></i>
                </button>
            </div>
        </form>
    </div>
</div>

"""
    new_content = content[:start_idx] + new_modal + "\n" + content[end_idx:]
    
    with open("templates/caterer/calendar.html", "w", encoding="utf-8") as fw:
        fw.write(new_content)
    print("Patched HTML successfully.")
else:
    print("Tags not found!")
