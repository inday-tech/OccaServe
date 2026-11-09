document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('detailsForm');
    const eventList = document.getElementById('booking-event-list');
    const eventsInput = document.getElementById('booking-events-json');
    const addEventButton = document.getElementById('add-booking-event');
    if (!form || !eventList || !eventsInput) return;

    const options = window.bookingEventOptions || {};
    const packages = Array.isArray(options.packages) ? options.packages : [];
    const menuItems = Array.isArray(options.menu_items) ? options.menu_items : [];
    const equipmentItems = Array.isArray(options.equipment) ? options.equipment : [];
    const serviceItems = Array.isArray(options.services) ? options.services : [];
    const legacyDate = document.getElementById('event_date');
    const legacyTime = document.getElementById('event_time');
    const legacyEndTime = document.getElementById('event_end_time');
    const legacyPackage = document.getElementById('package_id_hidden');
    const legacyGuests = document.getElementById('guest_count');
    const legacyGuestDisplay = document.getElementById('guest_count_display');
    const eventType = document.getElementById('event_type_hidden');
    const bookingId = form.querySelector('[name="booking_id"]')?.value || '';
    const eventStorageKey = `occaserve:booking-event-schedules:${window.catererId || ''}:${bookingId || legacyPackage?.value || ''}`;
    const submitButton = document.getElementById('submitBtn');
    const availability = new Map();
    let eventSequence = 0;

    const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[character]);
    const money = amount => `₱${Number(amount || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    const nextEventId = () => `event-${Date.now()}-${++eventSequence}`;
    const getPackage = id => packages.find(item => String(item.id) === String(id));
    const getSelected = (event, key) => new Set((Array.isArray(event[key]) ? event[key] : []).map(Number));
    const packageAddon = (pkg, key, id) => (pkg?.[key] || []).find(item => Number(item.id) === Number(id) && item.enabled);
    const packageRate = pkg => {
        const price = Number(pkg.price_per_head || pkg.price || 0);
        const fixed = String(pkg.pricing_mode || '').toLowerCase() === 'fixed' ||
            String(pkg.price_unit || '').toLowerCase() !== 'per_guest';
        if (fixed) {
            const guests = Number(pkg.min_guests || 0);
            return `${money(pkg.price || pkg.price_per_head)}${Number(pkg.additional_guest_price || 0) > 0 ? ` · +${money(pkg.additional_guest_price)}/extra guest` : ''}`;
        }
        return `${money(price)}/guest`;
    };
    const itemPrice = (item, pkg) => {
        const configuredAddon = packageAddon(pkg, 'menu_addons', item.id);
        if (item.is_addon) return Number(configuredAddon ? configuredAddon.price : (item.addon_price || item.price || 0));
        if (String(pkg?.pricing_mode || '').toLowerCase() === 'customizable' && Number(item.upgrade_fee) > 0) {
            return Number(item.upgrade_fee);
        }
        return Number(item.price || item.upgrade_fee || 0);
    };
    const menuItemsForEvent = event => {
        const pkg = getPackage(event.package_id);
        const allowed = (pkg?.allowed_menu_ids || []).map(Number);
        let items = String(pkg?.pricing_mode || '').toLowerCase() === 'customizable' && allowed.length
            ? menuItems.filter(item => allowed.includes(Number(item.id)))
            : menuItems;
        if ((pkg?.menu_addons || []).length) {
            const allowedAddonIds = new Set(pkg.menu_addons.filter(item => item.enabled).map(item => Number(item.id)));
            items = items.filter(item => !item.is_addon || allowedAddonIds.has(Number(item.id)));
        }
        return items;
    };
    const optionsForTime = () => Array.from(legacyTime?.options || [])
        .filter(option => option.value)
        .map(option => ({ value: option.value, label: option.textContent.trim() }));
    const timeOptions = optionsForTime();
    let restoredEvents = [];
    try {
        const savedState = JSON.parse(sessionStorage.getItem(
            eventStorageKey
        ) || 'null');
        const parsedEvents = Array.isArray(savedState) ? savedState : [];
        if (Array.isArray(parsedEvents)) restoredEvents = parsedEvents;
    } catch (error) {
        console.warn('Could not restore saved event schedules:', error);
    }
    const storedEvents = Array.isArray(window.initialBookingEvents) ? window.initialBookingEvents : [];
    const initialData = restoredEvents.length ? restoredEvents : storedEvents;
    const firstPackage = getPackage(legacyPackage?.value || window.currentPackageId);
    const makeEvent = (source = {}) => {
        const pkg = getPackage(source.package_id || source.packageId) || firstPackage || packages[0];
        const selectedMenuIds = Array.isArray(source.menu_ids) ? source.menu_ids :
            (Array.isArray(source.menu_item_ids) ? source.menu_item_ids : (pkg?.included_menu_ids || []));
        return {
            id: String(source.id || nextEventId()),
            event_date: String(Object.prototype.hasOwnProperty.call(source, 'event_date') ? source.event_date : (source.date || legacyDate?.value || '')),
            ingress: String(Object.prototype.hasOwnProperty.call(source, 'ingress') ? source.ingress : (source.event_time || legacyTime?.value || '')),
            egress: String(Object.prototype.hasOwnProperty.call(source, 'egress') ? source.egress : (source.event_end_time || legacyEndTime?.value || '')),
            guest_count: Math.max(1, Number(source.guest_count || legacyGuests?.value || 1)),
            package_id: pkg ? Number(pkg.id) : '',
            menu_ids: selectedMenuIds.map(Number),
            equipment_ids: (source.equipment_ids || []).map(Number),
            service_ids: (source.service_ids || []).map(Number),
            availability: null,
            availabilityMessage: ''
        };
    };
    const events = initialData.length ? initialData.map(makeEvent) : [makeEvent()];

    const isIncluded = (pkg, id, key) => (pkg?.[key] || []).some(value => Number(value) === Number(id));
    const packagesForEvent = event => {
        const guests = Number(event.guest_count || 0);
        const selectedDate = event.event_date ? new Date(`${event.event_date}T00:00:00`) : null;
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return packages.filter(pkg => {
            const min = Number(pkg.min_guests || 1);
            const max = Number(pkg.max_guests || 999999);
            const leadTime = Number(pkg.booking_lead_time || 0);
            const earliestDate = new Date(today);
            earliestDate.setDate(earliestDate.getDate() + leadTime);
            return guests >= min && guests <= max && Number(pkg.service_duration) > 0 &&
                (!selectedDate || selectedDate >= earliestDate);
        });
    };
    const selectedEventPrice = event => {
        const pkg = getPackage(event.package_id);
        if (!pkg) return { subtotal: 0, package: 0, menu: 0, equipment: 0, services: 0 };
        const guests = Math.max(1, Number(event.guest_count || 1));
        const mode = String(pkg.pricing_mode || (pkg.price_unit === 'per_guest' ? 'per_pax' : 'fixed')).toLowerCase();
        let packageTotal;
        if (mode === 'fixed' || String(pkg.price_unit || '').toLowerCase() !== 'per_guest') {
            packageTotal = Number(pkg.price || pkg.price_per_head || 0) +
                Math.max(0, guests - Number(pkg.min_guests || 0)) * Number(pkg.additional_guest_price || 0);
        } else {
            packageTotal = Number(pkg.price_per_head || pkg.price || 0) * guests;
        }
        const menuTotal = menuItemsForEvent(event).reduce((sum, item) => {
            if (!getSelected(event, 'menu_ids').has(Number(item.id)) || isIncluded(pkg, item.id, 'included_menu_ids')) return sum;
            const perGuest = ['per_pax', 'per_guest', 'per_person'].includes(String(item.pricing_unit || '').toLowerCase());
            return sum + itemPrice(item, pkg) * (perGuest ? guests : 1);
        }, 0);
        const equipmentTotal = equipmentItems.reduce((sum, item) => {
            if (!getSelected(event, 'equipment_ids').has(Number(item.id)) || isIncluded(pkg, item.id, 'included_equipment_ids')) return sum;
            return sum + Number(packageAddon(pkg, 'equipment_addons', item.id)?.price ?? item.price ?? 0);
        }, 0);
        const serviceTotal = serviceItems.reduce((sum, item) => {
            if (!getSelected(event, 'service_ids').has(Number(item.id)) || isIncluded(pkg, item.id, 'included_service_ids')) return sum;
            const perGuest = ['per_pax', 'per_guest', 'per_person'].includes(String(item.unit_type || '').toLowerCase());
            return sum + Number(packageAddon(pkg, 'service_addons', item.id)?.price ?? item.price ?? 0) * (perGuest ? guests : 1);
        }, 0);
        return {
            package: packageTotal,
            menu: menuTotal,
            equipment: equipmentTotal,
            services: serviceTotal,
            subtotal: packageTotal + menuTotal + equipmentTotal + serviceTotal
        };
    };

    const formatInclusions = pkg => {
        const groups = pkg.grouped_inclusions || {};
        const names = ['food', 'services', 'equipment'].flatMap(group =>
            (groups[group] || []).map(item => item.name)
        );
        return names.length ? `Includes: ${names.slice(0, 5).map(escapeHtml).join(', ')}${names.length > 5 ? ` +${names.length - 5} more` : ''}` : 'Package inclusions confirmed by caterer';
    };

    const selectedCard = (event, pkg) => String(event.package_id) === String(pkg.id);
    const renderPackages = event => {
        const eligible = packagesForEvent(event);
        if (event.availability === false) {
            return '<p class="booking-event-status is-error">No package can be selected until this date and time is available.</p>';
        }
        if (!eligible.length) {
            return '<p class="booking-event-status is-error">No active package supports this guest count and service duration.</p>';
        }
        return `<div class="booking-package-grid">${eligible.map(pkg => {
            const locked = event.availability !== true;
            const image = pkg.image_url
                ? `<img src="${escapeHtml(pkg.image_url)}" alt="" loading="lazy">`
                : '<span class="booking-package-image-placeholder" aria-hidden="true"><i class="fas fa-utensils"></i></span>';
            return `<label class="booking-package-option${selectedCard(event, pkg) ? ' is-selected' : ''}${locked ? ' is-unavailable' : ''}">
                <input type="radio" id="${escapeHtml(event.id)}-package-${Number(pkg.id)}" name="package-${escapeHtml(event.id)}" value="${Number(pkg.id)}" ${selectedCard(event, pkg) ? 'checked' : ''} ${locked ? 'disabled' : ''}>
                ${image}
                <span class="booking-package-info">
                    <span class="booking-package-name">${escapeHtml(pkg.name)}</span>
                    <span class="booking-package-meta">${packageRate(pkg)} · ${Number(pkg.min_guests || 1)}–${Number(pkg.max_guests || 999999)} guests · ${Number(pkg.service_duration)}-hour service</span>
                    <span class="booking-package-inclusions">${formatInclusions(pkg)}</span>
                </span>
            </label>`;
        }).join('')}</div>`;
    };
    const renderMenuChoices = event => {
        const availableMenuItems = menuItemsForEvent(event);
        if (!availableMenuItems.length) return '<p class="booking-event-status">No additional food options are currently listed for this package.</p>';
        const pkg = getPackage(event.package_id);
        const selected = getSelected(event, 'menu_ids');
        return `<div class="booking-menu-grid">${availableMenuItems.map(item => {
            const included = isIncluded(pkg, item.id, 'included_menu_ids');
            const price = itemPrice(item, pkg);
            const serving = [item.serving_size, item.serving_style].filter(Boolean).join(' · ');
            const perGuest = ['per_pax', 'per_guest', 'per_person'].includes(String(item.pricing_unit || '').toLowerCase());
            const priceText = included ? 'Included in package' : `${money(price)}${perGuest ? '/guest' : ''}`;
            return `<label class="booking-menu-option">
                <input type="checkbox" data-choice="menu_ids" value="${Number(item.id)}" ${selected.has(Number(item.id)) ? 'checked' : ''}>
                <span class="booking-choice-content"><strong>${escapeHtml(item.name)}</strong>
                    <span class="booking-choice-meta">${escapeHtml(item.category)}${serving ? ` · ${escapeHtml(serving)}` : ''}${item.description ? ` · ${escapeHtml(item.description)}` : ''}</span>
                </span>
                <span class="booking-choice-price">${priceText}</span>
            </label>`;
        }).join('')}</div>`;
    };
    const renderAddons = (event, group, title, source, key, includedKey) => {
        const selected = getSelected(event, key);
        const pkg = getPackage(event.package_id);
        const addonKey = key === 'equipment_ids' ? 'equipment_addons' : 'service_addons';
        const configured = pkg?.[addonKey] || [];
        const available = configured.length
            ? source.filter(item => packageAddon(pkg, addonKey, item.id))
            : source;
        if (!available.length) return '';
        return `<div class="booking-choice-group">
            <div class="booking-menu-heading"><strong>${title}</strong><span class="booking-choice-meta">Optional</span></div>
            <div class="booking-addon-grid">${available.map(item => {
                const included = isIncluded(pkg, item.id, includedKey);
                const configuredItem = packageAddon(pkg, addonKey, item.id);
                const price = configuredItem ? Number(configuredItem.price || 0) : Number(item.price || 0);
                return `<label class="booking-addon-option">
                    <input type="checkbox" data-choice="${key}" value="${Number(item.id)}" ${selected.has(Number(item.id)) ? 'checked' : ''}>
                    <span class="booking-choice-content"><strong>${escapeHtml(item.name)}</strong>
                        ${item.description ? `<span class="booking-choice-meta">${escapeHtml(item.description)}</span>` : ''}
                    </span>
                    <span class="booking-choice-price">${included ? 'Included' : `${money(price)}${['per_pax', 'per_guest', 'per_person'].includes(String(item.unit_type || '').toLowerCase()) ? '/guest' : ''}`}</span>
                </label>`;
            }).join('')}</div>
        </div>`;
    };
    const renderEvent = (event, index) => {
        const price = selectedEventPrice(event);
        const times = timeOptions.map(option =>
            `<option value="${escapeHtml(option.value)}" ${option.value === event.ingress ? 'selected' : ''}>${escapeHtml(option.label)}</option>`
        ).join('');
        const status = event.availability === null
            ? 'Choose a date and ingress time to check availability.'
            : (event.availability ? (event.availabilityMessage || 'This date and time is available.') : (event.availabilityMessage || 'This date and time is unavailable.'));
        return `<article class="booking-event-card" data-event-id="${escapeHtml(event.id)}">
            <div class="booking-event-heading">
                <h4 class="booking-event-title">Event ${index + 1}</h4>
                <button class="booking-event-remove" type="button" data-action="remove-event" ${events.length === 1 ? 'disabled' : ''}>Remove event</button>
            </div>
            <div class="booking-event-fields">
                <div class="booking-field"><label for="${escapeHtml(event.id)}-date">Event date</label>
                    <input id="${escapeHtml(event.id)}-date" type="date" data-field="event_date" value="${escapeHtml(event.event_date)}" required></div>
                <div class="booking-field"><label for="${escapeHtml(event.id)}-ingress">Ingress</label>
                    <select id="${escapeHtml(event.id)}-ingress" data-field="ingress" required><option value="">Select time</option>${times}</select></div>
                <div class="booking-field"><label for="${escapeHtml(event.id)}-egress">Egress · automatic</label>
                    <input id="${escapeHtml(event.id)}-egress" type="time" value="${escapeHtml(event.egress)}" readonly aria-readonly="true"></div>
                <div class="booking-field"><label for="${escapeHtml(event.id)}-guests">Estimated guests</label>
                    <input id="${escapeHtml(event.id)}-guests" type="number" data-field="guest_count" min="1" max="999999" value="${Number(event.guest_count || 1)}" required></div>
            </div>
            <p class="booking-events-help">Egress is calculated from this event’s selected package duration.</p>
            <div class="booking-event-status${event.availability === false ? ' is-error' : ''}" role="status">${escapeHtml(status)}</div>
            <div class="booking-package-heading"><strong>Available package choices</strong></div>
            ${renderPackages(event)}
            <details class="booking-event-menu" open>
                <summary class="booking-menu-heading"><strong>Menu / Food selection</strong><span class="booking-choice-meta">Per event · included items are not charged twice</span></summary>
                ${renderMenuChoices(event)}
            </details>
            ${renderAddons(event, 'equipment', 'Equipment & rentals', equipmentItems, 'equipment_ids', 'included_equipment_ids')}
            ${renderAddons(event, 'services', 'Additional services', serviceItems, 'service_ids', 'included_service_ids')}
            <div class="booking-event-subtotal"><span>Event ${index + 1} estimated subtotal</span><strong>${money(price.subtotal)}</strong></div>
        </article>`;
    };

    const updateHiddenFirstEvent = () => {
        const first = events[0];
        if (!first) return;
        const pkg = getPackage(first.package_id);
        if (legacyDate) legacyDate.value = first.event_date;
        if (legacyTime) {
            if (first.ingress && !Array.from(legacyTime.options).some(option => option.value === first.ingress)) {
                legacyTime.add(new Option(first.ingress, first.ingress));
            }
            legacyTime.value = first.ingress;
        }
        if (legacyEndTime) legacyEndTime.value = first.egress;
        if (legacyPackage) legacyPackage.value = pkg ? pkg.id : '';
        if (legacyGuests) legacyGuests.value = first.guest_count;
        if (legacyGuestDisplay) legacyGuestDisplay.value = Number(first.guest_count || 1).toLocaleString();
        if (eventType && pkg) eventType.value = pkg.event_type || 'General Catering';
        if (pkg && String(window.currentPackageId) !== String(pkg.id) && typeof window.switchPackage === 'function') {
            window.switchPackage(String(pkg.id));
        }
    };

    const updateEventTotals = () => {
        events.forEach(event => {
            const pkg = getPackage(event.package_id);
            const duration = Number(pkg?.service_duration || 0);
            const [hours, minutes] = String(event.ingress || '').split(':').map(Number);
            const start = Number.isFinite(hours) && Number.isFinite(minutes) ? hours * 60 + minutes : NaN;
            const end = start + duration * 60;
            event.egress = duration > 0 && Number.isFinite(start) && end < 1440
                ? `${String(Math.floor(end / 60)).padStart(2, '0')}:${String(end % 60).padStart(2, '0')}`
                : '';
            const egress = document.getElementById(`${event.id}-egress`);
            if (egress) egress.value = event.egress;
        });
        updateHiddenFirstEvent();
        const estimates = events.map(selectedEventPrice);
        const subtotal = estimates.reduce((sum, value) => sum + value.subtotal, 0);
        const feeStatus = String(window.deliveryFeeStatus || '').toLowerCase();
        const feeIsKnown = ['calculated', 'confirmed', 'available', 'success'].includes(feeStatus);
        const fee = feeIsKnown ? Number(window.currentDeliveryFee || 0) : 0;
        const total = subtotal + fee;
        const guests = events.reduce((sum, event) => sum + Number(event.guest_count || 0), 0);
        const totalElement = document.getElementById('booking-events-total');
        const sidebarTotal = document.getElementById('calc-grand-total');
        const sidebarGuests = document.getElementById('calc-guests');
        const sidebarPackage = document.getElementById('calc-pkg-price-label');
        const sidebarFee = document.getElementById('calc-delivery-fee');
        const totalInput = document.getElementById('total_price_input');
        const reservationInput = document.getElementById('reservation_fee_input');
        if (totalElement) totalElement.textContent = money(total);
        if (sidebarTotal) sidebarTotal.textContent = money(total);
        if (sidebarGuests) sidebarGuests.textContent = String(guests);
        if (sidebarPackage) sidebarPackage.textContent = `${events.length} event${events.length === 1 ? '' : 's'} · packages, menu & add-ons`;
        if (sidebarFee) sidebarFee.textContent = feeIsKnown ? money(fee) : 'Coordinate with caterer';
        if (totalInput) totalInput.value = total.toFixed(2);
        if (reservationInput) reservationInput.value = (total * 0.3).toFixed(2);
        const transport = document.getElementById('booking-events-transport');
        if (transport) {
            transport.textContent = feeIsKnown
                ? `Transportation fee: ${money(fee)} (configured for this venue).`
                : 'Transportation: Coordinate with caterer until confirmed.';
        }
        eventsInput.value = JSON.stringify(events.map(event => ({
            id: event.id,
            event_date: event.event_date,
            ingress: event.ingress,
            egress: event.egress,
            guest_count: Number(event.guest_count || 1),
            package_id: Number(event.package_id || 0),
            menu_ids: Array.from(getSelected(event, 'menu_ids')),
            equipment_ids: Array.from(getSelected(event, 'equipment_ids')),
            service_ids: Array.from(getSelected(event, 'service_ids'))
        })));
        try {
            sessionStorage.setItem(eventStorageKey, eventsInput.value);
        } catch (error) {
            console.warn('Could not save event schedules in this browser:', error);
        }
    };

    const render = () => {
        const activeElement = document.activeElement;
        const activeId = activeElement && eventList.contains(activeElement) ? activeElement.id : '';
        eventList.innerHTML = events.map(renderEvent).join('');
        if (activeId) document.getElementById(activeId)?.focus({ preventScroll: true });
        if (addEventButton) addEventButton.disabled = packages.length === 0;
        updateEventTotals();
    };

    const checkAvailability = async event => {
        if (!event.event_date || !event.ingress) {
            availability.delete(event.id);
            event.availability = null;
            event.availabilityMessage = '';
            render();
            return;
        }
        const cacheKey = `${event.event_date}|${event.ingress}`;
        event.availability = null;
        event.availabilityMessage = 'Checking caterer availability…';
        render();
        const params = new URLSearchParams({
            caterer_id: String(window.catererId || ''),
            date_str: event.event_date,
            time_str: event.ingress,
            event_end_time: event.egress
        });
        if (bookingId) params.set('booking_id', bookingId);
        const requestKey = `${event.id}:${cacheKey}`;
        availability.set(event.id, requestKey);
        try {
            const response = await fetch(`/packages/api/check-availability?${params.toString()}`, { cache: 'no-store' });
            if (!response.ok) throw new Error(`Availability check failed with status ${response.status}`);
            const result = await response.json();
            if (availability.get(event.id) !== requestKey) return;
            event.availability = Boolean(result.available);
            event.availabilityMessage = result.message || (result.available ? 'This date and time is available.' : 'This date and time is unavailable.');
        } catch (error) {
            if (availability.get(event.id) !== requestKey) return;
            console.error('Could not verify event availability:', error);
            event.availability = false;
            event.availabilityMessage = 'Availability could not be verified. Please try again.';
        }
        render();
    };

    const validateInternalConflicts = () => {
        const intervals = [];
        let turnoverHours = Number(window.catererRules?.package_rules?.turnover_time_hours ?? 2);
        if (!Number.isFinite(turnoverHours) || turnoverHours < 0) turnoverHours = 2;
        const turnoverMilliseconds = turnoverHours * 60 * 60 * 1000;
        for (const event of events) {
            if (!event.event_date || !event.ingress || !event.egress) return 'Complete each event date, ingress, and package selection.';
            const start = new Date(`${event.event_date}T${event.ingress}:00`).getTime();
            const end = new Date(`${event.event_date}T${event.egress}:00`).getTime();
            if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return 'Each event egress must follow ingress on the same date.';
            const pkg = getPackage(event.package_id);
            if (!pkg) return 'Choose an available package for each event.';
            const guests = Number(event.guest_count || 0);
            if (guests < Number(pkg.min_guests || 1) || guests > Number(pkg.max_guests || 999999)) {
                return `${pkg.name} supports ${pkg.min_guests || 1}–${pkg.max_guests || 999999} guests. Update the guest count or package.`;
            }
            if (event.availability !== true) return event.availabilityMessage || 'Wait for availability to be confirmed for each event.';
            for (const interval of intervals) {
                if (
                    interval.date === event.event_date &&
                    start < interval.end + turnoverMilliseconds &&
                    end + turnoverMilliseconds > interval.start
                ) {
                    return 'Events on the same date need enough time for caterer setup and turnover.';
                }
            }
            intervals.push({ date: event.event_date, start, end });
        }
        return '';
    };

    eventList.addEventListener('change', event => {
        const card = event.target.closest('.booking-event-card');
        if (!card) return;
        const current = events.find(item => item.id === card.dataset.eventId);
        if (!current) return;
        const field = event.target.dataset.field;
        if (field) {
            if (field === 'guest_count') current.guest_count = Math.max(1, Math.min(999999, Number(event.target.value || 1)));
            else current[field] = event.target.value;
            if (field === 'event_date' || field === 'ingress') {
                current.availability = null;
                current.availabilityMessage = '';
            }
            render();
            if (field === 'event_date' || field === 'ingress') checkAvailability(current);
            else if (field === 'guest_count') checkAvailability(current);
            return;
        }
        if (event.target.matches('input[type="radio"][name^="package-"]')) {
            current.package_id = Number(event.target.value);
            const pkg = getPackage(current.package_id);
            if (pkg && events.indexOf(current) !== 0) {
                current.menu_ids = Array.from(new Set([...(pkg.included_menu_ids || []).map(Number), ...getSelected(current, 'menu_ids')]));
            } else if (pkg && !current.menu_ids.length) {
                current.menu_ids = (pkg.included_menu_ids || []).map(Number);
            }
            render();
            if (events.indexOf(current) === 0) updateHiddenFirstEvent();
            updateEventTotals();
            checkAvailability(current);
            return;
        }
        const choice = event.target.dataset.choice;
        if (choice && event.target.type === 'checkbox') {
            const selected = getSelected(current, choice);
            if (event.target.checked) selected.add(Number(event.target.value));
            else selected.delete(Number(event.target.value));
            current[choice] = Array.from(selected);
            updateEventTotals();
            const subtotal = card.querySelector('.booking-event-subtotal strong');
            if (subtotal) subtotal.textContent = money(selectedEventPrice(current).subtotal);
        }
    });

    eventList.addEventListener('click', event => {
        const button = event.target.closest('[data-action="remove-event"]');
        if (!button || events.length <= 1) return;
        const card = button.closest('.booking-event-card');
        const index = events.findIndex(item => item.id === card?.dataset.eventId);
        if (index >= 0) {
            availability.delete(events[index].id);
            events.splice(index, 1);
            render();
        }
    });

    addEventButton?.addEventListener('click', () => {
        const pkg = getPackage(legacyPackage?.value || window.currentPackageId) || packages[0];
        const event = makeEvent({
            event_date: '',
            ingress: '',
            egress: '',
            package_id: pkg?.id,
            guest_count: legacyGuests?.value || 1,
            menu_ids: pkg?.included_menu_ids || []
        });
        event.id = nextEventId();
        events.push(event);
        render();
    });

    form.addEventListener('submit', event => {
        updateEventTotals();
        const error = validateInternalConflicts();
        if (error) {
            event.preventDefault();
            event.stopImmediatePropagation();
            window.alert(error);
            return;
        }
        if (legacyDate && legacyTime && typeof window.checkAvailability === 'function') {
            legacyDate.value = events[0].event_date;
            legacyTime.value = events[0].ingress;
        }
    });

    window.updateEventTotals = updateEventTotals;
    render();
    events.forEach(item => {
        if (item.event_date && item.ingress) checkAvailability(item);
    });
});
