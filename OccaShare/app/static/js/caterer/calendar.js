document.addEventListener('DOMContentLoaded', function () {
    const calendarEl = document.getElementById('calendar');
    if (calendarEl) {
        // Change default view based on screen width
        const initialView = window.innerWidth <= 768 ? 'listMonth' : 'dayGridMonth';
        
        const calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: initialView,
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek'
            },
            events: '/caterer/api/events',
            eventContent: function(arg) {
                const props = arg.event.extendedProps;
                const isBlocked = props.type === 'BLOCKED';
                const iconClass = isBlocked ? 'fas fa-ban' : 'fas fa-calendar-check';
                
                return {
                    html: `
                        <div class="custom-calendar-event" style="
                            display: flex; align-items: center; gap: 0.35rem; width: 100%;
                            padding: 0.2rem 0.4rem; border-radius: 6px; 
                            background-color: ${arg.event.backgroundColor}; 
                            color: ${arg.event.textColor || '#fff'}; 
                            border-left: 3px solid ${arg.event.borderColor || arg.event.backgroundColor};
                            font-size: 0.8rem; font-weight: 500; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
                        ">
                            <i class="${iconClass}" style="opacity: 0.8;"></i>
                            <span style="overflow: hidden; text-overflow: ellipsis;">${arg.event.title}</span>
                        </div>
                    `
                };
            },
            eventClick: function (info) {
                const today = new Date();
                today.setHours(0,0,0,0);
                if (info.event.start < today) {
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
                    return; 
                }
                
                const blockInput = document.getElementById('blockDate');
                const manInput = document.getElementById('manDate');
                if (blockInput) blockInput.value = info.dateStr;
                if (manInput) manInput.value = info.dateStr;
                
                openManualBookingModal();
            },
            height: 'auto',
            dayMaxEvents: true,
            windowResize: function(arg) {
                if (window.innerWidth <= 768) {
                    calendar.changeView('listMonth');
                } else {
                    calendar.changeView('dayGridMonth');
                }
            }
        });
        calendar.render();
    }

    // Initialize Manual Booking Validation
    if (window.ValidationManager) {
        window.manualBookingValidation = new window.ValidationManager('manualBookingForm', {
            'customer_name': { label: 'customer name', noSameParts: true },
            'customer_email': { label: 'email address' },
            'customer_contact': { phMobile: true, noRepetitive: true, maxLength: 11 },
            'event_name': { label: 'event name' },
            'guest_count': { numericOnly: true, min: 1, max: 100000, autoStop: true },
            'total_amount': { numericOnly: true, max: 10000000, autoStop: true },
            'event_date': { label: 'event date' }
        });
    }
    
    initCustomerDetection();

    // Proactive Numeric Blocking for Contact
    const contactInput = document.getElementById('manCustContact');
    if (contactInput) {
        contactInput.addEventListener('keydown', (e) => {
            const allowedKeys = ['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab', 'Enter'];
            if (!allowedKeys.includes(e.key) && !/[0-9]/.test(e.key) && !e.ctrlKey) {
                e.preventDefault();
            }
        });
    }

    // Initialize Listeners
    attachPackageListeners();
});

function attachPackageListeners() {
    const pkgSelect = document.getElementById('manPackage');
    const guestInput = document.getElementById('manGuests');
    const amountInput = document.getElementById('manAmount');
    if (!pkgSelect || !guestInput || !amountInput) return;

    // Listen to changes that affect price
    pkgSelect.addEventListener('change', () => {
        syncPackageMenus();
        
        const option = pkgSelect.options[pkgSelect.selectedIndex];
        const minGuests = parseInt(option.dataset.min) || 1;
        guestInput.min = minGuests;
        if (!guestInput.value || parseInt(guestInput.value) < minGuests) {
            guestInput.value = minGuests;
        }
        
        recalculateTotal();
    });
    guestInput.addEventListener('input', recalculateTotal);
    
    document.querySelectorAll('.man-menu-checkbox').forEach(cb => {
        cb.addEventListener('change', recalculateTotal);
    });

    // Initial calculation
    recalculateTotal();
}

/**
 * Synchronize checkboxes based on package menu items
 */
function syncPackageMenus() {
    const pkgSelect = document.getElementById('manPackage');
    if (!pkgSelect) return;
    
    const option = pkgSelect.options[pkgSelect.selectedIndex];
    if (!option.dataset.menus) return;

    try {
        const menuIds = JSON.parse(option.dataset.menus);
        // Clear all first
        document.querySelectorAll('.man-menu-checkbox').forEach(cb => cb.checked = false);
        
        // Check associated ones
        if (menuIds.length > 0) {
            menuIds.forEach(id => {
                const cb = document.querySelector(`.man-menu-checkbox[value="${id}"]`);
                if (cb) cb.checked = true;
            });
        }
    } catch (e) {
        console.error("Error syncing menus:", e);
    }
}

/**
 * Real-time Accurate Pricing Calculation
 */
function recalculateTotal() {
    const pkgSelect = document.getElementById('manPackage');
    const guestInput = document.getElementById('manGuests');
    const amountInput = document.getElementById('manAmount');
    
    if (!pkgSelect || !guestInput || !amountInput) return;

    const guests = parseInt(guestInput.value) || 0;
    const option = pkgSelect.options[pkgSelect.selectedIndex];
    const basePrice = parseFloat(option.dataset.price) || 0;
    const unit = option.dataset.unit || 'fixed';
    const minGuests = parseInt(option.dataset.min) || 1;

    let total = 0;

    // 1. Calculate Package Price
    if (unit === 'per_guest') {
        total = basePrice * guests;
    } else {
        total = basePrice;
    }

    // 2. Add Extra Menu Add-ons Price
    let includedMenuIds = [];
    if (option.dataset.menus) {
        try {
            includedMenuIds = JSON.parse(option.dataset.menus).map(id => id.toString());
        } catch (e) {}
    }

    document.querySelectorAll('.man-menu-checkbox:checked').forEach(cb => {
        // Only add price if it's NOT part of the package inclusions
        if (!includedMenuIds.includes(cb.value.toString())) {
            total += parseFloat(cb.dataset.price) || 0;
        }
    });

    // 3. Update UI - Fixed Formatting to match js-format-comma expectation
    amountInput.value = total.toLocaleString('en-US', { minimumFractionDigits: 2 });
    
    // 4. Smart Validation: Min Guests Enforcement
    if (pkgSelect.value && guests < minGuests) {
        if (window.manualBookingValidation) {
            window.manualBookingValidation.setError(guestInput, `Minimum of ${minGuests} guests required for this package.`);
        }
    } else {
        if (window.manualBookingValidation) {
            window.manualBookingValidation.clearError(guestInput);
        }
    }

    // Trigger validation update
    amountInput.dispatchEvent(new Event('input', { bubbles: true }));

    // --- SMART PRICING UI UPDATE ---
    const quoteBtn = document.getElementById('btnQuickQuote');
    const roiLabel = document.getElementById('roiPreviewLabel');
    if (pkgSelect.value) {
        if (quoteBtn) quoteBtn.style.display = 'inline-block';
        if (roiLabel) {
            roiLabel.style.display = 'block';
            roiLabel.innerHTML = '<i class="fas fa-sync fa-spin"></i> Calculating ROI...';
            
            // Debounced ROI Preview
            clearTimeout(window.roiPreviewTimeout);
            window.roiPreviewTimeout = setTimeout(async () => {
                try {
                    const resp = await fetch(`/caterer/api/quick-quotation/${pkgSelect.value}?pax=${guests}`);
                    if (resp.ok) {
                        const data = await resp.json();
                        roiLabel.innerHTML = `Calc. Profit: ₱${data.roi.toLocaleString()} (${data.markup_label})`;
                    }
                } catch (e) {}
            }, 500);
        }
    } else {
        if (quoteBtn) quoteBtn.style.display = 'none';
        if (roiLabel) roiLabel.style.display = 'none';
    }
}

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
        list.innerHTML = '';
        data.breakdown.forEach(item => {
            const itemCost = item.cost_per_pax * pax;
            list.innerHTML += `
                <div style="background: white; padding: var(--space-md); border-radius: var(--radius-sm); border: 1px solid var(--color-neutral-100); display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: 700; color: var(--color-neutral-700); font-size: var(--text-sm);">${item.name}</div>
                        <div style="font-size: var(--text-xs); color: var(--color-neutral-400);">Total Dish Cost (x${pax})</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-weight: 900; color: var(--color-neutral-700);">₱${itemCost.toLocaleString()}</div>
                        <div style="font-size: var(--text-xs); color: var(--color-info); font-weight: 700;">₱${item.cost_per_pax.toFixed(2)} / pax</div>
                    </div>
                </div>
            `;
        });

        const modal = document.getElementById('roiBreakdownModal');
        modal.style.display = 'flex';
        setTimeout(() => modal.classList.add('active'), 10);
        
        // Update the preview label on the main modal too
        const roiLabel = document.getElementById('roiPreviewLabel');
        if (roiLabel) {
            roiLabel.innerHTML = `Calc. Profit: ₱${data.roi.toLocaleString()} (${data.markup_label})`;
        }

    } catch (e) {
        console.error(e);
        alert('Failed to fetch quotation breakdown');
    }
}

function closeRoiBreakdown() {
    const modal = document.getElementById('roiBreakdownModal');
    modal.classList.remove('active');
    setTimeout(() => modal.style.display = 'none', 400);
}

function showEventDetails(event) {
    const props = event.extendedProps;
    const modalTitle = document.getElementById('calModalTitle');
    if (modalTitle) modalTitle.textContent = event.title || 'Event Details';

    document.getElementById('currentBookingId').value = event.id;
    document.getElementById('detCustomer').textContent = props.customer || '---';
    document.getElementById('detType').textContent = props.type || '---';
    document.getElementById('detDateTime').textContent = event.start.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    }) + ' at ' + (props.time || 'TBD');
    document.getElementById('detVenue').textContent = props.venue || '---';
    document.getElementById('detPackage').textContent = (props.guests || '0') + ' Guests - ' + (props.package || '---');

    // Disable reminder for past events
    const reminderBtn = document.querySelector('#eventModal .btn-primary');
    const today = new Date();
    today.setHours(0,0,0,0);
    if (event.start < today) {
        if (reminderBtn) reminderBtn.style.display = 'none';
    } else {
        if (reminderBtn) reminderBtn.style.display = 'block';
    }

    document.getElementById('eventModal').style.display = 'flex';
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            document.getElementById('eventModal').classList.add('active');
        });
    });
}

let currentBlockedDate = '';

function showBlockedDetails(event) {
    const props = event.extendedProps;
    document.getElementById('detBlockedReason').textContent = props.reason || 'No reason provided';
    document.getElementById('detBlockedDate').textContent = event.start.toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
    
    currentBlockedDate = event.startStr.split('T')[0];
    
    document.getElementById('blockedDateModal').style.display = 'flex';
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            document.getElementById('blockedDateModal').classList.add('active');
        });
    });
}

function openManualBookingModal(slotStr = null) {
    const modal = document.getElementById('manualBookingModal');
    if (!modal) return;
    document.getElementById('manualBookingForm').reset();
    
    const errorDrawer = document.getElementById('manualBookingError');
    if (errorDrawer) errorDrawer.style.display = 'none';
    
    if (slotStr) {
        document.getElementById('manDate').value = slotStr;
    }
    
    if (document.getElementById('manAmount')) {
        document.getElementById('manAmount').value = '0.00';
    }

    // Reset checkmarks
    document.querySelectorAll('.man-menu-checkbox').forEach(cb => cb.checked = false);

    // Initial validation check
    setTimeout(() => {
        recalculateTotal();
        document.getElementById('manualBookingForm').dispatchEvent(new Event('input', { bubbles: true }));
    }, 50);

    modal.style.display = 'flex';
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            modal.classList.add('active');
        });
    });
}

function clearErrorDrawer() {
    const drawer = document.getElementById('manualBookingError');
    if (drawer) {
        drawer.style.display = 'none';
        drawer.innerHTML = '';
    }
}

function showErrorInDrawer(message) {
    const drawer = document.getElementById('manualBookingError');
    if (drawer) {
        drawer.innerHTML = `<i class="fas fa-exclamation-circle"></i> <span>${message}</span>`;
        drawer.style.display = 'flex';
        document.querySelector('#manualBookingModal .occ-modal-body').scrollTop = 0;
    }
}

async function unblockSelectedDate() {
    if (!currentBlockedDate) return;
    try {
        const response = await fetch('/caterer/api/availability/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: currentBlockedDate, is_available: true, reason: '' })
        });
        if (response.ok) {
            location.reload();
        } else {
            window.showError('Failed to unblock date.');
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

async function submitManualEvent(e) {
    e.preventDefault();
    clearErrorDrawer();
    
    const guests = parseInt(document.getElementById('manGuests').value) || 0;
    const amountInputString = document.getElementById('manAmount').value || '0.00';
    const amount = parseFloat(amountInputString.replace(/,/g, '').replace('₱', '').trim()) || 0;
    
    if (guests < 1) {
        showErrorInDrawer('Oops! Guest count must be at least 1 pax.');
        return;
    }
    
    if (amount <= 0) {
        showErrorInDrawer('Invalid Amount! Total price must be greater than ₱0.00.');
        return;
    }

    const eventDateStr = document.getElementById('manDate').value;
    if (!eventDateStr) {
        showErrorInDrawer('Please select a valid date for the event.');
        return;
    }

    const selectedDate = new Date(eventDateStr);
    const today = new Date();
    today.setHours(0,0,0,0);
    if (selectedDate < today) {
        showErrorInDrawer('Booking Error: You cannot create bookings for past dates.');
        return;
    }

    let eventType = document.getElementById('manEventType').value;
    if (eventType === 'Other') {
        eventType = document.getElementById('manOtherType').value.trim();
        if (!eventType) {
            showErrorInDrawer('Please specify the "Other" event type name.');
            return;
        }
    }

    const btn = document.getElementById('btnSubmitManual');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    
    const packageId = document.getElementById('manPackage').value;
    const selectedMenus = Array.from(document.querySelectorAll('.man-menu-checkbox:checked')).map(cb => parseInt(cb.value));

    const payload = {
        customer_name: document.getElementById('manCustName').value.trim(),
        customer_email: document.getElementById('manCustEmail').value.trim() || null,
        customer_contact: document.getElementById('manCustContact').value.trim() || null,
        event_name: document.getElementById('manEventName').value,
        event_type: eventType,
        event_date: eventDateStr,
        event_time: document.getElementById('manTime').value || null,
        venue_address: document.getElementById('manVenue').value || null,
        guest_count: guests,
        total_amount: amount,
        package_id: packageId ? parseInt(packageId) : null,
        menu_items: selectedMenus
    };
    
    try {
        const response = await fetch('/caterer/api/bookings/manual', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        if (response.ok) {
            window.showSuccess('Walk-in booking created successfully!');
            setTimeout(() => location.reload(), 1500);
        } else {
            window.showError(data.detail || 'Failed to create booking.');
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    } catch (error) {
        console.error('Error:', error);
        window.showError('An error occurred.');
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

async function setReminder() {
    const bookingId = document.getElementById('currentBookingId').value;
    const btn = document.querySelector('#eventModal .btn-primary');
    if (!btn) return;

    // Request Notification Permission
    if ("Notification" in window) {
        if (Notification.permission !== "granted" && Notification.permission !== "denied") {
            const permission = await Notification.requestPermission();
            if (permission !== "granted") {
                window.showError('Notification permission denied. Alarms will not sound.');
            }
        }
    }

    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Setting...';

    try {
        const response = await fetch(`/caterer/api/bookings/${bookingId}/reminders`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.status === 'success') {
            window.showSuccess('Reminder set! You will see it in your notifications.');
            
            // Trigger Local "Alarm" Preview
            if ("Notification" in window && Notification.permission === "granted") {
                const eventName = document.getElementById('calModalTitle').textContent;
                const eventDate = document.getElementById('detDateTime').textContent;
                
                // Play notification sound
                const audio = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');
                audio.play().catch(e => console.log("Audio play failed, needs user interaction first."));

                new Notification("OccaServe Reminder Set! 🔔", {
                    body: `Alarm active for: ${eventName}\nScheduled for: ${eventDate}`,
                    icon: '/static/img/logo.png' // Fallback to icon if available
                });
            }

            closeModal();
            setTimeout(() => location.reload(), 2000);
        } else {
            window.showError(data.message || 'Failed to set reminder.');
        }
    } catch (error) {
        console.error('Error:', error);
        window.showError('Failed to set reminder.');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

function closeModal() {
    document.querySelectorAll('.occ-modal-overlay').forEach(m => {
        m.classList.remove('active');
        setTimeout(() => {
            if (!m.classList.contains('active')) {
                m.style.display = 'none';
            }
        }, 400);
    });
}

async function toggleDateAvailability(isAvailable) {
    const dateInput = document.getElementById('blockDate');
    const reasonInput = document.getElementById('blockReason');

    if (!dateInput) return;

    const date = dateInput.value;
    const reason = reasonInput ? reasonInput.value : '';

    if (!date) {
        window.showError('Please select a date first.');
        return;
    }

    if (!isAvailable) {
        const selectedDate = new Date(date);
        const today = new Date();
        today.setHours(0,0,0,0);
        if (selectedDate < today) {
            window.showError('You cannot block past dates.');
            return;
        }
    }

    try {
        const response = await fetch('/caterer/api/availability/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date, is_available: isAvailable, reason })
        });

        if (response.ok) {
            window.showSuccess(`Date successfully ${isAvailable ? 'unblocked' : 'blocked'}!`);
            setTimeout(() => location.reload(), 1000);
        } else {
            window.showError('Failed to update availability.');
        }
    } catch (error) {
        console.error('Error:', error);
        window.showError('An error occurred.');
    }
}

function toggleOtherEventType() {
    const select = document.getElementById('manEventType');
    const otherDiv = document.getElementById('otherEventTypeDiv');
    const otherInput = document.getElementById('manOtherType');
    
    if (select.value === 'Other') {
        otherDiv.style.display = 'block';
        otherInput.required = true;
    } else {
        otherDiv.style.display = 'none';
        otherInput.required = false;
        otherInput.value = '';
    }
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

window.showEventDetails = showEventDetails;
window.showBlockedDetails = showBlockedDetails;
window.setReminder = setReminder;
window.closeModal = closeModal;
window.toggleDateAvailability = toggleDateAvailability;
window.openManualBookingModal = openManualBookingModal;
window.submitManualEvent = submitManualEvent;
window.unblockSelectedDate = unblockSelectedDate;
window.toggleOtherEventType = toggleOtherEventType;

function initCustomerDetection() {
    let timeoutId;
    const nameInput = document.getElementById('manCustName');
    const emailInput = document.getElementById('manCustEmail');
    const contactInput = document.getElementById('manCustContact');
    const badge = document.getElementById('userDetectionBadge');
    
    if (!nameInput || !emailInput || !badge) return;

    function checkUser() {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(async () => {
            const name = nameInput.value.trim();
            const email = emailInput.value.trim();
            
            if (!name && !email) {
                badge.style.display = 'none';
                return;
            }

            badge.style.display = 'flex';
            badge.className = 'detection-badge-container';
            badge.style.background = 'var(--color-neutral-50)';
            badge.style.borderLeftColor = 'var(--color-neutral-300)';
            
            badge.innerHTML = `
                <div class="badge-spinner"><i class="fas fa-circle-notch fa-spin"></i></div>
                <div class="badge-content">
                    <span class="badge-title">AI Scanner</span>
                    <span style="color: var(--color-neutral-500); font-size: 11px;">Scanning platform records...</span>
                </div>
            `;

            try {
                const response = await fetch('/caterer/api/check-customer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email })
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.exists) {
                        badge.style.display = 'flex';
                        if (data.is_taken) {
                            badge.style.background = '#fff1f2';
                            badge.style.borderLeftColor = '#e11d48';
                            badge.innerHTML = `
                                <div class="badge-spinner" style="color: #e11d48;"><i class="fas fa-exclamation-triangle"></i></div>
                                <div class="badge-content">
                                    <span class="badge-title" style="color: #e11d48;">System Warning</span>
                                    <span style="color: #9f1239; font-size: 11px;">Email is registered to <b>${data.name}</b>.</span>
                                </div>
                            `;
                        } else {
                            badge.style.background = '#f0f9ff';
                            badge.style.borderLeftColor = '#0284c7';
                            badge.innerHTML = `
                                <div class="badge-spinner" style="color: #0284c7;"><i class="fas fa-fingerprint"></i></div>
                                <div class="badge-content">
                                    <span class="badge-title" style="color: #0284c7;">Match Detected</span>
                                    <span style="color: #0369a1; font-size: 11px;">Found <b>${data.name}</b>. Linking enabled.</span>
                                </div>
                            `;
                        }
                        
                        // Smart Auto-fill
                        if (data.exists && !data.is_taken) {
                             if (!nameInput.value || nameInput.value.length < 3) nameInput.value = data.name;
                             if (!contactInput.value && data.contact) contactInput.value = data.contact;
                             
                             nameInput.dispatchEvent(new Event('input', { bubbles: true }));
                             if (contactInput.value) contactInput.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    } else {
                        badge.style.background = '#f0fdf4';
                        badge.style.borderLeftColor = '#16a34a';
                        badge.innerHTML = `
                            <div class="badge-spinner" style="color: #16a34a;"><i class="fas fa-user-plus"></i></div>
                            <div class="badge-content">
                                <span class="badge-title" style="color: #16a34a;">New Registry</span>
                                <span style="color: #166534; font-size: 11px;">Unique user. Ready for registration.</span>
                            </div>
                        `;
                    }
                }
            } catch (err) {
                badge.style.display = 'none';
            }
        }, 600);
    }

    nameInput.addEventListener('input', checkUser);
    emailInput.addEventListener('input', checkUser);
}

window.openSidebarEventModal = function(elem) {
    const ds = elem.dataset;
    const modalTitle = document.getElementById('calModalTitle');
    if (modalTitle) modalTitle.textContent = ds.title || 'Event Details';

    document.getElementById('currentBookingId').value = ds.id || '';
    document.getElementById('detCustomer').textContent = ds.customer || '---';
    document.getElementById('detType').textContent = ds.type || '---';
    document.getElementById('detDateTime').textContent = ds.datetime || '---';
    document.getElementById('detVenue').textContent = ds.venue || '---';
    document.getElementById('detPackage').textContent = ds.package || '---';

    const reminderBtn = document.querySelector('#eventModal .btn-primary');
    if (reminderBtn) {
        reminderBtn.style.display = 'block';
    }

    document.getElementById('eventModal').style.display = 'flex';
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            document.getElementById('eventModal').classList.add('active');
        });
    });
};
