/* ==========================================================================
   CATERER CALENDAR CORE LOGIC (v13.0)
   - Real-time WebSocket Updates
   - Intelligent Validation & Conflict Detection
   - Automated Pricing & ROI Engine
   - Professional Performance Optimizations
   ========================================================================== */

let wsConnection = null;
let calendarRefreshTimer = null;

function initWebSocket() {
    if (wsConnection) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const clientId = 'caterer_cal_' + Math.random().toString(36).substr(2, 9);
    const url = `${protocol}//${window.location.host}/ws/${clientId}`;

    wsConnection = new WebSocket(url);

    wsConnection.onopen = function () {
        console.log('✓ Calendar WebSocket Connected');
    };

    wsConnection.onmessage = function (event) {
        const data = JSON.parse(event.data);
        handleRealtimeUpdate(data);
    };

    wsConnection.onerror = function (error) {
        console.error('✗ WebSocket error:', error);
    };

    wsConnection.onclose = function () {
        console.log('↻ WebSocket disconnected, will retry...');
        wsConnection = null;
        setTimeout(initWebSocket, 5000);
    };
}

function handleRealtimeUpdate(data) {
    if (!window.fullCalendarInstance) return;

    switch (data.type) {
        case 'booking_added':
        case 'booking_updated':
            window.fullCalendarInstance.refetchEvents();
            showNotification('Booking Updated', 'Calendar synchronized', 'success');
            break;
        case 'availability_changed':
            window.fullCalendarInstance.refetchEvents();
            break;
        case 'booking_count_changed':
            // Removed undefined function to prevent crash
            break;
    }
}

function showNotification(title, message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        bottom: 40px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 10px 15px rgba(0,0,0,0.1);
        font-weight: 600;
        z-index: 10000;
        animation: slideInRight 0.3s ease-out;
        max-width: 400px;
    `;

    const bgColor = {
        'success': '#d1fae5',
        'error': '#fee2e2',
        'warning': '#fef3c7',
        'info': '#dbeafe'
    }[type];

    const textColor = {
        'success': '#065f46',
        'error': '#991b1b',
        'warning': '#92400e',
        'info': '#1e40af'
    }[type];

    notification.style.background = bgColor;
    notification.style.color = textColor;
    notification.innerHTML = `<strong>${title}</strong><br><small>${message}</small>`;

    document.body.appendChild(notification);
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

document.addEventListener('DOMContentLoaded', function () {
    initWebSocket();
    const calendarEl = document.getElementById('calendar');
    if (calendarEl) {
        const initialView = 'dayGridMonth';

        const calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: initialView,
            height: window.innerWidth <= 768 ? 550 : 750,
            expandRows: true,
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,listMonth'
            },
            datesSet: function (info) {
                const titleEl = document.querySelector('.fc-toolbar-title');
                if (titleEl) {
                    const d = info.view.currentStart;
                    const year = d.getFullYear();
                    const month = String(d.getMonth() + 1).padStart(2, '0');
                    const currentMonth = `${year}-${month}`;
                    let maxMonthStr = "";
                    if (window.MAX_BOOKING_DATE) {
                        maxMonthStr = window.MAX_BOOKING_DATE.substring(0, 7);
                    }
                    let minMonthStr = "";
                    if (window.MIN_BOOKING_DATE) {
                        const today = new Date();
                        const minDate = new Date(window.MIN_BOOKING_DATE);
                        const actualMin = today < minDate ? today : minDate;
                        minMonthStr = actualMin.toISOString().substring(0, 7);
                    }
                    
                    titleEl.innerHTML = `
                        <input type="month" id="calMonthPicker" value="${currentMonth}" 
                            max="${maxMonthStr}" min="${minMonthStr}"
                            style="border: none; background: transparent; font-size: inherit; font-weight: inherit; color: inherit; cursor: pointer; outline: none; font-family: inherit; width: 100%; text-align: center;"
                            onchange="if(window.fullCalendarInstance) window.fullCalendarInstance.gotoDate(this.value + '-01')">
                    `;
                }
            },
            themeSystem: 'standard',
            events: '/caterer/api/events',
            editable: false,
            selectable: true,
            selectConstraint: 'businessHours',
            dayMaxEvents: false, // Ensure all events are visible, row will expand
            selectAllow: function (selectInfo) {
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                return selectInfo.start >= today;
            },
            eventClick: function (info) {
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                if (info.event.start < today) {
                    showNotification('Archive Notice', 'Past event details are not editable', 'info');
                    return;
                }
                if (info.event.extendedProps.type === 'BLOCKED') {
                    showBlockedDetails(info.event);
                } else {
                    showEventDetails(info.event);
                }
            },
            dateClick: function (info) {
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                const clickedDate = new Date(info.dateStr);

                if (clickedDate < today) {
                    showNotification('Error', 'Cannot manage past dates', 'error');
                    return;
                }

                const blockInput = document.getElementById('blockDate');
                const manInput = document.getElementById('manDate');
                if (blockInput) blockInput.value = info.dateStr;
                if (manInput) {
                    manInput.value = info.dateStr;
                    checkDateConflict(info.dateStr);
                }
                if (window.innerWidth <= 768) {
                    // Mobile View: Populate bottom list instead of opening modal
                    const clickedEvents = window.fullCalendarInstance.getEvents().filter(e => {
                        return e.startStr.split('T')[0] === info.dateStr;
                    });
                    
                    const listContainer = document.getElementById('mobileDayList');
                    const titleEl = document.getElementById('mobileDayTitle');
                    const mobileContainer = document.getElementById('mobileDayEvents');
                    
                    titleEl.innerText = new Date(info.dateStr).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
                    listContainer.innerHTML = '';
                    
                    if (clickedEvents.length === 0) {
                        listContainer.innerHTML = '<div style="padding: 1rem; text-align: center; color: #64748b; font-size: 0.9rem; background: #f8fafc; border-radius: 8px;">No events on this date</div>';
                    } else {
                        clickedEvents.forEach(e => {
                            let type = e.extendedProps.type || 'Standard';
                            let status = e.extendedProps.status || 'pending';
                            let statusColor = status === 'confirmed' ? '#10b981' : (status === 'ongoing' ? '#3b82f6' : (status === 'cancelled' ? '#ef4444' : '#f59e0b'));
                            
                            let cardHtml = `
                                <div onclick="showEventDetailsById('${e.id}')" style="background: white; border: 1px solid #e2e8f0; border-left: 4px solid ${statusColor}; border-radius: 8px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05); cursor: pointer;">
                                    <div style="font-weight: 700; color: #1e293b; font-size: 0.95rem; margin-bottom: 4px;">${e.title === 'BLOCKED' ? '<span style="color: #ef4444;">Blocked Date</span>' : e.title}</div>
                                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; color: #64748b;">
                                        <span>${e.title !== 'BLOCKED' && e.extendedProps.customer ? e.extendedProps.customer : '---'}</span>
                                        <span style="background: ${statusColor}15; color: ${statusColor}; padding: 2px 8px; border-radius: 9999px; font-weight: 600; font-size: 0.7rem; text-transform: capitalize;">${e.title === 'BLOCKED' ? 'Unavailable' : status}</span>
                                    </div>
                                </div>
                            `;
                            listContainer.innerHTML += cardHtml;
                        });
                    }
                    mobileContainer.style.display = 'block';
                    // Scroll to it smoothly
                    mobileContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                } else {
                    // Desktop View: Standard manual booking modal
                    openManualBookingModal();
                }
            },
            eventDidMount: function (info) {
                info.el.setAttribute('role', 'button');
                info.el.setAttribute('tabindex', '0');
                
                // Professional Tooltip implementation using native title
                if (info.event.extendedProps && info.event.extendedProps.type && info.event.extendedProps.type !== 'BLOCKED') {
                    const props = info.event.extendedProps;
                    let tooltip = `Event: ${info.event.title}\n`;
                    if (props.customer) tooltip += `Customer: ${props.customer}\n`;
                    if (props.guests) tooltip += `Guests: ${props.guests} pax\n`;
                    if (props.time && props.time !== 'TBD') tooltip += `Time: ${props.time}\n`;
                    if (props.venue && props.venue !== 'TBD') tooltip += `Venue: ${props.venue}`;
                    info.el.setAttribute('title', tooltip);
                } else if (info.event.title === 'BLOCKED') {
                    info.el.setAttribute('title', 'Blocked Date\nNot accepting bookings');
                }
            },
            windowResize: function (arg) {
                // Let FullCalendar handle responsive layouts inherently, maintain day grid
            }
        });
        calendar.render();
        window.fullCalendarInstance = calendar;

        // Helper for mobile cards
        window.showEventDetailsById = function(id) {
            const event = window.fullCalendarInstance.getEventById(id);
            if (event) {
                if (event.title === 'BLOCKED') {
                    showBlockedDetails(event);
                } else {
                    showEventDetails(event);
                }
            }
        };

        // Global Search Integration
        window.addEventListener('globalSearch', function (e) {
            const query = e.detail.value.toLowerCase();
            const events = window.fullCalendarInstance.getEvents();
            
            events.forEach(event => {
                let match = false;
                if (!query) {
                    match = true;
                } else {
                    const titleMatch = event.title && event.title.toLowerCase().includes(query);
                    const customerMatch = event.extendedProps && event.extendedProps.customer && event.extendedProps.customer.toLowerCase().includes(query);
                    const typeMatch = event.extendedProps && event.extendedProps.type && event.extendedProps.type.toLowerCase().includes(query);
                    const idMatch = event.extendedProps && event.extendedProps.booking_id && String(event.extendedProps.booking_id).includes(query);
                    
                    match = titleMatch || customerMatch || typeMatch || idMatch;
                }
                
                // Ensure we restore to 'auto' so FullCalendar natively handles the allDay block rendering
                event.setProp('display', match ? 'auto' : 'none');
            });
        });

        window.addEventListener('resize', function () {
            clearTimeout(calendarRefreshTimer);
            calendarRefreshTimer = setTimeout(() => {
                calendar.updateSize();
            }, 250);
        });
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

window.updateVisibleCapacity = function (start, end) {
    // Safely do nothing to prevent ReferenceErrors
};

window.updateCapacityDisplay = function (data) {
    // Safely do nothing to prevent ReferenceErrors
};

function validateFirstName() {
    const field = document.getElementById('manFirstName');
    const error = document.getElementById('error-manFirstName');
    const val = field.value.trim();

    if (!val) {
        error.textContent = 'First name is required';
        field.classList.add('is-invalid');
        return false;
    }
    if (val.length < 2) {
        error.textContent = 'First name must be at least 2 characters';
        field.classList.add('is-invalid');
        return false;
    }
    field.classList.remove('is-invalid');
    error.textContent = '';
    return true;
}

function validateLastName() {
    const field = document.getElementById('manLastName');
    const error = document.getElementById('error-manLastName');
    const val = field.value.trim();

    if (!val) {
        error.textContent = 'Last name is required';
        field.classList.add('is-invalid');
        return false;
    }
    if (val.length < 2) {
        error.textContent = 'Last name must be at least 2 characters';
        field.classList.add('is-invalid');
        return false;
    }
    field.classList.remove('is-invalid');
    error.textContent = '';
    return true;
}

function validateEmail() {
    const field = document.getElementById('manCustEmail');
    const error = document.getElementById('error-manCustEmail');
    const val = field.value.trim();

    if (!val) {
        error.textContent = 'Email is required';
        field.classList.add('is-invalid');
        return false;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(val)) {
        error.textContent = 'Please enter a valid email address';
        field.classList.add('is-invalid');
        return false;
    }
    field.classList.remove('is-invalid');
    error.textContent = '';
    return true;
}

function validateContact() {
    const field = document.getElementById('manCustContact');
    const error = document.getElementById('error-manCustContact');
    const val = field.value.trim();

    if (!val) {
        error.textContent = 'Contact number is required';
        field.classList.add('is-invalid');
        return false;
    }
    if (!val.startsWith('09')) {
        error.textContent = 'PH number must start with 09';
        field.classList.add('is-invalid');
        return false;
    }
    if (val.length !== 11) {
        error.textContent = 'PH number must be 11 digits';
        field.classList.add('is-invalid');
        return false;
    }
    if (/(\d)\1{7,}/.test(val)) {
        error.textContent = 'Invalid pattern detected';
        field.classList.add('is-invalid');
        return false;
    }
    field.classList.remove('is-invalid');
    error.textContent = '';
    return true;
}

function validateEventName() {
    const field = document.getElementById('manEventName');
    const error = document.getElementById('error-manEventName');
    const val = field.value.trim();

    if (!val) {
        error.textContent = 'Event name is required';
        field.classList.add('is-invalid');
        return false;
    }
    if (val.length < 3) {
        error.textContent = 'Event name must be at least 3 characters';
        field.classList.add('is-invalid');
        return false;
    }
    field.classList.remove('is-invalid');
    error.textContent = '';
    return true;
}

function validateEventType() {
    const field = document.getElementById('manEventType');
    const error = document.getElementById('error-manEventType');

    if (!field.value) {
        error.textContent = 'Please select an event type';
        field.classList.add('is-invalid');
        return false;
    }
    field.classList.remove('is-invalid');
    error.textContent = '';
    return true;
}

function validateOtherType() {
    const typeField = document.getElementById('manEventType');
    const field = document.getElementById('manOtherType');
    const error = document.getElementById('error-manOtherType');

    if (typeField.value === 'Other') {
        if (!field.value.trim()) {
            error.textContent = 'Please specify the event type';
            field.classList.add('is-invalid');
            return false;
        }
        if (field.value.trim().length < 3) {
            error.textContent = 'Description must be at least 3 characters';
            field.classList.add('is-invalid');
            return false;
        }
    }
    field.classList.remove('is-invalid');
    error.textContent = '';
    return true;
}

function validateEventDate() {
    const field = document.getElementById('manDate');
    const error = document.getElementById('error-manDate');
    const val = field.value;

    if (!val) {
        error.textContent = 'Event date is required';
        field.classList.add('is-invalid');
        return false;
    }
    const eventDate = new Date(val);
    eventDate.setHours(0, 0, 0, 0);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const leadTimeDays = window.CATERER_LEAD_TIME || 0;
    const minDate = new Date(today);
    minDate.setDate(minDate.getDate() + leadTimeDays);
    minDate.setHours(0, 0, 0, 0);

    if (eventDate < minDate) {
        error.textContent = `Date must be at least ${leadTimeDays} days from today based on your profile settings.`;
        field.classList.add('is-invalid');
        return false;
    }

    if (window.MAX_BOOKING_DATE) {
        const maxDate = new Date(window.MAX_BOOKING_DATE);
        maxDate.setHours(0, 0, 0, 0);
        if (eventDate > maxDate) {
            error.textContent = `Date exceeds your maximum advance booking limit.`;
            field.classList.add('is-invalid');
            return false;
        }
    }

    field.classList.remove('is-invalid');
    error.textContent = '';
    return true;
}

function validateEventTime() {
    const field = document.getElementById('manTime');
    const error = document.getElementById('error-manTime');
    const val = field.value;

    if (!val) {
        error.textContent = 'Event time is required';
        field.classList.add('is-invalid');
        return false;
    }
    
    if (window.BUSINESS_OPEN && window.BUSINESS_CLOSE) {
        if (val < window.BUSINESS_OPEN || val > window.BUSINESS_CLOSE) {
            const formatTime = (timeStr) => {
                const [h, m] = timeStr.split(':');
                let hr = parseInt(h);
                const ampm = hr >= 12 ? 'PM' : 'AM';
                hr = hr % 12 || 12;
                return `${hr}:${m} ${ampm}`;
            };
            const open12 = formatTime(window.BUSINESS_OPEN);
            const close12 = formatTime(window.BUSINESS_CLOSE);
            error.textContent = `Time must be within your business hours (${open12} - ${close12})`;
            field.classList.add('is-invalid');
            return false;
        }
    }

    field.classList.remove('is-invalid');
    error.textContent = '';
    return true;
}

function validateGuestCount() {
    const field = document.getElementById('manGuests');
    const error = document.getElementById('error-manGuests');
    const packageSelect = document.getElementById('manPackage');
    const val = parseInt(field.value) || 0;
    const profileMinPax = window.CATERER_MIN_PAX || 1;

    if (!field.value || val < profileMinPax) {
        error.textContent = `Guest count must be at least ${profileMinPax} (based on your settings)`;
        field.classList.add('is-invalid');
        return false;
    }

    if (packageSelect && packageSelect.value) {
        const selectedOption = packageSelect.options[packageSelect.selectedIndex];
        const minPax = parseInt(selectedOption.getAttribute('data-min')) || profileMinPax;
        if (val < minPax) {
            error.textContent = `Selected package requires minimum ${minPax} guests`;
            field.classList.add('is-invalid');
            return false;
        }
    }

    field.classList.remove('is-invalid');
    error.textContent = '';
    return true;
}

function validateProvince() {
    const field = document.getElementById('manProvince');
    const error = document.getElementById('error-manProvince');

    if (!field.value) {
        error.textContent = 'Province is required';
        field.classList.add('is-invalid');
        return false;
    }
    field.classList.remove('is-invalid');
    error.textContent = '';
    return true;
}

function validateMunicipality() {
    const field = document.getElementById('manMunicipality');
    const error = document.getElementById('error-manMunicipality');

    if (!field.value) {
        error.textContent = 'Municipality is required';
        field.classList.add('is-invalid');
        return false;
    }
    field.classList.remove('is-invalid');
    error.textContent = '';
    return true;
}

function validateBarangay() {
    const field = document.getElementById('manBarangay');
    const error = document.getElementById('error-manBarangay');

    if (!field.value) {
        error.textContent = 'Barangay is required';
        field.classList.add('is-invalid');
        return false;
    }
    field.classList.remove('is-invalid');
    error.textContent = '';
    return true;
}

function validatePackage() {
    const field = document.getElementById('manPackage');
    const error = document.getElementById('error-manPackage');

    if (!field.value) {
        error.textContent = 'Please select a catering package';
        field.classList.add('is-invalid');
        return false;
    }
    field.classList.remove('is-invalid');
    error.textContent = '';
    error.textContent = '';
    return true;
}

/**
 * Throttles and restricts inputs in real-time
 */
function attachInputRestrictions() {
    const contactInput = document.getElementById('manCustContact');
    if (contactInput) {
        contactInput.addEventListener('input', function (e) {
            // Only allow numbers
            this.value = this.value.replace(/[^0-9]/g, '');
            // Must start with 09 logic check (will show error in validate)
            // Limit to 11 digits
            if (this.value.length > 11) {
                this.value = this.value.slice(0, 11);
            }
            validateSmartContact(this.value);
        });
    }

    const guestsInput = document.getElementById('manGuests');
    const packageSelect = document.getElementById('manPackage');

    const validateGuests = () => {
        if (!guestsInput || !packageSelect) return;
        const val = parseInt(guestsInput.value) || 0;
        const profileMinPax = window.CATERER_MIN_PAX || 1;

        if (packageSelect.value) {
            const selectedOption = packageSelect.options[packageSelect.selectedIndex];
            const minPax = parseInt(selectedOption.getAttribute('data-min')) || profileMinPax;
            if (val < minPax) {
                window.setFieldError('manGuests', `Selected package requires min ${minPax} guests.`);
            } else {
                window.clearFieldError('manGuests');
            }
        } else if (val < profileMinPax) {
            window.setFieldError('manGuests', `Guest count must be at least ${profileMinPax} (based on your settings).`);
        } else {
            window.clearFieldError('manGuests');
        }
    };

    if (guestsInput) guestsInput.addEventListener('input', validateGuests);
    if (packageSelect) packageSelect.addEventListener('change', validateGuests);
    const fNameInput = document.getElementById('manFirstName');
    const lNameInput = document.getElementById('manLastName');

    const validateNameFields = () => {
        const f = (fNameInput ? fNameInput.value.trim().toLowerCase() : "");
        const m = (document.getElementById('manMiddleName') ? document.getElementById('manMiddleName').value.trim().toLowerCase() : "");
        const l = (lNameInput ? lNameInput.value.trim().toLowerCase() : "");

        if (f && l && f === l) {
            window.setFieldError('manFirstName', 'First and Last name cannot be identical.');
            window.setFieldError('manLastName', 'First and Last name cannot be identical.');
            return false;
        } else if (f && m && l && f === m && m === l) {
            window.setFieldError('manFirstName', 'Names cannot be identical.');
            return false;
        } else if (f && f.length < 2) {
            window.setFieldError('manFirstName', 'First name too short.');
            return false;
        } else {
            window.clearFieldError('manFirstName');
            window.clearFieldError('manLastName');
            return true;
        }
    };

    if (fNameInput) fNameInput.addEventListener('input', validateNameFields);
    if (lNameInput) lNameInput.addEventListener('input', validateNameFields);
    if (document.getElementById('manMiddleName')) document.getElementById('manMiddleName').addEventListener('input', validateNameFields);

    const emailInput = document.getElementById('manCustEmail');
    if (emailInput) {
        emailInput.addEventListener('input', function () {
            validateSmartEmail(this.value);
        });
    }
}

function validateSmartEmail(val) {
    if (!val) { window.clearFieldError('manCustEmail'); return false; }
    const emailLower = val.toLowerCase();
    if (!emailLower.endsWith('@gmail.com')) {
        window.setFieldError('manCustEmail', 'Only @gmail.com addresses are permitted.');
        return false;
    }
    if (emailLower.startsWith('test@') || emailLower.startsWith('dummy@') || emailLower.startsWith('admin@')) {
        window.setFieldError('manCustEmail', 'Dummy or generic emails are not allowed.');
        return false;
    }
    window.clearFieldError('manCustEmail');
    return true;
}

function validateSmartContact(val) {
    if (!val) { window.clearFieldError('manCustContact'); return false; }

    // Check start
    if (!val.startsWith('09')) {
        window.setFieldError('manCustContact', 'Must start with 09');
        return false;
    }

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
    const fNameInput = document.getElementById('manFirstName');
    const lNameInput = document.getElementById('manLastName');
    const contactInput = document.getElementById('manCustContact');
    const badge = document.getElementById('userDetectionBadge');

    if (!emailInput || !badge) return;

    const runDetection = () => {
        clearTimeout(detectionTimeout);
        detectionTimeout = setTimeout(async () => {
            const email = emailInput.value.trim();
            const name = (fNameInput.value.trim() + " " + lNameInput.value.trim()).trim();
            const contact = contactInput.value.trim();

            if (email.length < 10 && name.length < 3 && contact.length < 11) {
                badge.style.display = 'none';
                return;
            }

            // Real-time validation check before API call
            const isEmailValid = validateSmartEmail(email);
            if (!isEmailValid || fNameInput.value.trim().length === 0 || lNameInput.value.trim().length === 0) { badge.style.display = 'none'; return; }
            badge.style.display = 'flex';
            badge.style.alignItems = 'center';
            badge.style.gap = '12px';
            badge.style.padding = '12px 16px';
            badge.style.borderRadius = '8px';
            badge.style.border = '1px solid #e2e8f0';
            badge.style.borderLeft = '4px solid #cbd5e1';
            badge.style.background = '#f8fafc';
            badge.style.marginTop = '1rem';

            badge.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; color: #64748b;">
                    <i class="fas fa-circle-notch fa-spin" style="font-size: 1rem;"></i>
                </div>
                <div style="display: flex; flex-direction: column; justify-content: center;">
                    <span style="font-weight: 800; font-size: 0.85rem; color: #475569; text-transform: uppercase; letter-spacing: 0.02em; margin-bottom: 2px;">AI Scanner</span>
                    <span style="font-size: 0.75rem; color: #64748b; font-weight: 500;">Analyzing platform records...</span>
                </div>
            `;

            try {
                const resp = await fetch(`/caterer/api/customers/check_duplicate?email=${encodeURIComponent(email)}&contact=${encodeURIComponent(contact)}`);
                const data = await resp.json();

                if (data.exists) {
                    if (data.role === 'caterer' || data.role === 'admin') {
                        window.setFieldError('manCustEmail', 'Security Violation: This email is registered to a Caterer or Admin account. Only customer accounts can be used for walk-in bookings.');
                        btn.innerHTML = 'Create Booking';
                        btn.disabled = false;
                        return;
                    }
                    badge.style.borderLeftColor = '#0ea5e9';
                    badge.style.background = '#f0f9ff';
                    badge.style.borderColor = '#bae6fd';
                    badge.innerHTML = `
                        <div style="display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; background: rgba(14, 165, 233, 0.15); border-radius: 50%; color: #0ea5e9;">
                            <i class="fas fa-user-check" style="font-size: 0.9rem;"></i>
                        </div>
                        <div style="display: flex; flex-direction: column; justify-content: center;">
                            <span style="font-weight: 800; font-size: 0.85rem; color: #0ea5e9; text-transform: uppercase; letter-spacing: 0.02em; margin-bottom: 2px;">Existing Customer Found</span>
                            <span style="font-size: 0.75rem; color: #475569; font-weight: 500;">Booking will link to: <b style="color: #0f172a; font-weight: 700;">${data.name}</b></span>
                        </div>
                    `;
                } else {
                    badge.style.borderLeftColor = '#10b981';
                    badge.style.background = '#ecfdf5';
                    badge.style.borderColor = '#a7f3d0';
                    badge.innerHTML = `
                        <div style="display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; background: rgba(16, 185, 129, 0.15); border-radius: 50%; color: #10b981;">
                            <i class="fas fa-user-plus" style="font-size: 0.9rem;"></i>
                        </div>
                        <div style="display: flex; flex-direction: column; justify-content: center;">
                            <span style="font-weight: 800; font-size: 0.85rem; color: #10b981; text-transform: uppercase; letter-spacing: 0.02em; margin-bottom: 2px;">New Customer Profile</span>
                            <span style="font-size: 0.75rem; color: #475569; font-weight: 500;">A new profile will be created for this booking.</span>
                        </div>
                    `;
                }
            } catch (err) {
                badge.style.display = 'none';
            }
        }, 800);
    };

    [emailInput, fNameInput, lNameInput, contactInput].forEach(el => el.addEventListener('input', runDetection));
}

/**
 * Submit & Validation Logic
 */
async function submitManualEvent(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSubmitManual');

    // Run all validators
    const validations = [
        validateFirstName(),
        validateLastName(),
        validateEmail(),
        validateContact(),
        validateEventName(),
        validateEventType(),
        validateEventDate(),
        validateEventTime(),
        validateGuestCount(),
        validateProvince(),
        validateMunicipality(),
        validateBarangay(),
        validatePackage()
    ];

    if (document.getElementById('manEventType').value === 'Other') {
        validations.push(validateOtherType());
    }

    const allValid = validations.every(v => v === true);
    if (!allValid) {
        showNotification('Validation Error', 'Please check the highlighted fields and try again', 'error');
        return;
    }

    // Get form data
    const date = document.getElementById('manDate').value;
    const guests = parseInt(document.getElementById('manGuests').value);
    const fName = document.getElementById('manFirstName').value.trim();
    const lName = document.getElementById('manLastName').value.trim();
    const mName = document.getElementById('manMiddleName').value.trim();
    const email = document.getElementById('manCustEmail').value.trim();
    const contact = document.getElementById('manCustContact').value.trim();
    const province = document.getElementById('manProvinceText').value.trim();
    const municipality = document.getElementById('manMunicipalityText').value.trim();
    const barangay = document.getElementById('manBarangayText').value.trim();
    const landmark = document.getElementById('manLandmark').value.trim();

    // Check for date conflicts
    const conflictRes = await checkDateConflict(date);
    if (!conflictRes.available && conflictRes.isManualBlock) {
        const error = document.getElementById('error-manDate');
        error.textContent = `Cannot book: ${conflictRes.reason}`;
        document.getElementById('manDate').classList.add('is-invalid');
        showNotification('Date Unavailable', conflictRes.reason, 'error');
        return;
    }

    // Warn if capacity full
    let forceOverride = false;
    if (!conflictRes.available && !conflictRes.isManualBlock) {
        if (!confirm(`⚠️ Capacity Warning\n\n${conflictRes.reason}\n\nDo you still want to create this booking?`)) {
            return;
        }
        forceOverride = true;
    }

    if (window.apiAction) {
        let pkgId = document.getElementById('manPackageMode') ? document.getElementById('manPackageMode').value : null;
        if (pkgId === 'custom') pkgId = null;

        const payload = {
            first_name: fName,
            last_name: lName,
            middle_name: mName,
            customer_email: email,
            customer_contact: contact,
            event_name: document.getElementById('manEventName').value.trim(),
            event_type: document.getElementById('manEventType').value,
            event_date: date,
            event_time: document.getElementById('manTime').value || null,
            province: province,
            municipality: municipality,
            barangay: barangay,
            landmark: landmark,
            guest_count: guests,
            total_amount: parseFloat(document.getElementById('manAmount').value) || 0,
            amount_paid: parseFloat(document.getElementById('manAmountPaid').value) || 0,
            remaining_balance: parseFloat(document.getElementById('manBalance').value) || 0,
            discount_amount: parseFloat(document.getElementById('quoteDiscount').value) || 0,
            quotation_items: window.quoteItems || [],
            package_id: pkgId ? parseInt(pkgId) : null,
            special_notes: document.getElementById('manSpecialNotes') ? document.getElementById('manSpecialNotes').value.trim() : "",
            payment_method: document.getElementById('manPaymentMethod') ? document.getElementById('manPaymentMethod').value : "Cash",
            payment_status: document.getElementById('manPaymentStatus') ? document.getElementById('manPaymentStatus').value : "paid",
            booking_source: document.getElementById('manBookingSource') ? document.getElementById('manBookingSource').value : "Walk-in",
            force_override: forceOverride
        };

        try {
            const res = await fetch('/caterer/api/bookings/manual', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const data = await res.json();
            
            if (!res.ok) {
                let detailStr = data.detail || data.message || 'Failed to create booking';
                const errBox = document.getElementById('manualBookingFormError');
                
                if (typeof detailStr === 'string' && detailStr.includes('|')) {
                    const parts = detailStr.split('|');
                    const fieldId = parts[0];
                    const msg = parts[1];
                    
                    // Show text under the specific field
                    window.setFieldError(fieldId, msg);
                    
                    // Scroll to the field smoothly
                    const targetEl = document.getElementById(fieldId);
                    if (targetEl) {
                        targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        targetEl.focus();
                    }
                    
                    // Optional: Still show general banner, or clear it
                    if (errBox) errBox.style.display = 'none';
                } else {
                    // Fallback to banner if no field specified
                    if (errBox) {
                        errBox.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${detailStr}`;
                        errBox.style.display = 'flex';
                    } else {
                        showNotification("Error", detailStr, "error");
                    }
                }
                
                btn.innerHTML = 'Create Booking';
                btn.disabled = false;
                btn.style.opacity = '1';
                btn.style.cursor = 'pointer';
                return;
            }
            
            // Clear any previous inline errors on success
            const errBox = document.getElementById('manualBookingFormError');
            if (errBox) errBox.style.display = 'none';
            closeModal('manualBookingModal');
            showNotification("Success", "Booking successfully recorded to your system.", "success");

            // Real-Time Update: FullCalendar
            if (window.fullCalendarInstance) {
                window.fullCalendarInstance.refetchEvents();
            }

            // Real-Time Update: Prepend to Sidebar list
            injectBookingToSidebar({
                id: data.booking_id || 'NEW',
                customer: payload.first_name + ' ' + payload.last_name,
                type: payload.event_type === 'Other' ? document.getElementById('manOtherType').value : payload.event_type,
                eventName: payload.event_name,
                date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: '2-digit' }),
                dateFull: new Date(date),
                time: payload.event_time,
                venue: payload.venue_address,
                guests: guests,
                packageText: document.getElementById('manPackage').options[document.getElementById('manPackage').selectedIndex].text
            });

            document.getElementById('manualBookingForm').reset();
            document.getElementById('displayTotal').innerText = '₱0.00';
            const badge = document.getElementById('userDetectionBadge');
            if (badge) badge.style.display = 'none';
        } catch (e) {
            console.error(e);
            showNotification("Error", "A network error occurred while submitting.", "error");
            btn.innerHTML = 'Create Booking';
            btn.disabled = false;
        }
    }
}

function toggleOtherEventType() {
    const sel = document.getElementById('manEventType');
    const otherDiv = document.getElementById('otherEventTypeDiv');
    if (sel.value === 'Other') {
        otherDiv.style.display = 'block';
        document.getElementById('manOtherType').required = true;
    } else {
        otherDiv.style.display = 'none';
        document.getElementById('manOtherType').required = false;
    }
}

function injectBookingToSidebar(data) {
    const list = document.querySelector('.cal-tracker-list');
    if (!list) return;

    // Remove "No events" placeholder if it exists
    if (list.innerHTML.includes('No events scheduled')) {
        list.innerHTML = '';
    }

    const d = data.dateFull;
    const typeClass = data.type ? data.type.toLowerCase().split(' ')[0] : 'other';
    const month = d.toLocaleDateString('en-US', { month: 'short' });
    const day = d.toLocaleDateString('en-US', { day: '2-digit' });

    let timeFormatted = 'TBD';
    if (data.time) {
        const [h, m] = data.time.split(':');
        const ampm = h >= 12 ? 'PM' : 'AM';
        const h12 = h % 12 || 12;
        timeFormatted = `${h12}:${m} ${ampm}`;
    }
    const datetimeStr = `${d.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })} at ${timeFormatted}`;

    const newEl = document.createElement('div');
    newEl.className = `weekly-event-card type-${typeClass}`;
    newEl.dataset.id = data.id;
    newEl.dataset.customer = data.customer;
    newEl.dataset.type = data.type;
    newEl.dataset.title = data.eventName;
    newEl.dataset.datetime = datetimeStr;
    newEl.dataset.venue = data.venue;
    newEl.dataset.package = `${data.guests} Guests - ${data.packageText}`;
    newEl.setAttribute('onclick', 'openSidebarEventModal(this)');

    newEl.innerHTML = `
        <div class="weekly-event-date">
            <span>${month}</span>
            <span>${day}</span>
        </div>
        <div class="weekly-event-info">
            <div class="weekly-event-name">${data.eventName}</div>
            <div class="event-status-badge status-upcoming">New Booking</div>
        </div>
    `;

    // Add glowing effect to highlight new entry
    newEl.style.boxShadow = "0 0 15px rgba(16, 185, 129, 0.4)";
    list.prepend(newEl);
    setTimeout(() => { newEl.style.boxShadow = ""; }, 3000);
}

async function checkAvailabilityStatus(dateStr) {
    if (!dateStr) return;
    const box = document.getElementById('availabilityStatusBox');
    const icon = document.getElementById('availabilityStatusIcon');
    const text = document.getElementById('availabilityStatusText');
    const btnBlock = document.getElementById('btnBlockDate');
    const btnOpen = document.getElementById('btnOpenDate');
    const blockReasonDiv = document.getElementById('blockReasonDiv');
    const blockReasonInput = document.getElementById('blockReason');

    if (!box) return;

    box.style.display = 'flex';
    box.style.background = '#f1f5f9';
    box.style.color = '#64748b';
    icon.className = 'fas fa-spinner fa-spin';
    text.textContent = 'Checking status...';
    btnBlock.style.display = 'none';
    btnOpen.style.display = 'none';
    if(blockReasonDiv) blockReasonDiv.style.display = 'none';
    if(blockReasonInput) blockReasonInput.value = '';

    try {
        const resp = await fetch(`/caterer/api/availability/check?date=${dateStr}`);
        const data = await resp.json();

        const countStr = ` (${data.booking_count || 0}/${data.max_capacity || 1} slots booked)`;

        if (data.is_available) {
            box.style.background = '#ecfdf5';
            box.style.color = '#059669';
            box.style.border = '1px solid #a7f3d0';
            icon.className = 'fas fa-check-circle';
            text.innerHTML = `<strong>Status: Available</strong><br><small style="opacity:0.8">${countStr}</small>`;
            btnBlock.style.display = 'block';
            if(blockReasonDiv) blockReasonDiv.style.display = 'block';
        } else {
            if (data.is_manual_block) {
                box.style.background = '#fef2f2';
                box.style.color = '#e11d48';
                box.style.border = '1px solid #fecaca';
                icon.className = 'fas fa-lock';
                text.innerHTML = `<strong>Status: Blocked Manually</strong><br><small style="opacity:0.8">Reason: ${data.reason}</small>`;
                btnOpen.style.display = 'block';
            } else {
                // Auto-blocked due to capacity
                box.style.background = '#fffbeb';
                box.style.color = '#d97706';
                box.style.border = '1px solid #fde68a';
                icon.className = 'fas fa-exclamation-triangle';
                text.innerHTML = `<strong>Status: Capacity Full</strong><br><small style="opacity:0.8">Auto-blocked ${countStr}</small>`;
                btnBlock.style.display = 'block'; // Can still manually block if desired
            }
        }
    } catch (e) {
        box.style.display = 'none';
    }
}

/**
 * Real-time Conflict Detection
 */
async function checkDateConflict(dateStr) {
    try {
        const resp = await fetch(`/caterer/api/availability/check?date=${dateStr}`);
        const data = await resp.json();

        if (!data.is_available && data.is_manual_block) {
            window.setFieldError('manDate', `Date unavailable: ${data.reason}`);
        } else if (!data.is_available && !data.is_manual_block) {
            window.setFieldError('manDate', `Warning: Capacity Full (${data.booking_count}/${data.max_capacity}). Overriding this will exceed your limit.`);
        } else {
            window.clearFieldError('manDate');
        }

        return {
            available: data.is_available,
            reason: data.reason,
            isManualBlock: data.is_manual_block,
            bookingCount: data.booking_count,
            maxCapacity: data.max_capacity
        };
    } catch (e) {
        return { available: true }; // Failsafe
    }
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

    // Removed updateRoiPreview since ROI is no longer used
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

    // New Fields
    const paymentMap = { 'pending': 'Unpaid', 'deposit_paid': 'Deposit Paid', 'paid': 'Fully Paid' };
    const paymentStatusEl = document.getElementById('detPayment');
    if (paymentStatusEl) paymentStatusEl.textContent = paymentMap[props.payment_status] || props.payment_status || '---';

    const specialEl = document.getElementById('detSpecial');
    if (specialEl) specialEl.textContent = props.special_requests || 'None';

    document.getElementById('evModalBookingId').value = event.id;
    if (window.openModal) window.openModal('eventModal');
    else document.getElementById('eventModal').style.display = 'flex';
}

function showBlockedDetails(event) {
    const props = event.extendedProps;
    showNotification("Error", `Date Blocked: ${props.reason || 'Capacity reached or manually blocked'}`, "error");
}

window.showEventDetails = showEventDetails;
window.showBlockedDetails = showBlockedDetails;

window.copyInvoiceLink = function() {
    const bookingId = document.getElementById('evModalBookingId').value;
    if (!bookingId) {
        showNotification('Error', 'Booking ID not found', 'error');
        return;
    }
    const url = window.location.origin + '/customer/booking/' + bookingId + '/invoice';
    navigator.clipboard.writeText(url).then(() => {
        showNotification('Invoice Link Copied!', 'You can now send this payment link/invoice to the customer via FB.', 'success');
    }).catch(err => {
        showNotification('Error', 'Failed to copy invoice link', 'error');
    });
};
/* ==========================================================================
   PSGC ADDRESS API INTEGRATION
   ========================================================================== */
const PSGC_BASE = 'https://psgc.gitlab.io/api';

async function initPSGC() {
    try {
        const sel = document.getElementById('manProvince');
        if (!sel) return;

        // Lock to Laguna only
        sel.innerHTML = '<option value="043400000" selected>Laguna</option>';
        document.getElementById('manProvinceText').value = "Laguna";

        const citySel = document.getElementById('manMunicipality');
        citySel.innerHTML = '<option value="" disabled selected>Loading...</option>';
        document.getElementById('manBarangay').innerHTML = '<option value="" disabled selected>Barangay</option>';

        // Fetch Laguna Cities automatically
        const res = await fetch(`${PSGC_BASE}/provinces/043400000/cities-municipalities/`);
        const cities = await res.json();
        citySel.innerHTML = '<option value="" disabled selected>Municipality / City</option>';
        cities.sort((a, b) => a.name.localeCompare(b.name)).forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.code;
            opt.textContent = c.name;
            citySel.appendChild(opt);
        });

        document.getElementById('manMunicipality').addEventListener('change', async function () {
            document.getElementById('manMunicipalityText').value = this.options[this.selectedIndex].text;

            const brgySel = document.getElementById('manBarangay');
            brgySel.innerHTML = '<option value="" disabled selected>Barangay</option>';
            if (!this.value) return;
            const res = await fetch(`${PSGC_BASE}/cities-municipalities/${this.value}/barangays/`);
            const brgys = await res.json();
            brgys.sort((a, b) => a.name.localeCompare(b.name)).forEach(b => {
                const opt = document.createElement('option');
                opt.value = b.code;
                opt.textContent = b.name;
                brgySel.appendChild(opt);
            });
        });

        document.getElementById('manBarangay').addEventListener('change', function () {
            document.getElementById('manBarangayText').value = this.options[this.selectedIndex].text;
        });

    } catch (err) { console.error("PSGC Load Failed", err); }
}

document.addEventListener('DOMContentLoaded', initPSGC);

window.closeModal = window.closeModal || closeCalModal; // Fallback if global not exists
window.closeCalModal = closeCalModal;
window.toggleDateAvailability = toggleDateAvailability;
window.checkAvailabilityStatus = checkAvailabilityStatus;
window.openManualBookingModal = openManualBookingModal;
window.submitManualEvent = submitManualEvent;
window.unblockSelectedDate = unblockSelectedDate;
window.toggleOtherEventType = toggleOtherEventType;
window.updateCapacitySettings = updateCapacitySettings;
window.setReminder = setReminder;

async function updateCapacitySettings() {
    const maxBookings = document.getElementById('capMaxBookings').value;
    const autoBlock = document.getElementById('capAutoBlock').checked;

    if (window.apiAction) {
        const res = await window.apiAction('/caterer/api/calendar/capacity-settings', {
            method: 'POST',
            body: JSON.stringify({
                max_bookings_per_day: parseInt(maxBookings),
                auto_block_enabled: autoBlock
            }),
            muteToast: true
        });
        if (res) {
            showNotification("Success", "Capacity settings updated successfully.", "success");
            setTimeout(() => location.reload(), 1500); // Reload to reflect max capacity correctly on calendar
        }
    }
}

async function setReminder() {
    const bookingId = document.getElementById('evModalBookingId').value;
    if (!bookingId) return;

    if (window.apiAction) {
        const res = await window.apiAction(`/caterer/api/bookings/${bookingId}/reminders`, {
            method: 'POST'
        });
        if (res) {
            closeModal('eventModal');
        }
    }
}


// ROI Functions Removed

/**
 * Availability Management Helpers
 */
async function toggleDateAvailability(isAvailable) {
    const dateInput = document.getElementById("blockDate");
    const blockReasonInput = document.getElementById("blockReason");

    if (!dateInput || !dateInput.value) {
        showNotification("Error", "Please select a target date first.", "error");
        return;
    }

    let reasonText = "";
    if (!isAvailable) {
        reasonText = blockReasonInput ? blockReasonInput.value.trim() : "";
        if (!reasonText) {
            showNotification("Error", "Please provide a reason for blocking this date.", "error");
            if (blockReasonInput) blockReasonInput.focus();
            return;
        }
    }

    const payload = {
        date: dateInput.value,
        is_available: isAvailable,
        reason: isAvailable ? "" : reasonText
    };

    try {
        const response = await fetch("/caterer/api/availability/toggle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            showNotification("Success", `Date successfully ${isAvailable ? "opened" : "blocked"}!`, "success");
            if (window.fullCalendarInstance) {
                window.fullCalendarInstance.refetchEvents();
            }
            document.getElementById('availabilityForm').reset();
        } else {
            showNotification("Error", "Failed to update availability.", "error");
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
            if (window.fullCalendarInstance) {
                window.fullCalendarInstance.refetchEvents();
            }
            showNotification("Success", "Date unblocked successfully.", "success");
            closeModal('blockedDateModal');
        } else {
            showNotification("Error", "Failed to unblock date.", "error");
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

window.openSidebarEventModal = function (elem) {
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

function updateCapacityDisplay(data) {
    const dateStr = data.date;
    const count = data.booking_count;
    const max = data.max_capacity;

    const dayCell = document.querySelector(`[data-date="${dateStr}"]`);
    if (dayCell) {
        const indicator = dayCell.querySelector('.capacity-indicator');
        if (indicator) {
            indicator.textContent = `${count}/${max}`;
            if (count >= max) {
                indicator.style.color = '#ef4444';
            } else if (count >= max * 0.75) {
                indicator.style.color = '#f59e0b';
            } else {
                indicator.style.color = '#10b981';
            }
        }
    }
}

function updateVisibleCapacity(start, end) {
    const days = [];
    const current = new Date(start);
    while (current < end) {
        days.push(current.toISOString().split('T')[0]);
        current.setDate(current.getDate() + 1);
    }
}

window.closeModal = window.closeModal || closeCalModal;
window.closeCalModal = closeCalModal;
window.toggleDateAvailability = toggleDateAvailability;
window.checkAvailabilityStatus = checkAvailabilityStatus;
window.openManualBookingModal = openManualBookingModal;
window.submitManualEvent = submitManualEvent;
window.unblockSelectedDate = unblockSelectedDate;
window.getQuickQuotation = getQuickQuotation;
window.closeRoiBreakdown = closeRoiBreakdown;
window.toggleOtherEventType = toggleOtherEventType;
window.updateCapacitySettings = updateCapacitySettings;
window.setReminder = setReminder;

