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
                // Custom render for the event banners to ensure they look premium
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
                    return; // Prevent clicking on any past event or blocked date natively
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
                    // Modern clean way: just don't do anything or show a very subtle log
                    return; 
                }
                
                // Pre-fill date in manual booking and blocking form
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
    setupRealTimeValidation();
});

function setupRealTimeValidation() {
    const guestsInput = document.getElementById('manGuests');
    const amountInput = document.getElementById('manAmount');
    const submitBtn = document.getElementById('btnSubmitManual');
    
    function setInputErrorState(input, isError) {
        if (isError) {
            input.style.borderColor = '#ef4444';
            input.style.backgroundColor = '#fef2f2';
        } else {
            input.style.borderColor = '';
            input.style.backgroundColor = '';
        }
    }
    
    function validateInputs(e) {
        let isValid = true;
        clearErrorDrawer();
        
        // Contact Format Validation
        const contactInput = document.getElementById('manCustContact');
        if (contactInput && contactInput.value !== '') {
            let val = contactInput.value.replace(/\D/g, ''); 
            contactInput.value = val;
            if (val.length !== 11 || !val.startsWith('09')) {
                showErrorInDrawer('Contact Number must be a valid 11-digit number starting with 09.');
                isValid = false;
                setInputErrorState(contactInput, true);
            } else {
                setInputErrorState(contactInput, false);
            }
        } else if (contactInput) {
            setInputErrorState(contactInput, false);
        }

        // Name Gibberish Validation
        const nameInput = document.getElementById('manCustName');
        if (nameInput && nameInput.value.trim() !== '') {
            const val = nameInput.value;
            // Catch 4+ repeating characters like aaaa
            if (/(.)\1{3,}/.test(val)) {
                showErrorInDrawer('Invalid Name! Consecutive repeating characters are not allowed.');
                isValid = false;
                setInputErrorState(nameInput, true);
            } else {
                setInputErrorState(nameInput, false);
            }
        }

        // Hard limits during typing
        if (guestsInput && guestsInput.value !== '') {
            let guestsStr = guestsInput.value;
            let guests = parseInt(guestsStr);
            if (guests > 100000) {
                // If they typed something that made it > 100000, revert the last character
                guestsInput.value = guestsStr.slice(0, -1);
                guests = parseInt(guestsInput.value) || 0;
            }
            if (guests < 1 || isNaN(guests)) {
                showErrorInDrawer('Invalid Guest Count! Must be at least 1.');
                isValid = false;
                setInputErrorState(guestsInput, true);
            } else {
                setInputErrorState(guestsInput, false);
            }
        } else if(guestsInput) {
            setInputErrorState(guestsInput, false);
        }
        
        // Process Amount Currency limits cleanly
        if (amountInput && amountInput.value !== '') {
            // Because formatting has commas and symbols, filter natively
            let rawStr = amountInput.value.replace(/[^\d.]/g, '');
            let amount = parseFloat(rawStr) || 0;
            if (amount > 10000000) {
                rawStr = rawStr.slice(0, -1);
                amount = parseFloat(rawStr) || 0;
                amountInput.value = rawStr; // Keep caret flow normally
            }
            if (amount <= 0 || isNaN(amount)) {
                showErrorInDrawer('Invalid Amount! Must be at least ₱1.00');
                isValid = false;
                setInputErrorState(amountInput, true);
            } else {
                setInputErrorState(amountInput, false);
            }
        } else if(amountInput) {
            setInputErrorState(amountInput, false);
        }
        
        if (submitBtn) {
            submitBtn.disabled = !isValid;
            submitBtn.style.opacity = isValid ? '1' : '0.5';
        }
    }

    function preventInvalidChars(e) {
        if (['e', 'E', '+', '-'].includes(e.key)) {
            e.preventDefault();
        }
    }

    if (guestsInput) {
        guestsInput.addEventListener('input', validateInputs);
        guestsInput.addEventListener('keydown', preventInvalidChars);
    }
    if (amountInput) {
        amountInput.addEventListener('input', validateInputs);
        amountInput.addEventListener('keydown', preventInvalidChars);
        
        // Dynamic string currency formatting handles caret jumping when blurred
        amountInput.addEventListener('blur', function() {
            let val = parseCurrency(this.value);
            if(val > 0) this.value = formatCurrency(val);
        });
        amountInput.addEventListener('focus', function() {
            let parsed = parseCurrency(this.value);
            if(parsed > 0) this.value = parsed;
        });
    }

    // Attach listeners conditionally to ensure coverage if DOM repaints
    const contactInput = document.getElementById('manCustContact');
    if (contactInput) contactInput.addEventListener('input', validateInputs);
    
    const nameInput = document.getElementById('manCustName');
    if (nameInput) nameInput.addEventListener('input', validateInputs);
    
    attachPackageListeners();
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
}

let currentBlockedDate = '';

function showBlockedDetails(event) {
    const props = event.extendedProps;
    document.getElementById('detBlockedReason').textContent = props.reason || 'No reason provided';
    document.getElementById('detBlockedDate').textContent = event.start.toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
    
    // YYYY-MM-DD format for unblocking
    currentBlockedDate = event.startStr.split('T')[0];
    
    document.getElementById('blockedDateModal').style.display = 'flex';
}

function openManualBookingModal(slotStr = null) {
    const modal = document.getElementById('manualBookingModal');
    if (!modal) return;
    document.getElementById('manualBookingForm').reset();
    document.getElementById('manualBookingError').style.display = 'none';
    
    // Default to proper date if slot provided
    if (slotStr) {
        document.getElementById('manDate').value = slotStr;
    }
    
    // Clear formatted fields
    if(document.getElementById('manAmount')) {
        document.getElementById('manAmount').style.borderColor = '';
        document.getElementById('manAmount').style.backgroundColor = '';
    }
    document.getElementById('btnSubmitManual').disabled = true;
    document.getElementById('btnSubmitManual').style.opacity = '0.5';

    modal.style.display = 'flex';
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
        // Scroll to top of modal to see error
        document.querySelector('#manualBookingModal .calendar-modal-content').scrollTop = 0;
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
    
    // Validate inputs
    const guests = parseInt(document.getElementById('manGuests').value);
    const amountInputString = document.getElementById('manAmount').value;
    const amount = parseCurrency(amountInputString);
    
    if (guests < 1) {
        showErrorInDrawer('Oops! Guest count must be at least 1 pax.');
        return;
    }
    
    if (amount <= 0) {
        showErrorInDrawer('Invalid Amount! Total price must be greater than ₱0.00.');
        return;
    }

    if (!eventDateStr) {
        showErrorInDrawer('Please select a valid date for the event.');
        return;
    }

    const selectedDate = new Date(eventDateStr);
    const today = new Date();
    today.setHours(0,0,0,0);
    if (selectedDate < today) {
        showErrorInDrawer('Blocking Error: You cannot create bookings for past dates.');
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
        customer_contact: document.getElementById('manCustContact').value.trim() || null,
        event_name: document.getElementById('manEventName').value,
        event_type: eventType,
        event_date: document.getElementById('manDate').value,
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
            closeModal();
            setTimeout(() => location.reload(), 2000); // To update notification count
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
    document.querySelectorAll('.calendar-modal').forEach(m => m.style.display = 'none');
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

    // Validation to prevent blocking past dates unless we're unblocking
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

// Close on escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

// Global exposure
window.showEventDetails = showEventDetails;
window.showBlockedDetails = showBlockedDetails;
window.setReminder = setReminder;
window.closeModal = closeModal;
window.toggleDateAvailability = toggleDateAvailability;
window.openManualBookingModal = openManualBookingModal;
window.submitManualEvent = submitManualEvent;
window.unblockSelectedDate = unblockSelectedDate;
window.toggleOtherEventType = toggleOtherEventType;

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
        // Just keep it enabled since upcoming list doesn't show past events anyway
        reminderBtn.style.display = 'block';
    }

    document.getElementById('eventModal').style.display = 'flex';
};
