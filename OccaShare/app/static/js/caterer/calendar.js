/* ==========================================================================
   CATERER CALENDAR CORE LOGIC (v12.0)
   - Intelligent Validation & Conflict Detection
   - Automated Pricing & ROI Engine
   - Adaptive Mobile View Switching
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {
    const calendarEl = document.getElementById('calendar');
    if (calendarEl) {
        const initialView = window.innerWidth <= 768 ? 'listMonth' : 'dayGridMonth';
        
        const calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: initialView,
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,listMonth'
            },
            themeSystem: 'standard',
            events: '/caterer/api/events',
            // --- BLOCK PAST DATES ---
            selectAllow: function(selectInfo) {
                const today = new Date();
                today.setHours(0,0,0,0);
                return selectInfo.start >= today;
            },
            eventContent: function(arg) {
                const props = arg.event.extendedProps;
                const isBlocked = props.type === 'BLOCKED';
                const iconClass = isBlocked ? 'fas fa-ban' : 'fas fa-utensils';
                return {
                    html: `<div class="custom-calendar-event" style="background-color: ${arg.event.backgroundColor}; color: ${arg.event.textColor || '#fff'};">
                            <i class="${iconClass}" style="font-size: 0.7rem;"></i>
                            <span>${arg.event.title}</span>
                        </div>`
                };
            },
            eventClick: function (info) {
                const today = new Date();
                today.setHours(0,0,0,0);
                // Prevent clicking events on past dates
                if (info.event.start < today) {
                    window.showError('Audit Guard: Past event details are archived.');
                    return;
                }
                if (info.event.extendedProps.type === 'BLOCKED') {
                    showBlockedDetails(info.event);
                } else {
                    showEventDetails(info.event);
                }
            },
            dateClick: function(info) {
                const today = new Date();
                today.setHours(0,0,0,0);
                const clickedDate = new Date(info.dateStr);
                
                if (clickedDate < today) {
                    window.showError('Audit Guard: You cannot manage past dates.');
                    return; 
                }
                
                const blockInput = document.getElementById('blockDate');
                const manInput = document.getElementById('manDate');
                if (blockInput) blockInput.value = info.dateStr;
                if (manInput) {
                    manInput.value = info.dateStr;
                    checkDateConflict(info.dateStr);
                }
                openManualBookingModal();
            },
            height: 'auto',
            dayMaxEvents: 3,
            windowResize: function(arg) {
                if (window.innerWidth <= 768) {
                    calendar.changeView('listMonth');
                } else {
                    calendar.changeView('dayGridMonth');
                }
            }
        });
        calendar.render();
        window.fullCalendarInstance = calendar;
    }

    // --- FIELD LEVEL VALIDATION HELPER ---
    window.setFieldError = (fieldId, msg) => {
        const field = document.getElementById(fieldId);
        const errorDiv = document.getElementById(`error-${fieldId}`);
        if (field && errorDiv) {
            field.classList.add('is-invalid');
            errorDiv.textContent = msg;
            errorDiv.style.display = 'block';
        }
    };

    window.clearFieldError = (fieldId) => {
        const field = document.getElementById(fieldId);
        const errorDiv = document.getElementById(`error-${fieldId}`);
        if (field && errorDiv) {
            field.classList.remove('is-invalid');
            errorDiv.style.display = 'none';
        }
    };

    initCustomerDetection();
    attachPricingListeners();
    attachInputRestrictions();
});

/**
 * Throttles and restricts inputs in real-time
 */
function attachInputRestrictions() {
    const contactInput = document.getElementById('manCustContact');
    if (contactInput) {
        contactInput.addEventListener('input', function(e) {
            // Only allow numbers
            this.value = this.value.replace(/[^0-9]/g, '');
            // Limit to 11 digits
            if (this.value.length > 11) {
                this.value = this.value.slice(0, 11);
            }
            validateSmartContact(this.value);
        });
    }

    const nameInput = document.getElementById('manCustName');
    if (nameInput) {
        nameInput.addEventListener('input', function() {
            validateSmartName(this.value);
        });
    }

    const emailInput = document.getElementById('manCustEmail');
    if (emailInput) {
        emailInput.addEventListener('input', function() {
            validateSmartEmail(this.value);
        });
    }
}

function validateSmartEmail(val) {
    if (!val) { window.clearFieldError('manCustEmail'); return false; }
    if (!val.toLowerCase().endsWith('@gmail.com')) {
        window.setFieldError('manCustEmail', 'Only @gmail.com addresses are permitted.');
        return false;
    }
    window.clearFieldError('manCustEmail');
    return true;
}

function validateSmartName(val) {
    if (!val) { window.clearFieldError('manCustName'); return false; }
    const parts = val.trim().split(/\s+/);
    
    // Check structure: First, Middle/Initial, Last
    if (parts.length < 3) {
        window.setFieldError('manCustName', 'Format: First Name, Middle Initial, and Surname.');
        return false;
    }

    // Check for repetitive parts (e.g., "John John")
    const firstName = parts[0].toLowerCase();
    const lastName = parts[parts.length - 1].toLowerCase();
    if (firstName === lastName) {
        window.setFieldError('manCustName', 'First name and Surname cannot be identical.');
        return false;
    }

    window.clearFieldError('manCustName');
    return true;
}

function validateSmartContact(val) {
    if (!val) { window.clearFieldError('manCustContact'); return false; }
    
    // Check length
    if (val.length < 11) {
        window.setFieldError('manCustContact', 'Incomplete number (11 digits required).');
        return false;
    }

    // Check for repetitive patterns (e.g., "09111111111")
    if (/(\d)\1{7,}/.test(val)) {
        window.setFieldError('manCustContact', 'Invalid pattern: Repetitive numbers detected.');
        return false;
    }

    window.clearFieldError('manCustContact');
    return true;
}

/**
 * Intelligent Customer detection (Name, Email, Contact)
 */
function initCustomerDetection() {
    let detectionTimeout;
    const emailInput = document.getElementById('manCustEmail');
    const nameInput = document.getElementById('manCustName');
    const contactInput = document.getElementById('manCustContact');
    const badge = document.getElementById('userDetectionBadge');
    
    if (!emailInput || !badge) return;

    const runDetection = () => {
        clearTimeout(detectionTimeout);
        detectionTimeout = setTimeout(async () => {
            const email = emailInput.value.trim();
            const name = nameInput.value.trim();
            const contact = contactInput.value.trim();

            if (email.length < 10 && name.length < 5 && contact.length < 11) {
                badge.style.display = 'none';
                return;
            }

            // Real-time validation check before API call
            const isEmailValid = validateSmartEmail(email);
            const isNameValid = validateSmartName(name);
            if (!isEmailValid || !isNameValid) { badge.style.display = 'none'; return; }

            badge.style.display = 'flex';
            badge.innerHTML = `<div class="badge-spinner"><i class="fas fa-circle-notch fa-spin"></i></div><div class="badge-content"><span class="badge-title">AI Scanner</span><span style="font-size: 11px; color: #64748b;">Analyzing platform records...</span></div>`;

            try {
                const resp = await fetch('/caterer/api/check-customer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email, contact })
                });
                const data = await resp.json();
                
                if (data.exists) {
                    badge.style.borderLeftColor = data.is_taken ? '#ef4444' : '#0ea5e9';
                    badge.style.background = data.is_taken ? '#fff1f2' : '#f0f9ff';
                    badge.innerHTML = `
                        <div class="badge-spinner" style="color: ${data.is_taken ? '#ef4444' : '#0ea5e9'};"><i class="fas ${data.is_taken ? 'fa-user-lock' : 'fa-user-check'}"></i></div>
                        <div class="badge-content">
                            <span class="badge-title" style="color: ${data.is_taken ? '#ef4444' : '#0ea5e9'};">${data.is_taken ? 'Registered Client' : 'Match Found'}</span>
                            <span style="font-size: 11px; color: #475569;">Verified: <b>${data.name}</b>. Profiles will be linked.</span>
                        </div>
                    `;
                    if (!contactInput.value && data.contact) contactInput.value = data.contact;
                } else {
                    badge.style.borderLeftColor = '#10b981';
                    badge.style.background = '#f0fdf4';
                    badge.innerHTML = `<div class="badge-spinner" style="color: #10b981;"><i class="fas fa-user-plus"></i></div><div class="badge-content"><span class="badge-title" style="color: #10b981;">New Discovery</span><span style="font-size: 11px; color: #166534;">Unique customer detected. Ready for registration.</span></div>`;
                }
            } catch (e) { badge.style.display = 'none'; }
        }, 800);
    };

    [emailInput, nameInput, contactInput].forEach(el => el.addEventListener('input', runDetection));
}

/**
 * Submit & Validation Logic
 */
async function submitManualEvent(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSubmitManual');
    
    // Clear all errors first
    ['manCustName', 'manCustEmail', 'manCustContact', 'manEventName', 'manGuests', 'manDate', 'manVenue'].forEach(id => window.clearFieldError(id));

    // Client-side validation
    const name = document.getElementById('manCustName').value.trim();
    const email = document.getElementById('manCustEmail').value.trim();
    const contact = document.getElementById('manCustContact').value.trim();
    const guests = parseInt(document.getElementById('manGuests').value) || 0;
    const date = document.getElementById('manDate').value;

    const isNameValid = validateSmartName(name);
    const isEmailValid = validateSmartEmail(email);
    const isContactValid = validateSmartContact(contact);
    
    let hasError = !isNameValid || !isEmailValid || !isContactValid;

    if (guests < 1) { window.setFieldError('manGuests', 'Minimum 1 guest required.'); hasError = true; }
    
    const today = new Date();
    today.setHours(0,0,0,0);
    if (new Date(date) < today) { window.setFieldError('manDate', 'Past dates not allowed.'); hasError = true; }

    if (hasError) {
        window.showError("Audit Check: Please resolve all field errors before proceeding.");
        return;
    }

    if (window.apiAction) {
        const payload = {
            customer_name: name,
            customer_email: email,
            customer_contact: contact,
            event_name: document.getElementById('manEventName').value.trim(),
            event_type: document.getElementById('manEventType').value,
            event_date: date,
            event_time: document.getElementById('manTime').value || null,
            venue_address: document.getElementById('manVenue').value.trim(),
            guest_count: guests,
            total_amount: parseFloat(document.getElementById('manAmount').value) || 0,
            package_id: document.getElementById('manPackage').value ? parseInt(document.getElementById('manPackage').value) : null
        };

        const res = await window.apiAction('/caterer/api/bookings/manual', {
            method: 'POST',
            body: JSON.stringify(payload)
        }, btn);

        if (res) {
            closeModal('manualBookingModal');
            setTimeout(() => window.location.reload(), 1000);
        }
    }
}

/**
 * Real-time Conflict Detection
 */
async function checkDateConflict(dateStr) {
    const submitBtn = document.getElementById('btnSubmitManual');
    try {
        const resp = await fetch(`/caterer/api/availability/check?date=${dateStr}`);
        const data = await resp.json();
        
        if (!data.is_available) {
            window.setFieldError('manDate', `CONFLICT: This date is BLOCKED (${data.reason || 'No reason provided'}).`);
            submitBtn.disabled = true;
        } else {
            window.clearFieldError('manDate');
            submitBtn.disabled = false;
        }
    } catch (e) { console.error("Conflict check failed:", e); }
}

/**
 * Pricing & ROI Intelligence
 */
function attachPricingListeners() {
    const pkgSelect = document.getElementById('manPackage');
    const guestInput = document.getElementById('manGuests');
    const dateInput = document.getElementById('manDate');
    
    if (!pkgSelect || !guestInput || !dateInput) return;

    pkgSelect.addEventListener('change', recalculateTotal);
    guestInput.addEventListener('input', recalculateTotal);
    dateInput.addEventListener('change', (e) => checkDateConflict(e.target.value));

    recalculateTotal();
}

function recalculateTotal() {
    const pkgSelect = document.getElementById('manPackage');
    const guestInput = document.getElementById('manGuests');
    const displayTotal = document.getElementById('displayTotal');
    const manAmount = document.getElementById('manAmount');
    
    if (!pkgSelect || !guestInput || !displayTotal) return;

    const guests = parseInt(guestInput.value) || 0;
    const option = pkgSelect.options[pkgSelect.selectedIndex];
    const basePrice = parseFloat(option.dataset.price) || 0;
    const unit = option.dataset.unit || 'fixed';
    const minGuests = parseInt(option.dataset.min) || 1;

    let total = 0;
    if (unit === 'per_guest') {
        total = basePrice * guests;
    } else {
        total = basePrice;
    }

    displayTotal.innerText = `₱${total.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    manAmount.value = total.toFixed(2);
    
    if (pkgSelect.value && guests < minGuests) {
        // Auto-fill to minimum if it's too low
        guestInput.value = minGuests;
        window.setFieldError('manGuests', `Auto-adjusted: Min ${minGuests} guests required for this package.`);
        // Recurse once with new value
        recalculateTotal();
        return;
    } else {
        window.clearFieldError('manGuests');
    }

    updateRoiPreview(pkgSelect.value, guests);
}

async function updateRoiPreview(pkgId, pax) {
    const roiPill = document.getElementById('roiPreviewLabel');
    const quoteBtn = document.getElementById('btnQuickQuote');
    
    if (!pkgId || pax <= 0) {
        if (roiPill) roiPill.style.display = 'none';
        if (quoteBtn) quoteBtn.style.display = 'none';
        return;
    }

    if (roiPill) {
        roiPill.style.display = 'inline-flex';
        roiPill.innerHTML = '<i class="fas fa-sync fa-spin"></i> Calculating ROI...';
    }

    clearTimeout(window.roiTimer);
    window.roiTimer = setTimeout(async () => {
        try {
            const resp = await fetch(`/caterer/api/quick-quotation/${pkgId}?pax=${pax}`);
            if (resp.ok) {
                const data = await resp.json();
                roiPill.innerHTML = `<i class="fas fa-chart-line"></i> Est. Profit: ₱${data.roi.toLocaleString()} (${data.markup_label})`;
                if (quoteBtn) quoteBtn.style.display = 'inline-block';
            }
        } catch (e) { if (roiPill) roiPill.style.display = 'none'; }
    }, 600);
}



function showErrorInDrawer(msg) {
    const drawer = document.getElementById('manualBookingError');
    const text = document.getElementById('errorText');
    if (drawer && text) {
        text.innerText = msg;
        drawer.style.display = 'flex';
    }
}

function clearErrorDrawer() {
    const drawer = document.getElementById('manualBookingError');
    if (drawer) drawer.style.display = 'none';
}

function openManualBookingModal() {
    if (window.openModal) window.openModal('manualBookingModal');
    else document.getElementById('manualBookingModal').style.display = 'flex';
}

function closeCalModal(id) {
    // If the global modal engine exists and it's NOT this function, use it
    if (window.closeModal && window.closeModal !== closeCalModal) {
        window.closeModal(id);
    } else {
        // Fallback: direct DOM manipulation
        const modal = document.getElementById(id);
        if (modal) {
            modal.classList.remove('active');
            setTimeout(() => {
                if (!modal.classList.contains('active')) {
                    modal.style.display = 'none';
                }
            }, 400);
        }
    }
}

function showEventDetails(event) {
    const props = event.extendedProps;
    document.getElementById('detCustomer').textContent = props.customer || '---';
    document.getElementById('detType').textContent = props.type || '---';
    document.getElementById('detDateTime').textContent = event.start.toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    }) + ' at ' + (props.time || 'TBD');
    document.getElementById('detVenue').textContent = props.venue || '---';
    document.getElementById('detPackage').textContent = (props.guests || '0') + ' Guests - ' + (props.package || '---');
    
    document.getElementById('currentBookingId').value = event.id;
    if (window.openModal) window.openModal('eventModal');
    else document.getElementById('eventModal').style.display = 'flex';
}

window.showEventDetails = showEventDetails;
window.showBlockedDetails = showBlockedDetails;
window.closeModal = window.closeModal || closeCalModal; // Fallback if global not exists
window.closeCalModal = closeCalModal;
window.toggleDateAvailability = toggleDateAvailability;
window.openManualBookingModal = openManualBookingModal;
window.submitManualEvent = submitManualEvent;
window.unblockSelectedDate = unblockSelectedDate;
window.getQuickQuotation = getQuickQuotation;
window.closeRoiBreakdown = closeRoiBreakdown;
window.toggleOtherEventType = toggleOtherEventType;


async function getQuickQuotation() {
    const pkgId = document.getElementById('manPackage').value;
    const pax = parseInt(document.getElementById('manGuests').value) || 0;
    if (!pkgId || pax <= 0) return;

    try {
        const resp = await fetch(`/caterer/api/quick-quotation/${pkgId}?pax=${pax}`);
        const data = await resp.json();
        
        document.getElementById('roiBreakdownSubtitle').innerText = `Package: ${data.package_name} (${pax} Pax)`;
        document.getElementById('breakdownTotalCost').innerText = `₱${data.total_cost.toLocaleString()}`;
        document.getElementById('breakdownRoi').innerText = `₱${data.roi.toLocaleString()}`;
        document.getElementById('breakdownTotalPrice').innerText = `₱${data.total_price.toLocaleString()}`;
        
        const list = document.getElementById('breakdownList');
        list.innerHTML = data.breakdown.map(item => `
            <div style="background: white; padding: 1rem; border-radius: 12px; border: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div>
                    <div style="font-weight: 800; color: #1e293b; font-size: 0.85rem;">${item.name}</div>
                    <div style="font-size: 0.65rem; color: #94a3b8;">Dish Cost x ${pax} pax</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-weight: 900; color: #1e293b;">₱${(item.cost_per_pax * pax).toLocaleString()}</div>
                    <div style="font-size: 0.65rem; color: #10b981; font-weight: 700;">₱${item.cost_per_pax.toFixed(2)} / pax</div>
                </div>
            </div>
        `).join('');

        if (window.openModal) window.openModal('roiBreakdownModal');
    } catch (e) { console.error(e); }
}

function closeRoiBreakdown() {
    closeModal('roiBreakdownModal');
}

/**
 * Availability Management Helpers
 */
async function toggleDateAvailability(isAvailable) {
    const dateInput = document.getElementById("blockDate");
    if (!dateInput || !dateInput.value) {
        window.showError("Please select a target date first.");
        return;
    }

    const payload = { 
        date: dateInput.value, 
        is_available: isAvailable, 
        reason: isAvailable ? "" : "Manual Block via Calendar" 
    };

    try {
        const response = await fetch("/caterer/api/availability/toggle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            window.showSuccess(`Date successfully ${isAvailable ? "opened" : "blocked"}!`);
            setTimeout(() => location.reload(), 1000);
        } else {
            window.showError("Failed to update availability.");
        }
    } catch (error) {
        console.error("Error:", error);
    }
}

async function unblockSelectedDate() {
    const date = document.getElementById("detBlockedDate").textContent; // This needs to be set when opening the modal
    // Actually we should store it in a global variable
    if (!window.currentBlockedDate) return;
    
    try {
        const response = await fetch("/caterer/api/availability/toggle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ date: window.currentBlockedDate, is_available: true, reason: "" })
        });
        if (response.ok) {
            location.reload();
        } else {
            window.showError("Failed to unblock date.");
        }
    } catch (error) {
        console.error("Error:", error);
    }
}

function showBlockedDetails(event) {
    const props = event.extendedProps;
    document.getElementById("detBlockedReason").textContent = props.reason || "No reason provided";
    document.getElementById("detBlockedDate").textContent = event.start.toLocaleDateString("en-US", {
        weekday: "long", year: "numeric", month: "long", day: "numeric"
    });
    
    window.currentBlockedDate = event.startStr.split("T")[0];
    if (window.openModal) window.openModal("blockedDateModal");
}

window.openSidebarEventModal = function(elem) {
    const ds = elem.dataset;
    document.getElementById("detCustomer").textContent = ds.customer || "---";
    document.getElementById("detType").textContent = ds.type || "---";
    document.getElementById("detDateTime").textContent = ds.datetime || "---";
    document.getElementById("detVenue").textContent = ds.venue || "---";
    document.getElementById("detPackage").textContent = ds.package || "---";
    document.getElementById("currentBookingId").value = ds.id || "";
    
    if (window.openModal) window.openModal("eventModal");
    else document.getElementById("eventModal").style.display = "flex";
};
