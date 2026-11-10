document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('detailsForm');
    const eventList = document.getElementById('booking-event-list');
    const eventsInput = document.getElementById('booking-events-json');
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
    const legacyEventName = document.getElementById('event_name');
    const legacySpecialRequests = document.getElementById('booking-special-requests');
    const legacyEventTypeSelect = document.getElementById('event_type_select');
    const legacyOtherEventType = document.getElementById('other_event_type');
    const legacyCelebrant = form.querySelector('[name="celebrant_name"]');
    const legacyTheme = form.querySelector('[name="theme_motif"]');
    const eventType = document.getElementById('event_type_hidden');
    const eventTypeOptions = ['Wedding', 'Birthday', 'Corporate', 'Debut', 'Baptism', 'Anniversary', 'Other'];
    const bookingId = form.querySelector('[name="booking_id"]')?.value || '';
    const eventStorageKey = `occaserve:booking-event-schedules:v2:${window.catererId || ''}:${bookingId || legacyPackage?.value || ''}`;
    const submitButton = document.getElementById('submitBtn');
    const availability = new Map();
    let eventSequence = 0;

    const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[character]);
    const money = amount => `₱${Number(amount || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    const nextEventId = () => `event-${Date.now()}-${++eventSequence}`;
    const formatDisplayTime = value => {
        const match = String(value || '').match(/^(\d{1,2}):(\d{2})$/);
        if (!match) return value || '';
        const hour = Number(match[1]);
        const minute = Number(match[2]);
        if (hour > 23 || minute > 59) return value;
        return new Date(2000, 0, 1, hour, minute).toLocaleTimeString('en-US', {
            hour: 'numeric', minute: '2-digit', hour12: true
        });
    };
    const dateFromIso = value => /^\d{4}-\d{2}-\d{2}$/.test(String(value || '')) ? new Date(`${value}T00:00:00`) : null;
    const formatDisplayDate = value => {
        const date = dateFromIso(value);
        return date ? date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : 'Choose a date';
    };
    const shiftIsoDate = (value, days) => {
        const date = dateFromIso(value);
        if (!date) return '';
        date.setDate(date.getDate() + days);
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    };
    const minimumEventDate = pkg => {
        const now = new Date();
        now.setHours(0, 0, 0, 0);
        const pkgLeadTime = pkg?.booking_lead_time;
        const leadTime = Math.max(7, Number(pkgLeadTime != null ? pkgLeadTime : (window.bookingLeadTime || 7)));
        now.setDate(now.getDate() + leadTime);
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    };

    const maximumAdvanceDate = () => {
        try {
            const maxDate = new Date();
            maxDate.setFullYear(maxDate.getFullYear() + 1);
            return `${maxDate.getFullYear()}-${String(maxDate.getMonth() + 1).padStart(2, '0')}-${String(maxDate.getDate()).padStart(2, '0')}`;
        } catch (_) {
            const fallback = new Date();
            fallback.setFullYear(fallback.getFullYear() + 1);
            return `${fallback.getFullYear()}-${String(fallback.getMonth() + 1).padStart(2, '0')}-${String(fallback.getDate()).padStart(2, '0')}`;
        }
    };

    const eventDateBounds = (event, index = events.indexOf(event)) => {
        const pkg = getPackage(event?.package_id || events[0]?.package_id);
        const packageMinimum = minimumEventDate(pkg);
        const maxAdvance = maximumAdvanceDate();

        let minDate = packageMinimum;
        for (let p = 0; p < index; p++) {
            const prevEvent = events[p];
            if (prevEvent && prevEvent.event_date) {
                const earliestFromPrev = shiftIsoDate(prevEvent.event_date, index - p);
                if (earliestFromPrev && earliestFromPrev > minDate) {
                    minDate = earliestFromPrev;
                }
            }
        }

        let maxDate = maxAdvance || '';
        for (let s = index + 1; s < events.length; s++) {
            const nextEvent = events[s];
            if (nextEvent && nextEvent.event_date) {
                const latestFromNext = shiftIsoDate(nextEvent.event_date, -(s - index));
                if (latestFromNext && (!maxDate || latestFromNext < maxDate)) {
                    maxDate = latestFromNext;
                }
            }
        }

        return { min: minDate, max: maxDate };
    };

    const checkDateRestrictions = (isoDate, event, index) => {
        if (!isoDate) return { valid: false, message: 'Please select an event date.' };
        const bounds = eventDateBounds(event, index);
        if (bounds.min && isoDate < bounds.min) {
            if (index === 0) {
                const pkg = getPackage(event?.package_id || events[0]?.package_id);
                const leadTime = Math.max(7, Number(pkg?.booking_lead_time ?? window.bookingLeadTime ?? 7));
                const daysWord = leadTime === 1 ? '1 day' : `${leadTime} days`;
                return { valid: false, message: `This caterer requires at least ${daysWord} advance notice. Earliest available date is ${bounds.min}.` };
            }
            return { valid: false, message: `Day ${index + 1} must be after the previous event date (on or after ${bounds.min}).` };
        }
        if (bounds.max && isoDate > bounds.max) {
            const maxAdvance = maximumAdvanceDate();
            if (isoDate > maxAdvance) {
                return { valid: false, message: `Bookings can only be scheduled up to 1 year in advance (${maxAdvance}).` };
            }
            return { valid: false, message: `Keep event dates in order: Day ${index + 1} must be on or before ${bounds.max}.` };
        }
        const duplicate = events.some((item, i) => i !== index && item.event_date === isoDate);
        if (duplicate) {
            return { valid: false, message: 'This date is already selected for another event. Choose a different date.' };
        }

        try {
            const rules = typeof window.catererRules === 'string' ? JSON.parse(window.catererRules) : (window.catererRules || {});
            const evAvail = rules.event_availability || {};
            if (evAvail.status === 'temporarily_unavailable') {
                return { valid: false, message: 'This caterer is temporarily unavailable and not accepting new bookings.' };
            }
            const blocked = evAvail.blocked_dates || [];
            const isBlocked = blocked.some(b => (typeof b === 'string' ? b : b?.date) === isoDate);
            if (isBlocked) {
                return { valid: false, message: 'This date is blocked and unavailable for this caterer. Please choose another date.' };
            }
            const opDays = evAvail.operating_days || (rules.business_hours && rules.business_hours.operating_days);
            if (Array.isArray(opDays) && opDays.length > 0 && opDays.length < 7) {
                const dateObj = dateFromIso(isoDate);
                if (dateObj) {
                    const daysOfWeek = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
                    const dayName = daysOfWeek[dateObj.getDay()];
                    if (!opDays.includes(dayName)) {
                        return { valid: false, message: `Caterer does not accept bookings on ${dayName}s.` };
                    }
                }
            }
        } catch (_) {}

        return { valid: true, message: '' };
    };
    const getPackage = id => packages.find(item => String(item.id) === String(id));
    const getSelected = (event, key) => new Set((Array.isArray(event[key]) ? event[key] : []).map(Number));
    const packageAddon = (pkg, key, id) => (pkg?.[key] || []).find(item => Number(item.id) === Number(id) && item.enabled);
    const isPerGuestUnit = unit => /pax|guest|person/.test(String(unit || '').toLowerCase());
    const addonServiceQuantity = (item, event, pkg) => {
        const unit = String(item.unit_type || '').toLowerCase();
        const guests = Math.max(1, Number(event.guest_count || 1));
        if (isPerGuestUnit(unit)) return guests;
        if (unit.includes('hour')) return Math.max(Number(item.minimum_hours || 1), Number(pkg?.service_duration || 1));
        if ((unit.includes('staff') || item.capacity_type === 'staff_based') && Number(item.staff_to_pax_ratio || 0) > 0) {
            return Math.max(Number(item.min_staff_required || 1), Math.ceil(guests / Number(item.staff_to_pax_ratio)));
        }
        return 1;
    };
    const addonEquipmentDuration = (item, pkg) => {
        const unit = String(item.unit_type || '').toLowerCase();
        if (unit.includes('hour')) return Math.max(1, Number(pkg?.service_duration || 1));
        if (unit.includes('day')) return Math.max(1, Math.ceil(Number(pkg?.service_duration || 1) / 24));
        return 1;
    };
    const detailQuantity = item => {
        const raw = item.quantity ?? item.qty;
        const text = String(raw ?? '').trim();
        if (!text) return '';
        if (/\D/.test(text)) return text;
        const count = Number(text);
        const unit = String(item.unit || item.unit_type || '').toLowerCase().replace(/_/g, ' ').trim();
        if (isPerGuestUnit(unit)) return `${count} ${count === 1 ? 'guest' : 'guests'}`;
        if (unit.includes('event') && count === 1) return '';
        const unitLabel = unit.replace(/^per\s+/, '').replace(/s$/, '');
        const duration = Number(item.duration_qty || 0);
        const durationLabel = unit.includes('hour') ? 'hours' : unit.includes('day') ? 'days' : '';
        if (duration > 1 && durationLabel) return `${count * duration} ${durationLabel}`;
        const pluralUnit = { box: 'boxes', dish: 'dishes', bus: 'buses' }[unitLabel] || `${unitLabel}s`;
        return `${count} ${count === 1 || !unitLabel ? unitLabel : pluralUnit}`.trim();
    };
    const priceUnitSuffix = unit => {
        const normalized = String(unit || '').toLowerCase().replace(/_/g, ' ').trim();
        if (!normalized || normalized === 'fixed' || normalized === 'per event') return '/event';
        if (isPerGuestUnit(normalized)) return '/guest';
        return `/${normalized.replace(/^per\s+/, '')}`;
    };
    const displayEventType = event => event?.event_type === 'Other'
        ? String(event.event_type_other || 'Other').trim()
        : String(event?.event_type || 'Event').trim();
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
        if (String(pkg?.pricing_mode || '').toLowerCase() !== 'customizable') {
            items = items.filter(item => item.is_addon);
        }
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
    const makeEvent = (source = {}, sourceIndex = 0) => {
        const pkg = getPackage(source.package_id || source.packageId) || firstPackage;
        const selectedMenuIds = Array.isArray(source.menu_ids) ? source.menu_ids :
            (Array.isArray(source.menu_item_ids) ? source.menu_item_ids : (pkg?.included_menu_ids || []));
        return {
            id: String(source.id || nextEventId()),
            event_name: String(Object.prototype.hasOwnProperty.call(source, 'event_name') ? source.event_name : (sourceIndex === 0 ? legacyEventName?.value || '' : (source.id ? `Event ${sourceIndex + 1}` : ''))),
            event_type: String(source.event_type || legacyEventTypeSelect?.value || eventType?.value || pkg?.event_type || 'General Catering'),
            event_type_other: String(source.event_type_other || (sourceIndex === 0 ? legacyOtherEventType?.value || '' : '')),
            celebrant_name: String(Object.prototype.hasOwnProperty.call(source, 'celebrant_name') ? source.celebrant_name : (sourceIndex === 0 ? legacyCelebrant?.value || '' : '')),
            theme_motif: String(Object.prototype.hasOwnProperty.call(source, 'theme_motif') ? source.theme_motif : (sourceIndex === 0 ? legacyTheme?.value || '' : '')),
            event_date: String(Object.prototype.hasOwnProperty.call(source, 'event_date') ? source.event_date : (source.date || legacyDate?.value || '')),
            ingress: String(Object.prototype.hasOwnProperty.call(source, 'ingress') ? source.ingress : (source.event_time || legacyTime?.value || '')),
            egress: String(Object.prototype.hasOwnProperty.call(source, 'egress') ? source.egress : (source.event_end_time || legacyEndTime?.value || '')),
            guest_count: Math.max(1, Number(source.guest_count || legacyGuests?.value || 1)),
            special_requests: String(source.special_requests || source.customization?.special_requests || ''),
            package_id: pkg ? Number(pkg.id) : '',
            menu_ids: selectedMenuIds.map(Number),
            equipment_ids: (source.equipment_ids || []).map(Number),
            service_ids: (source.service_ids || []).map(Number),
            customization: source.customization || null,
            availability: null,
            availabilityMessage: ''
        };
    };
    const events = initialData.length ? initialData.map((source, index) => makeEvent(source, index)) : [makeEvent()];
    const eventCustomizations = options.event_customizations || {};
    const getEventCustomization = (event, index = events.indexOf(event)) => {
        const pkg = getPackage(event?.package_id);
        if (!pkg || String(pkg.pricing_mode || '').toLowerCase() !== 'customizable') return null;

        const isDayOne = index === 0 || (!event?.id && index <= 0);
        const matchesEvent = customization => {
            if (!customization) return false;
            if (customization.event_id) {
                return String(customization.event_id) === String(event?.id);
            }
            return Boolean(isDayOne);
        };

        let savedEventCustomization = eventCustomizations[event?.id];
        if (!savedEventCustomization && event?.id) {
            savedEventCustomization = Object.values(eventCustomizations).find(c => c && String(c.event_id) === String(event.id));
        }
        const cust = (matchesEvent(savedEventCustomization) ? savedEventCustomization : null)
            || (matchesEvent(event?.customization) ? event.customization : null)
            || (isDayOne && matchesEvent(options.initial_customization) ? options.initial_customization : null)
            || (isDayOne && matchesEvent(window.customization) ? window.customization : null)
            || null;

        if (cust && Number(cust.package_id) !== Number(event?.package_id)) {
            return null;
        }
        return cust;
    };

    events.forEach((event, index) => {
        event.customization = getEventCustomization(event, index);
        if (event.customization && event.customization.guest_count) {
            event.guest_count = Number(event.customization.guest_count);
        }
        if (!event.special_requests) event.special_requests = String(event.customization?.special_requests || '');
        if (!index && event.customization && !eventCustomizations[event.id]) event.customization_source_event_id = '__initial__';
    });
    if (events[0]) {
        events[0].event_name = legacyEventName?.value || events[0].event_name || '';
        events[0].event_type = legacyEventTypeSelect?.value || eventType?.value || events[0].event_type;
        events[0].event_type_other = legacyOtherEventType?.value || events[0].event_type_other || '';
        events[0].celebrant_name = legacyCelebrant?.value || events[0].celebrant_name || '';
        events[0].theme_motif = legacyTheme?.value || events[0].theme_motif || '';
        if (!events[0].customization?.guest_count) {
            events[0].guest_count = Math.max(1, Number(legacyGuests?.value || legacyGuestDisplay?.value?.replace(/\D/g, '') || events[0].guest_count || 1));
        }
    }

    const isIncluded = (pkg, id, key) => (pkg?.[key] || []).some(value => Number(value) === Number(id));
    const packagesForEvent = event => {
        const guests = Number(event.guest_count || 0);
        const selectedDate = event.event_date ? new Date(`${event.event_date}T00:00:00`) : null;
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return packages.filter(pkg => {
            const min = Number(pkg.min_guests || 50);
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
        const index = events.indexOf(event);
        const customization = event.customization || getEventCustomization(event, index >= 0 ? index : 0);
        if (String(pkg.pricing_mode || '').toLowerCase() === 'customizable' && customization) {
            if (customization.guest_count && (!event.guest_count || event.guest_count !== Number(customization.guest_count))) {
                event.guest_count = Number(customization.guest_count);
            }
            const guests = Math.max(1, Number(event.guest_count || customization.guest_count || 1));
            const oldGuests = Math.max(1, Number(customization.guest_count || guests));
            const base = Number(customization.base_price || pkg.price_per_head || pkg.price || 0) * guests;
            const food = (customization.selected_food || []).reduce((sum, item) => {
                const quantity = String(item.unit || '').toLowerCase() === 'pax' ? guests : Number(item.qty || 1);
                return sum + Number(item.price || item.upgrade_fee || 0) * quantity;
            }, 0);
            const extras = (customization.selected_menu_extras || []).reduce(
                (sum, item) => sum + Number(item.price || 0) * Number(item.qty || 1), 0
            );
            const customServices = (customization.selected_services || []).reduce((sum, item) => {
                const unit = String(item.unit || '').toLowerCase();
                const quantity = isPerGuestUnit(unit)
                    ? guests
                    : (unit.includes('hour') ? Math.max(Number(item.qty || 1), Number(pkg.service_duration || 1))
                        : ((unit.includes('staff') || item.capacity_type === 'staff_based') && Number(item.staff_ratio) > 0
                            ? Math.max(Number(item.min_staff || 1), Math.ceil(guests / Number(item.staff_ratio)))
                            : Number(item.qty || 1)));
                return sum + Number(item.price || 0) * quantity;
            }, 0);
            const customEquipment = (customization.selected_equipment || []).reduce(
                (sum, item) => sum + Number(item.price || 0) * Number(item.qty || 1) * Number(item.duration_qty || 1), 0
            );
            const removalCredit = Number(customization.food_removal_credit || 0) / oldGuests * guests;
            const equipment = equipmentItems.reduce((sum, item) => {
                if (!getSelected(event, 'equipment_ids').has(Number(item.id)) || isIncluded(pkg, item.id, 'included_equipment_ids')) return sum;
                return sum + Number(packageAddon(pkg, 'equipment_addons', item.id)?.price ?? item.price ?? 0) * addonEquipmentDuration(item, pkg);
            }, 0);
            const services = serviceItems.reduce((sum, item) => {
                if (!getSelected(event, 'service_ids').has(Number(item.id)) || isIncluded(pkg, item.id, 'included_service_ids')) return sum;
                return sum + Number(packageAddon(pkg, 'service_addons', item.id)?.price ?? item.price ?? 0) * addonServiceQuantity(item, event, pkg);
            }, 0);
            const core = Math.max(0, base + food + extras + customServices + customEquipment - removalCredit);
            const subtotal = core + equipment + services;
            return { subtotal, package: base, menu: food + extras - removalCredit, equipment: customEquipment + equipment, services: customServices + services };
        }
        const guests = Math.max(1, Number(event.guest_count || 1));
        const mode = String(pkg.pricing_mode || (pkg.price_unit === 'per_guest' ? 'per_pax' : 'fixed')).toLowerCase();
        let packageTotal;
        if (mode === 'fixed') {
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
            return sum + Number(packageAddon(pkg, 'equipment_addons', item.id)?.price ?? item.price ?? 0) * addonEquipmentDuration(item, pkg);
        }, 0);
        const serviceTotal = serviceItems.reduce((sum, item) => {
            if (!getSelected(event, 'service_ids').has(Number(item.id)) || isIncluded(pkg, item.id, 'included_service_ids')) return sum;
            return sum + Number(packageAddon(pkg, 'service_addons', item.id)?.price ?? item.price ?? 0) * addonServiceQuantity(item, event, pkg);
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
        const count = ['food', 'services', 'equipment'].reduce((total, group) => total + (groups[group] || []).length, 0);
        return count ? `${count} included item${count === 1 ? '' : 's'}` : 'Package inclusions confirmed by caterer';
    };
    const renderPackageDetailGroup = (title, items) => {
        if (!items.length) return '';
        return `<section class="booking-package-modal-group"><h4>${title}</h4><ul>${items.map(item => {
            const quantity = detailQuantity(item);
            const description = String(item.description || '').trim();
            const price = Number(item.subtotal ?? item.price ?? 0);
            return `<li><strong>${escapeHtml(item.name || 'Included item')}</strong>${quantity ? `<span class="booking-package-modal-quantity">${escapeHtml(quantity)}</span>` : ''}${price > 0 ? `<span class="booking-package-modal-price">${money(price)}</span>` : ''}${description ? `<div class="booking-package-modal-item-description">${escapeHtml(description)}</div>` : ''}</li>`;
        }).join('')}</ul></section>`;
    };
    const openPackageDetails = (pkg, eventSelection, allEventSelections = null) => {
        const modal = document.getElementById('booking-package-details-modal');
        if (!modal || !pkg) return;
        const groups = pkg.grouped_inclusions || {};
        const inclusions = ['food', 'services', 'equipment'].map(key => Array.isArray(groups[key]) ? groups[key] : []);
        const selectionsToShow = (Array.isArray(allEventSelections) ? allEventSelections : [eventSelection])
            .filter(item => item && String(item.package_id) === String(pkg.id));
        const isSelectedEvent = eventSelection && String(eventSelection.package_id) === String(pkg.id);
        const isCustomizable = String(pkg.pricing_mode || '').toLowerCase() === 'customizable';
        const getCustomization = selection => {
            const idx = events.findIndex(item => String(item.id) === String(selection?.id));
            return getEventCustomization(selection, idx >= 0 ? idx : 0);
        };
        const lookupSelections = (source, ids, includedIds = [], addonKey = '', selectedEvent = eventSelection) => {
            const included = new Set(includedIds.map(Number));
            return ids.map(Number).filter(id => !included.has(id))
                .map(id => source.find(item => Number(item.id) === id)).filter(Boolean)
                .map(item => {
                    const configured = addonKey ? packageAddon(pkg, addonKey, item.id) : null;
                    const unit = String(item.pricing_unit || item.unit_type || '').toLowerCase();
                    const quantity = addonKey === 'equipment_addons'
                        ? addonEquipmentDuration(item, pkg)
                        : addonKey === 'service_addons'
                            ? addonServiceQuantity(item, selectedEvent || { guest_count: 1 }, pkg)
                            : (isPerGuestUnit(unit) ? Number(selectedEvent?.guest_count || 1) : 1);
                    const quantityUnit = addonKey === 'equipment_addons'
                        ? (unit.includes('hour') ? 'hour' : unit.includes('day') ? 'day' : unit || 'piece')
                        : addonKey === 'service_addons'
                            ? (isPerGuestUnit(unit) ? 'guest' : unit.includes('hour') ? 'hour' : (unit.includes('staff') || item.capacity_type === 'staff_based') ? 'staff' : 'event')
                            : isPerGuestUnit(unit) ? 'guest' : unit.replace(/^per[_ ]?/, '') || 'item';
                    const price = Number(configured?.price ?? item.addon_price ?? item.price ?? item.rental_price ?? item.selling_price ?? 0);
                    return { id: Number(item.id), name: item.name, qty: quantity, unit: quantityUnit, price, subtotal: price * quantity, description: item.description || '' };
                });
        };
        const title = document.getElementById('booking-package-details-title');
        const meta = document.getElementById('booking-package-details-meta');
        const description = document.getElementById('booking-package-details-description');
        const content = document.getElementById('booking-package-details-inclusions');
        if (title) title.textContent = pkg.name || 'Package Details';
        if (meta) meta.textContent = `${packageRate(pkg)} · Min ${Number(pkg.min_guests || 50)} · Max ${pkg.max_guests_display || 'No maximum'} · ${Number(pkg.service_duration || 0)}-hour service`;
        if (description) {
            description.textContent = pkg.description || '';
            description.hidden = !pkg.description;
        }
        if (content) {
            const blocks = [
                renderPackageDetailGroup(isCustomizable ? 'Included menu items' : 'Included in this fixed package · not editable', inclusions[0]),
                renderPackageDetailGroup('Included services', inclusions[1]),
                renderPackageDetailGroup('Included equipment', inclusions[2]),
            ];
            if (!isCustomizable && !inclusions.some(items => items.length)) {
                blocks.push('<p class="booking-package-modal-empty">The caterer has not provided a detailed inclusions list for this package.</p>');
            }
            if (selectionsToShow.length) {
                selectionsToShow.forEach((selection, index) => {
                    const customization = getCustomization(selection);
                    const eventIndex = events.findIndex(item => String(item.id) === String(selection.id));
                    const eventTitle = String(selection.event_name || '').trim() || `Event ${eventIndex >= 0 ? eventIndex + 1 : index + 1}`;
                    const eventMeta = [displayEventType(selection), selection.event_date ? formatDisplayDate(selection.event_date) : '', selection.ingress ? formatDisplayTime(selection.ingress) : ''].filter(Boolean).join(' · ');
                    const customFood = customization?.selected_food || [];
                    const customExtras = customization?.selected_menu_extras || [];
                    const customServices = customization?.selected_services || [];
                    const customEquipment = customization?.selected_equipment || [];
                    const customFoodIds = new Set([...customFood, ...customExtras].map(item => Number(item.id)));
                    const customServiceIds = new Set(customServices.map(item => Number(item.id)));
                    const customEquipmentIds = new Set(customEquipment.map(item => Number(item.id)));
                    const extras = lookupSelections(menuItems, selection.menu_ids || [], pkg.included_menu_ids || [], 'menu_addons', selection).filter(item => !customFoodIds.has(Number(item.id)));
                    const services = lookupSelections(serviceItems, selection.service_ids || [], pkg.included_service_ids || [], 'service_addons', selection).filter(item => !customServiceIds.has(Number(item.id)));
                    const equipment = lookupSelections(equipmentItems, selection.equipment_ids || [], pkg.included_equipment_ids || [], 'equipment_addons', selection).filter(item => !customEquipmentIds.has(Number(item.id)));
                    const selectedGroups = [
                        ...(isCustomizable && !customization ? ['<p class="booking-package-modal-empty">No custom menu, service, or equipment selections saved for this event yet.</p>'] : []),
                        ...(isCustomizable ? [
                            renderPackageDetailGroup('Menu selected', customFood),
                            renderPackageDetailGroup('Extra dishes selected', customExtras),
                            renderPackageDetailGroup('Services selected', customServices),
                            renderPackageDetailGroup('Equipment selected', customEquipment),
                        ] : []),
                        renderPackageDetailGroup('Optional food add-ons', extras),
                        renderPackageDetailGroup('Optional services', services),
                        renderPackageDetailGroup('Optional equipment', equipment),
                    ].filter(Boolean);
                    if (selectedGroups.length) blocks.push(`<section class="booking-package-modal-event"><h3>${escapeHtml(eventTitle)}</h3>${eventMeta ? `<p class="booking-package-modal-event-meta">${escapeHtml(eventMeta)}</p>` : ''}${selectedGroups.join('')}</section>`);
                });
            } else if (isSelectedEvent && isCustomizable) {
                blocks.push('<p class="booking-package-modal-empty">No saved choices for this event yet. Customize the package to see its menu, services, and equipment here.</p>');
            }
            content.innerHTML = blocks.filter(Boolean).join('');
        }
        if (!modal.open) modal.showModal();
    };

    const renderBookingSummaryModal = () => {
        const body = document.getElementById('booking-summary-modal-body');
        const footer = document.getElementById('booking-summary-modal-footer');
        if (!body || !footer) return;

        const feeStatus = String(window.deliveryFeeStatus || '').toLowerCase();
        const feeIsKnown = ['calculated', 'confirmed', 'available', 'success'].includes(feeStatus);
        const fee = feeIsKnown ? Number(window.currentDeliveryFee || 0) : 0;

        let totalSubtotal = 0;

        const daysHtml = events.map((event, index) => {
            const dayNumber = index + 1;
            const pkg = getPackage(event.package_id);
            const isCustomizable = String(pkg?.pricing_mode || '').toLowerCase() === 'customizable';
            const customization = getEventCustomization(event, index);
            const eventPrice = selectedEventPrice(event);
            totalSubtotal += eventPrice.subtotal;

            const dateDisplay = event.event_date ? formatDisplayDate(event.event_date) : '<span style="color:#94a3b8;">Not selected</span>';
            const ingressDisplay = event.ingress ? formatDisplayTime(event.ingress) : '<span style="color:#94a3b8;">Not set</span>';
            const egressDisplay = event.egress ? formatDisplayTime(event.egress) : '<span style="color:#94a3b8;">Not set</span>';
            const guestCount = Number(event.guest_count || 1);

            // 1. Menu Items
            let menuRowsHtml = '';
            let menuCount = 0;

            if (isCustomizable) {
                if (customization) {
                    const customFood = Array.isArray(customization.selected_food) ? customization.selected_food : [];
                    const customExtras = Array.isArray(customization.selected_menu_extras) ? customization.selected_menu_extras : [];
                    menuCount = customFood.length + customExtras.length;

                    if (menuCount > 0) {
                        menuRowsHtml = customFood.map(dish => {
                            const fee = Number(dish.upgrade_fee || dish.price || 0);
                            const feeBadge = fee > 0 ? `+${money(fee)}/pax` : 'Included';
                            const isInc = fee === 0;
                            const extraNote = dish.replacement_for_name ? `Replaces ${escapeHtml(dish.replacement_for_name)}` : (dish.category ? escapeHtml(dish.category) : '');
                            return `<li class="booking-summary-item-row">
                                <div class="booking-summary-item-info">
                                    <span class="booking-summary-item-name">${escapeHtml(dish.name)}</span>
                                    ${extraNote ? `<span class="booking-summary-item-extra">${extraNote}</span>` : ''}
                                </div>
                                <span class="booking-summary-item-badge ${isInc ? 'is-included' : ''}">${feeBadge}</span>
                            </li>`;
                        }).join('');

                        if (customExtras.length) {
                            menuRowsHtml += customExtras.map(dish => {
                                const qty = Number(dish.qty || 1);
                                const price = Number(dish.price || 0);
                                const subtotal = Number(dish.subtotal || (qty * price));
                                return `<li class="booking-summary-item-row">
                                    <div class="booking-summary-item-info">
                                        <span class="booking-summary-item-name">${escapeHtml(dish.name)} <small style="color:#6366f1;font-weight:700;">(Extra Dish)</small></span>
                                        <span class="booking-summary-item-extra">${qty} × ${money(price)}</span>
                                    </div>
                                    <span class="booking-summary-item-badge">${money(subtotal)}</span>
                                </li>`;
                            }).join('');
                        }

                        if (Number(customization.food_removal_credit || 0) > 0) {
                            menuRowsHtml += `<li class="booking-summary-item-row" style="background:#f0fdf4;border-radius:6px;">
                                <div class="booking-summary-item-info">
                                    <span class="booking-summary-item-name" style="color:#15803d;">Menu Credit Applied</span>
                                    <span class="booking-summary-item-extra" style="color:#166534;">Dishes removed from base</span>
                                </div>
                                <span class="booking-summary-item-badge" style="color:#15803d;">-${money(customization.food_removal_credit)}</span>
                            </li>`;
                        }
                    } else {
                        menuRowsHtml = `<li class="booking-summary-empty-note">No dishes selected yet.</li>`;
                    }
                } else {
                    menuRowsHtml = `<li class="booking-summary-empty-note">No custom menu selections saved yet for this event day.</li>`;
                }
            } else {
                // Fixed package
                const includedFood = (pkg?.grouped_inclusions?.food || []).map(dish => ({
                    name: dish.name || 'Included dish',
                    note: dish.category || 'Package inclusion',
                    fee: 0,
                    isIncluded: true
                }));

                if (index === 0) {
                    const slotInputs = Array.from(document.querySelectorAll('.slot-input'));
                    if (slotInputs.length) {
                        slotInputs.forEach(input => {
                            const dishId = Number(input.value);
                            const dish = menuItems.find(i => Number(i.id) === dishId);
                            const fee = Number(input.dataset.upgradeFee || 0);
                            if (dish) {
                                const existingIdx = includedFood.findIndex(f => f.name === dish.name);
                                if (existingIdx === -1) {
                                    includedFood.push({
                                        name: dish.name,
                                        note: dish.category ? `${dish.category} · Swapped` : 'Swapped dish',
                                        fee: fee,
                                        isIncluded: fee === 0
                                    });
                                }
                            }
                        });
                    }
                }

                const optionalFood = menuItemsForEvent(event).filter(item =>
                    getSelected(event, 'menu_ids').has(Number(item.id)) && !isIncluded(pkg, item.id, 'included_menu_ids')
                ).map(item => {
                    const perGuest = ['per_pax', 'per_guest', 'per_person'].includes(String(item.pricing_unit || '').toLowerCase());
                    const price = itemPrice(item, pkg);
                    return {
                        name: item.name,
                        note: `${item.category || 'Add-on'} · ${perGuest ? `${guestCount} guests` : '1 unit'}`,
                        fee: price * (perGuest ? guestCount : 1),
                        badge: `${money(price)}${perGuest ? '/pax' : ''}`,
                        isIncluded: false
                    };
                });

                const allFood = [...includedFood, ...optionalFood];
                menuCount = allFood.length;

                if (allFood.length) {
                    menuRowsHtml = allFood.map(item => `
                        <li class="booking-summary-item-row">
                            <div class="booking-summary-item-info">
                                <span class="booking-summary-item-name">${escapeHtml(item.name)}</span>
                                <span class="booking-summary-item-extra">${escapeHtml(item.note)}</span>
                            </div>
                            <span class="booking-summary-item-badge ${item.isIncluded ? 'is-included' : ''}">${item.isIncluded ? 'Included' : (item.badge || money(item.fee))}</span>
                        </li>
                    `).join('');
                } else {
                    menuRowsHtml = `<li class="booking-summary-empty-note">Package inclusions confirmed by caterer.</li>`;
                }
            }

            // 2. Add-on Services
            let servicesRowsHtml = '';
            let serviceCount = 0;

            if (isCustomizable) {
                const customSvcs = customization && Array.isArray(customization.selected_services) ? customization.selected_services : [];
                const customSvcIds = new Set(customSvcs.map(s => Number(s.id)));
                const extraSvcs = serviceItems.filter(s => getSelected(event, 'service_ids').has(Number(s.id)) && !customSvcIds.has(Number(s.id)));
                serviceCount = customSvcs.length + extraSvcs.length;

                if (serviceCount > 0) {
                    servicesRowsHtml = customSvcs.map(s => {
                        const isInc = Boolean(s.included);
                        const price = Number(s.price || 0);
                        const badge = isInc ? 'Included in base' : `${money(price)}${s.unit && s.unit !== 'fixed' && s.unit !== 'service' ? '/' + s.unit : ''}`;
                        return `<li class="booking-summary-item-row">
                            <div class="booking-summary-item-info">
                                <span class="booking-summary-item-name">${escapeHtml(s.name)}</span>
                                ${s.description ? `<span class="booking-summary-item-extra">${escapeHtml(s.description)}</span>` : ''}
                            </div>
                            <span class="booking-summary-item-badge ${isInc ? 'is-included' : ''}">${badge}</span>
                        </li>`;
                    }).join('');

                    if (extraSvcs.length) {
                        servicesRowsHtml += extraSvcs.map(s => {
                            const configured = packageAddon(pkg, 'service_addons', s.id);
                            const price = Number(configured?.price ?? s.price ?? 0);
                            const perGuest = ['per_pax', 'per_guest', 'per_person'].includes(String(s.unit_type || '').toLowerCase());
                            const sub = price * (perGuest ? guestCount : 1);
                            return `<li class="booking-summary-item-row">
                                <div class="booking-summary-item-info">
                                    <span class="booking-summary-item-name">${escapeHtml(s.name)}</span>
                                    <span class="booking-summary-item-extra">${perGuest ? `${guestCount} guests` : '1 service'}</span>
                                </div>
                                <span class="booking-summary-item-badge">${money(sub)}</span>
                            </li>`;
                        }).join('');
                    }
                } else {
                    servicesRowsHtml = `<li class="booking-summary-empty-note">None selected</li>`;
                }
            } else {
                const includedSvcs = (pkg?.grouped_inclusions?.services || []).map(s => ({
                    name: s.name || 'Included service',
                    desc: s.description || '',
                    badge: 'Included',
                    isIncluded: true
                }));
                const optionalSvcs = serviceItems.filter(s =>
                    getSelected(event, 'service_ids').has(Number(s.id)) && !isIncluded(pkg, s.id, 'included_service_ids')
                ).map(s => {
                    const configured = packageAddon(pkg, 'service_addons', s.id);
                    const price = Number(configured?.price ?? s.price ?? 0);
                    const perGuest = ['per_pax', 'per_guest', 'per_person'].includes(String(s.unit_type || '').toLowerCase());
                    const sub = price * (perGuest ? guestCount : 1);
                    return {
                        name: s.name,
                        desc: perGuest ? `${guestCount} guests × ${money(price)}` : '',
                        badge: money(sub),
                        isIncluded: false
                    };
                });

                const allSvcs = [...includedSvcs, ...optionalSvcs];
                serviceCount = allSvcs.length;

                if (allSvcs.length) {
                    servicesRowsHtml = allSvcs.map(s => `
                        <li class="booking-summary-item-row">
                            <div class="booking-summary-item-info">
                                <span class="booking-summary-item-name">${escapeHtml(s.name)}</span>
                                ${s.desc ? `<span class="booking-summary-item-extra">${escapeHtml(s.desc)}</span>` : ''}
                            </div>
                            <span class="booking-summary-item-badge ${s.isIncluded ? 'is-included' : ''}">${s.badge}</span>
                        </li>
                    `).join('');
                } else {
                    servicesRowsHtml = `<li class="booking-summary-empty-note">None selected</li>`;
                }
            }

            // 3. Equipment & Rentals
            let equipmentRowsHtml = '';
            let equipmentCount = 0;

            if (isCustomizable) {
                const customEq = customization && Array.isArray(customization.selected_equipment) ? customization.selected_equipment : [];
                const customEqIds = new Set(customEq.map(e => Number(e.id)));
                const extraEq = equipmentItems.filter(e => getSelected(event, 'equipment_ids').has(Number(e.id)) && !customEqIds.has(Number(e.id)));
                equipmentCount = customEq.length + extraEq.length;

                if (equipmentCount > 0) {
                    equipmentRowsHtml = customEq.map(eq => {
                        const isInc = Boolean(eq.included);
                        const qty = Number(eq.qty || 1);
                        const dur = Number(eq.duration_qty || 1);
                        const price = Number(eq.price || 0);
                        const sub = Number(eq.subtotal || (qty * dur * price));
                        const badge = isInc ? 'Included in base' : money(sub);
                        const desc = isInc ? '' : `${qty} × ${dur} ${eq.unit || 'unit'}${dur > 1 ? 's' : ''} × ${money(price)}`;
                        return `<li class="booking-summary-item-row">
                            <div class="booking-summary-item-info">
                                <span class="booking-summary-item-name">${escapeHtml(eq.name)}</span>
                                ${desc ? `<span class="booking-summary-item-extra">${desc}</span>` : ''}
                            </div>
                            <span class="booking-summary-item-badge ${isInc ? 'is-included' : ''}">${badge}</span>
                        </li>`;
                    }).join('');

                    if (extraEq.length) {
                        equipmentRowsHtml += extraEq.map(e => {
                            const configured = packageAddon(pkg, 'equipment_addons', e.id);
                            const price = Number(configured?.price ?? e.price ?? 0);
                            return `<li class="booking-summary-item-row">
                                <div class="booking-summary-item-info">
                                    <span class="booking-summary-item-name">${escapeHtml(e.name)}</span>
                                    ${e.description ? `<span class="booking-summary-item-extra">${escapeHtml(e.description)}</span>` : ''}
                                </div>
                                <span class="booking-summary-item-badge">${money(price)}</span>
                            </li>`;
                        }).join('');
                    }
                } else {
                    equipmentRowsHtml = `<li class="booking-summary-empty-note">None selected</li>`;
                }
            } else {
                const includedEq = (pkg?.grouped_inclusions?.equipment || []).map(e => ({
                    name: e.name || 'Included equipment',
                    desc: e.description || '',
                    badge: 'Included',
                    isIncluded: true
                }));
                const optionalEq = equipmentItems.filter(e =>
                    getSelected(event, 'equipment_ids').has(Number(e.id)) && !isIncluded(pkg, e.id, 'included_equipment_ids')
                ).map(e => {
                    const configured = packageAddon(pkg, 'equipment_addons', e.id);
                    const price = Number(configured?.price ?? e.price ?? 0);
                    return {
                        name: e.name,
                        desc: e.description || '',
                        badge: money(price),
                        isIncluded: false
                    };
                });

                const allEq = [...includedEq, ...optionalEq];
                equipmentCount = allEq.length;

                if (allEq.length) {
                    equipmentRowsHtml = allEq.map(e => `
                        <li class="booking-summary-item-row">
                            <div class="booking-summary-item-info">
                                <span class="booking-summary-item-name">${escapeHtml(e.name)}</span>
                                ${e.desc ? `<span class="booking-summary-item-extra">${escapeHtml(e.desc)}</span>` : ''}
                            </div>
                            <span class="booking-summary-item-badge ${e.isIncluded ? 'is-included' : ''}">${e.badge}</span>
                        </li>
                    `).join('');
                } else {
                    equipmentRowsHtml = `<li class="booking-summary-empty-note">None selected</li>`;
                }
            }

            return `<article class="booking-summary-day-card" data-event-id="${escapeHtml(event.id)}">
                <div class="booking-summary-day-head">
                    <div class="booking-summary-day-title">
                        <span class="booking-summary-day-badge">Day ${dayNumber}</span>
                        ${event.event_name ? `<span class="booking-summary-day-eventname">· ${escapeHtml(event.event_name)}</span>` : ''}
                    </div>
                    <span class="booking-summary-pkg-pill">
                        <i class="fas fa-box-archive" aria-hidden="true"></i> ${escapeHtml(pkg ? pkg.name : 'Package')}
                    </span>
                </div>

                <div class="booking-summary-meta-grid">
                    <div class="booking-summary-meta-item">
                        <span class="booking-summary-meta-label"><i class="far fa-calendar"></i> Date</span>
                        <span class="booking-summary-meta-val">${dateDisplay}</span>
                    </div>
                    <div class="booking-summary-meta-item">
                        <span class="booking-summary-meta-label"><i class="far fa-clock"></i> Ingress</span>
                        <span class="booking-summary-meta-val">${ingressDisplay}</span>
                    </div>
                    <div class="booking-summary-meta-item">
                        <span class="booking-summary-meta-label"><i class="fas fa-hourglass-end"></i> Egress</span>
                        <span class="booking-summary-meta-val">${egressDisplay}</span>
                    </div>
                    <div class="booking-summary-meta-item">
                        <span class="booking-summary-meta-label"><i class="fas fa-users"></i> Guests</span>
                        <span class="booking-summary-meta-val">${guestCount.toLocaleString()} pax</span>
                    </div>
                </div>

                <div class="booking-summary-group">
                    <div class="booking-summary-group-title">
                        <span><i class="fas fa-utensils" style="color:#f97316;"></i> Selected Menu</span>
                        <span class="booking-summary-group-count">${menuCount} item${menuCount === 1 ? '' : 's'}</span>
                    </div>
                    <ul class="booking-summary-items-list">
                        ${menuRowsHtml}
                    </ul>
                </div>

                <div class="booking-summary-group">
                    <div class="booking-summary-group-title">
                        <span><i class="fas fa-bell-concierge" style="color:#6366f1;"></i> Add-on Services</span>
                        <span class="booking-summary-group-count">${serviceCount} service${serviceCount === 1 ? '' : 's'}</span>
                    </div>
                    <ul class="booking-summary-items-list">
                        ${servicesRowsHtml}
                    </ul>
                </div>

                <div class="booking-summary-group">
                    <div class="booking-summary-group-title">
                        <span><i class="fas fa-chair" style="color:#0ea5e9;"></i> Equipment &amp; Rentals</span>
                        <span class="booking-summary-group-count">${equipmentCount} item${equipmentCount === 1 ? '' : 's'}</span>
                    </div>
                    <ul class="booking-summary-items-list">
                        ${equipmentRowsHtml}
                    </ul>
                </div>

                <div class="booking-summary-day-subtotal-bar">
                    <span><i class="fas fa-calculator"></i> Day ${dayNumber} Estimated Subtotal</span>
                    <strong>${money(eventPrice.subtotal)}</strong>
                </div>
            </article>`;
        }).join('');

        body.innerHTML = daysHtml || '<p class="booking-summary-empty-note">No event days configured yet.</p>';

        const grandTotal = totalSubtotal + fee;

        footer.innerHTML = `
            <div class="booking-summary-footer-card">
                ${events.length > 1 ? events.map((ev, i) => `
                    <div class="booking-summary-footer-row">
                        <span>Day ${i + 1} Subtotal (${formatDisplayDate(ev.event_date)})</span>
                        <strong>${money(selectedEventPrice(ev).subtotal)}</strong>
                    </div>
                `).join('') : ''}
                <div class="booking-summary-footer-row" ${events.length > 1 ? 'style="padding-top:0.35rem;border-top:1px dashed #cbd5e1;"' : ''}>
                    <span>Total Events Subtotal (${events.length} Event Day${events.length === 1 ? '' : 's'})</span>
                    <strong>${money(totalSubtotal)}</strong>
                </div>
                <div class="booking-summary-footer-row">
                    <span>Transportation Fee</span>
                    <span>${feeIsKnown ? money(fee) : '<em style="color:#64748b;font-style:normal;">Coordinate with caterer</em>'}</span>
                </div>
                <div class="booking-summary-footer-row is-grand-total">
                    <span>Estimated Booking Total</span>
                    <strong>${money(grandTotal)}</strong>
                </div>
            </div>
            <div class="booking-summary-footer-actions">
                <button type="button" class="btn-summary-close" data-action="close-booking-summary">Close Summary</button>
            </div>
        `;
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
            const priceText = included ? 'Included in package' : `${money(price)} ${priceUnitSuffix(item.pricing_unit)}`;
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
                const price = Number(configuredItem?.price ?? item.price ?? 0);
                const unitSuffix = priceUnitSuffix(item.unit_type);
                return `<label class="booking-addon-option">
                    <input type="checkbox" data-choice="${key}" value="${Number(item.id)}" ${selected.has(Number(item.id)) ? 'checked' : ''}>
                    <span class="booking-choice-content"><strong>${escapeHtml(item.name)}</strong>
                        ${item.description ? `<span class="booking-choice-meta">${escapeHtml(item.description)}</span>` : ''}
                    </span>
                    <span class="booking-choice-price">${included ? 'Included' : `${money(price)} ${unitSuffix}`}</span>
                </label>`;
            }).join('')}</div>
        </div>`;
    };
    const renderEvent = (event, index) => {
        const pkg = getPackage(event.package_id);
        const isCustomizable = String(pkg?.pricing_mode || '').toLowerCase() === 'customizable';
        const customizeUrl = isCustomizable
            ? `/bookings/customize/${encodeURIComponent(window.catererId)}?package_id=${encodeURIComponent(pkg.id)}&event_id=${encodeURIComponent(event.id)}&event_day=${index + 1}&guest_count=${encodeURIComponent(event.guest_count || 1)}${event.customization ? '' : (events[0]?.id ? `&reuse_from=${encodeURIComponent(events[0].id)}` : '&reuse_from=__initial__')}`
            : '';
        const times = timeOptions.map(option =>
            `<option value="${escapeHtml(option.value)}" ${option.value === event.ingress ? 'selected' : ''}>${escapeHtml(option.label)}</option>`
        ).join('');
        const status = event.availability === null
            ? 'Choose a date and ingress time to check availability.'
            : (event.availability ? (event.availabilityMessage || 'This date and time is available.') : (event.availabilityMessage || 'This date and time is unavailable.'));
        const { min: minDate, max: maxDate } = eventDateBounds(event, index);
        const scheduleFields = index === 0
            ? `<div class="booking-event-schedule-summary"><strong>${escapeHtml(event.event_name || 'Event 1')}</strong><span>${escapeHtml(displayEventType(event))}${event.event_date ? ` · ${escapeHtml(formatDisplayDate(event.event_date))}` : ' · Choose a date above'} · ${escapeHtml(formatDisplayTime(event.ingress) || 'Select ingress')}${event.egress ? ` – ${escapeHtml(formatDisplayTime(event.egress))}` : ''}</span></div>`
            : `<div class="booking-event-fields">
                <div class="booking-field booking-date-field">
                    <label class="form-label" for="${escapeHtml(event.id)}-date">Event Date</label>
                    <input id="${escapeHtml(event.id)}-date" type="date" class="form-input${event.event_date ? ' is-valid' : ''}" data-field="event_date" min="${escapeHtml(minDate)}" ${maxDate ? `max="${escapeHtml(maxDate)}"` : ''} value="${escapeHtml(event.event_date || '')}" required>
                </div>
                <div class="booking-field">
                    <label class="form-label" for="${escapeHtml(event.id)}-ingress">Ingress</label>
                    <select id="${escapeHtml(event.id)}-ingress" class="form-input" data-field="ingress" required><option value="">Select time</option>${times}</select>
                </div>
                <div class="booking-field">
                    <label class="form-label" for="${escapeHtml(event.id)}-egress">Egress (automatic)</label>
                    <input id="${escapeHtml(event.id)}-egress" class="form-input" type="time" value="${escapeHtml(event.egress || '')}" readonly aria-readonly="true">
                </div>
            </div>`;
        const eventTypeValues = eventTypeOptions.includes(event.event_type) ? eventTypeOptions : [event.event_type, ...eventTypeOptions];
        const eventTypeChoices = eventTypeValues.map(value => `<option value="${escapeHtml(value)}" ${value === event.event_type ? 'selected' : ''}>${escapeHtml(value)}</option>`).join('');
        const eventBasics = index === 0 ? '' : `<div class="booking-event-basics" aria-label="Event details">
            <div class="booking-field"><label class="form-label" for="${escapeHtml(event.id)}-name">Event name</label><input id="${escapeHtml(event.id)}-name" class="form-input" data-field="event_name" maxlength="100" value="${escapeHtml(event.event_name || '')}" required></div>
            <div class="booking-field"><label class="form-label" for="${escapeHtml(event.id)}-type">Event type</label><select id="${escapeHtml(event.id)}-type" class="form-input" data-field="event_type" required>${eventTypeChoices}</select></div>
            ${event.event_type === 'Other' ? `<div class="booking-field"><label class="form-label" for="${escapeHtml(event.id)}-type-other">Describe event type</label><input id="${escapeHtml(event.id)}-type-other" class="form-input" data-field="event_type_other" maxlength="100" value="${escapeHtml(event.event_type_other || '')}" required></div>` : ''}
            <div class="booking-field"><label class="form-label" for="${escapeHtml(event.id)}-guests">Guest count <span class="booking-field-range">(Min ${Number(pkg?.min_guests || 50)} · Max ${escapeHtml(pkg?.max_guests_display || 'No maximum')})</span></label><input id="${escapeHtml(event.id)}-guests" class="form-input" type="number" min="${Number(pkg?.min_guests || 50)}" max="${Number(pkg?.max_guests || 999999)}" data-field="guest_count" value="${Number(event.guest_count || 1)}" required></div>
            <div class="booking-field"><label class="form-label" for="${escapeHtml(event.id)}-celebrant">Celebrant / guest of honor <span class="booking-field-range">(optional)</span></label><input id="${escapeHtml(event.id)}-celebrant" class="form-input" data-field="celebrant_name" data-char-limit="100" maxlength="100" value="${escapeHtml(event.celebrant_name || '')}"></div>
            <div class="booking-field"><label class="form-label" for="${escapeHtml(event.id)}-theme">Theme / motif <span class="booking-field-range">(optional)</span></label><input id="${escapeHtml(event.id)}-theme" class="form-input" data-field="theme_motif" data-char-limit="100" maxlength="100" value="${escapeHtml(event.theme_motif || '')}"></div>
            <div class="booking-field booking-field-wide"><label class="form-label" for="${escapeHtml(event.id)}-special-requests">Special Requests &amp; Notes <span class="booking-field-range">(optional)</span></label><textarea id="${escapeHtml(event.id)}-special-requests" class="form-input" data-field="special_requests" maxlength="300" rows="2">${escapeHtml(event.special_requests || '')}</textarea></div>
        </div>`;
        const eventTitle = event.event_name || `Event ${index + 1}`;

        let customizationBlock = '';
        if (isCustomizable) {
            if (index === 0) {
                customizationBlock = `<div class="booking-event-customization is-saved">
                    <div class="booking-event-customization-main">
                        <i class="fas fa-check-circle booking-event-customization-icon" aria-hidden="true"></i>
                        <div>
                            <span>${event.customization ? 'Day 1 choices are from your Step 1 package selection.' : 'Choose or update Day 1 package choices in Step 1.'}</span>
                            <small style="display:block;font-size:0.78rem;color:#64748b;font-weight:600;">${Number(event.guest_count || 1)} guests</small>
                        </div>
                    </div>
                </div>`;
            } else if (event.customization) {
                const cust = event.customization;
                const guests = Number(event.guest_count || cust.guest_count || 1);
                const foodCount = (cust.selected_food || []).length;
                const extraCount = (cust.selected_menu_extras || []).length;
                const totalDishes = foodCount + extraCount;
                const serviceCount = (cust.selected_services || []).length;
                const equipCount = (cust.selected_equipment || []).length;
                const details = [];
                details.push(`<strong>${guests} guests</strong>`);
                if (totalDishes > 0) details.push(`${totalDishes} dish${totalDishes === 1 ? '' : 'es'}`);
                if (serviceCount > 0) details.push(`${serviceCount} service${serviceCount === 1 ? '' : 's'}`);
                if (equipCount > 0) details.push(`${equipCount} equipment`);

                customizationBlock = `<div class="booking-event-customization is-saved">
                    <div class="booking-event-customization-main">
                        <i class="fas fa-check-circle booking-event-customization-icon" aria-hidden="true"></i>
                        <div>
                            <span>Custom choices saved for Day ${index + 1}.</span>
                            <div style="font-size:0.78rem;color:#1e293b;margin-top:2px;">${details.join(' · ')}</div>
                        </div>
                    </div>
                    <div class="booking-event-customization-actions">
                        <a class="booking-event-customize" href="${customizeUrl}">Edit choices for this event</a>
                    </div>
                </div>`;
            } else {
                customizationBlock = `<div class="booking-event-customization">
                    <div class="booking-event-customization-main">
                        <i class="fas fa-utensils booking-event-customization-icon" aria-hidden="true"></i>
                        <div>
                            <span>Select this event’s menu, services, and equipment.</span>
                            <small style="display:block;font-size:0.78rem;color:#64748b;font-weight:600;">Current: ${Number(event.guest_count || 1)} guests</small>
                        </div>
                    </div>
                    <div class="booking-event-customization-actions">
                        <a class="booking-event-customize" href="${customizeUrl}">Customize this event</a>
                    </div>
                </div>`;
            }
        }

        return `<article class="booking-event-card" data-event-id="${escapeHtml(event.id)}" data-event-index="${index}">
            <div class="booking-event-heading">
                <div class="booking-event-title-wrap">
                    <h4 class="booking-event-title">${escapeHtml(eventTitle)}</h4>
                    <span class="booking-event-type">Day ${index + 1} · ${escapeHtml(displayEventType(event))}</span>
                </div>
                <button class="booking-event-remove" type="button" data-action="remove-event" ${events.length === 1 ? 'disabled' : ''}>Remove event</button>
            </div>
            ${scheduleFields}
            ${eventBasics}
            <p class="booking-events-help">Egress is calculated from this event’s selected package duration.</p>
            <div class="booking-event-status${event.availability === false ? ' is-error' : ''}" role="status">${escapeHtml(status)}</div>
            ${pkg ? `<div class="booking-event-package"><div><strong>${escapeHtml(pkg.name)}</strong><span>${packageRate(pkg)} · ${Number(event.guest_count || 1)} guests · ${Number(pkg.service_duration || 0)}-hour service</span></div><button type="button" data-action="view-package-details" data-package-id="${Number(pkg.id)}">View details</button></div>` : '<p class="booking-event-status is-error">Select a package in the previous step before adding event dates.</p>'}
            ${customizationBlock}
            ${!isCustomizable ? `<details class="booking-event-menu">
                <summary class="booking-menu-heading"><strong>Optional food add-ons</strong><span class="booking-choice-meta">Fixed package inclusions stay unchanged</span></summary>
                ${renderMenuChoices(event)}
            </details>` : ''}
            ${renderAddons(event, 'equipment', 'Equipment & rentals', equipmentItems, 'equipment_ids', 'included_equipment_ids')}
            ${renderAddons(event, 'services', 'Additional services', serviceItems, 'service_ids', 'included_service_ids')}
        </article>`;
    };

    const updateHiddenFirstEvent = () => {
        const first = events[0];
        if (!first) return;
        const pkg = getPackage(first.package_id);
        if (legacyEventName) legacyEventName.value = first.event_name || '';
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
        if (eventType && pkg) eventType.value = first.event_type || pkg.event_type || 'General Catering';
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
        const total = subtotal;
        const guests = events.reduce((sum, event) => sum + Number(event.guest_count || 0), 0);
        const sidebarTotal = document.getElementById('calc-grand-total');
        const sidebarGuests = document.getElementById('calc-guests');
        const sidebarPackage = document.getElementById('calc-pkg-price-label');
        const breakdown = document.getElementById('calc-event-breakdown');
        const totalInput = document.getElementById('total_price_input');
        const reservationInput = document.getElementById('reservation_fee_input');
        if (sidebarTotal) sidebarTotal.textContent = money(total);
        if (sidebarGuests) sidebarGuests.textContent = String(guests);
        if (sidebarPackage) sidebarPackage.textContent = money(estimates.reduce((sum, estimate) => sum + estimate.package, 0));
        if (events[0] && legacySpecialRequests) {
            events[0].special_requests = legacySpecialRequests.value.slice(0, 300);
            if (events[0].customization) events[0].customization = { ...events[0].customization, special_requests: events[0].special_requests };
        }
        if (breakdown) breakdown.innerHTML = events.map((event, index) => {
            const estimate = estimates[index];
            return `<details class="calc-event-breakdown-item"><summary><strong>${escapeHtml(event.event_name || `Event ${index + 1}`)}</strong><b>${money(estimate.subtotal)}</b></summary><div class="calc-event-lines"><span>Package <b>${money(estimate.package)}</b></span><span>Menu <b>${money(estimate.menu)}</b></span><span>Equipment <b>${money(estimate.equipment)}</b></span><span>Services <b>${money(estimate.services)}</b></span><span class="calc-event-subtotal">Event estimate <b>${money(estimate.subtotal)}</b></span></div></details>`;
        }).join('');
        if (totalInput) totalInput.value = total.toFixed(2);
        if (reservationInput) reservationInput.value = (total * 0.3).toFixed(2);
        eventsInput.value = JSON.stringify(events.map(event => ({
            id: event.id,
            event_name: event.event_name,
            event_type: event.event_type,
            event_type_other: event.event_type_other,
            special_requests: String(event.special_requests || '').slice(0, 300),
            celebrant_name: event.celebrant_name,
            theme_motif: event.theme_motif,
            event_date: event.event_date,
            ingress: event.ingress,
            egress: event.egress,
            guest_count: Number(event.guest_count || 1),
            package_id: Number(event.package_id || 0),
            menu_ids: Array.from(getSelected(event, 'menu_ids')),
            equipment_ids: Array.from(getSelected(event, 'equipment_ids')),
            service_ids: Array.from(getSelected(event, 'service_ids')),
            customization: event.customization || null
        })));
        try {
            sessionStorage.setItem(eventStorageKey, eventsInput.value);
        } catch (error) {
            console.warn('Could not save event schedules in this browser:', error);
        }
        const summaryModal = document.getElementById('booking-summary-modal');
        if (summaryModal && summaryModal.open) {
            renderBookingSummaryModal();
        }
    };

    legacySpecialRequests?.addEventListener('input', updateEventTotals);

    const render = () => {
        const activeElement = document.activeElement;
        const activeId = activeElement && eventList.contains(activeElement) ? activeElement.id : '';
        eventList.innerHTML = events.map(renderEvent).join('');
        if (activeId) document.getElementById(activeId)?.focus({ preventScroll: true });
        const panel = document.getElementById('booking-events-panel');
        if (panel) panel.hidden = !events[0]?.event_date;
        if (legacyDate && events[0]) {
            const day1Bounds = eventDateBounds(events[0], 0);
            legacyDate.min = day1Bounds.min;
            if (day1Bounds.max) {
                legacyDate.max = day1Bounds.max;
            } else {
                legacyDate.removeAttribute('max');
            }
        }
        updateEventTotals();
        const addEventButton = form.querySelector('[data-action="add-event"]');
        const addEventHint = document.getElementById('booking-add-event-hint');
        const hasPkg = Boolean(getPackage(events[0]?.package_id || legacyPackage?.value || window.currentPackageId));
        const allValid = events.length > 0 && events.every((item, index) => {
            if (!item.event_date) return false;
            const check = checkDateRestrictions(item.event_date, item, index);
            return check.valid && item.availability !== false;
        });
        const canAddEvent = hasPkg && events.every(item => item.event_date) && allValid;
        if (addEventButton) {
            addEventButton.disabled = !canAddEvent;
        }
        if (addEventHint) {
            addEventHint.hidden = canAddEvent;
            addEventHint.textContent = !hasPkg
                ? 'Choose a package before adding event dates.'
                : events.length > 1
                    ? 'Complete and verify each event date before adding another event.'
                    : 'Choose and verify an event date before adding another event.';
        }
    };

    legacyEventName?.addEventListener('input', () => {
        if (events[0]) events[0].event_name = legacyEventName.value;
        updateEventTotals();
    });
    eventList.addEventListener('input', event => {
        if (event.target.dataset.field !== 'special_requests') return;
        const card = event.target.closest('.booking-event-card');
        const current = events.find(item => item.id === card?.dataset.eventId);
        if (!current) return;
        current.special_requests = event.target.value.slice(0, 300);
        if (current.customization) {
            current.customization = { ...current.customization, special_requests: current.special_requests };
        }
        updateEventTotals();
    });
    legacyEventTypeSelect?.addEventListener('change', () => {
        if (!events[0]) return;
        events[0].event_type = legacyEventTypeSelect.value;
        events[0].event_type_other = legacyOtherEventType?.value || '';
        render();
    });
    legacyOtherEventType?.addEventListener('input', () => {
        if (!events[0]) return;
        events[0].event_type_other = legacyOtherEventType.value;
        updateEventTotals();
    });
    legacyCelebrant?.addEventListener('input', () => {
        if (!events[0]) return;
        events[0].celebrant_name = legacyCelebrant.value;
        updateEventTotals();
    });
    legacyTheme?.addEventListener('input', () => {
        if (!events[0]) return;
        events[0].theme_motif = legacyTheme.value;
        updateEventTotals();
    });
    legacyGuestDisplay?.addEventListener('input', () => {
        const guestCount = Math.max(1, Math.min(999999, Number(legacyGuestDisplay.value.replace(/\D/g, '') || 1)));
        if (legacyGuests) legacyGuests.value = guestCount;
        if (events[0]) {
            events[0].guest_count = guestCount;
            if (events[0].customization) {
                events[0].customization.guest_count = guestCount;
            }
        }
        events.forEach((event, idx) => {
            if (idx > 0 && !event.customization) {
                event.guest_count = guestCount;
            }
        });
        render();
    });

    const checkAvailability = async event => {
        if (!event.event_date || !event.ingress) {
            availability.delete(event.id);
            event.availability = null;
            event.availabilityMessage = '';
            render();
            return;
        }
        const currentIndex = events.indexOf(event);
        const dateCheck = checkDateRestrictions(event.event_date, event, currentIndex >= 0 ? currentIndex : 0);
        if (!dateCheck.valid) {
            availability.delete(event.id);
            event.availability = false;
            event.availabilityMessage = dateCheck.message;
            render();
            return;
        }

        const cacheKey = `${event.event_date}|${event.ingress}|${event.egress}`;
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
            if (events.indexOf(event) === 0 && typeof window.isAvailabilityValid !== 'undefined') {
                window.isAvailabilityValid = Boolean(result.available);
            }
        } catch (error) {
            if (availability.get(event.id) !== requestKey) return;
            console.error('Could not verify event availability:', error);
            event.availability = false;
            event.availabilityMessage = 'Availability could not be verified. Please try again.';
        }
        render();
    };

    const validateInternalConflicts = () => {
        const pkg = getPackage(events[0]?.package_id || legacyPackage?.value || window.currentPackageId);
        if (!pkg) return 'Please choose a package before setting up event dates.';

        const intervals = [];
        let turnoverHours = Number(window.catererRules?.package_rules?.turnover_time_hours ?? 2);
        if (!Number.isFinite(turnoverHours) || turnoverHours < 0) turnoverHours = 2;
        const turnoverMilliseconds = turnoverHours * 60 * 60 * 1000;

        for (const [index, event] of events.entries()) {
            const dayName = `Day ${index + 1}`;
            if (!String(event.event_name || '').trim()) return `Please enter an event name for ${dayName}.`;
            if (event.event_type === 'Other' && !String(event.event_type_other || '').trim()) {
                return `Please describe the event type for ${dayName}.`;
            }
            if (!event.event_date) return `Please select an event date for ${dayName}.`;
            if (!event.ingress) return `Please select an ingress time for ${dayName}.`;
            if (!event.egress) return `Egress time for ${dayName} could not be calculated. Choose a valid ingress time.`;

            // Validate date restrictions (lead time, operating days, blocked dates, bounds, duplicates)
            const dateCheck = checkDateRestrictions(event.event_date, event, index);
            if (!dateCheck.valid) return `${dayName}: ${dateCheck.message}`;

            // Enforce chronological order: Day 1 < Day 2 < Day 3
            if (index > 0 && event.event_date <= events[index - 1].event_date) {
                return `Keep event dates in order: ${dayName} must be after Day ${index}.`;
            }

            // Ingress and Egress order
            const start = new Date(`${event.event_date}T${event.ingress}:00`).getTime();
            const end = new Date(`${event.event_date}T${event.egress}:00`).getTime();
            if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
                return `${dayName}: Egress time must follow ingress on the same date.`;
            }

            // Guests count
            const evPkg = getPackage(event.package_id) || pkg;
            const guests = Number(event.guest_count || 0);
            if (guests < Number(evPkg.min_guests || 1) || guests > Number(evPkg.max_guests || 999999)) {
                return `${evPkg.name} supports ${evPkg.min_guests || 1}–${evPkg.max_guests || 999999} guests. Adjust ${dayName}’s guest count.`;
            }

            // Availability confirmation check
            if (event.availability === false) {
                return `${dayName}: ${event.availabilityMessage || 'The selected date and time is not available. Please choose another date or time.'}`;
            }
            if (event.availability !== true) {
                return `${dayName}: Caterer availability is still being verified. Please wait a moment and try again.`;
            }

            // Turnover time check if multiple events on the same date
            for (const interval of intervals) {
                if (
                    interval.date === event.event_date &&
                    start < interval.end + turnoverMilliseconds &&
                    end + turnoverMilliseconds > interval.start
                ) {
                    return `Events on the same date need at least ${turnoverHours} hours for caterer setup and turnover.`;
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
            if (['event_name', 'celebrant_name', 'theme_motif', 'event_type_other', 'special_requests'].includes(field)) {
                current[field] = event.target.value;
                if (field === 'special_requests' && current.customization) {
                    current.customization = { ...current.customization, special_requests: current[field].slice(0, 300) };
                }
                if (field === 'event_name') {
                    const title = card.querySelector('.booking-event-title');
                    if (title) title.textContent = current.event_name || `Event ${events.indexOf(current) + 1}`;
                }
                if (field === 'event_type_other') {
                    const typeLabel = card.querySelector('.booking-event-type');
                    if (typeLabel) typeLabel.textContent = displayEventType(current);
                }
                updateEventTotals();
                return;
            }
            if (field === 'guest_count') {
                current.guest_count = Math.max(1, Math.min(999999, Number(event.target.value || 1)));
            } else if (field === 'event_date') {
                const selectedDate = event.target.value;
                const currentIndex = events.indexOf(current);
                if (selectedDate) {
                    const check = checkDateRestrictions(selectedDate, current, currentIndex);
                    if (!check.valid) {
                        event.target.setCustomValidity(check.message);
                        event.target.reportValidity();
                        event.target.value = current.event_date || '';
                        return;
                    }
                }
                event.target.setCustomValidity('');
                current.event_date = selectedDate;
            } else {
                current[field] = event.target.value;
            }
            if (field === 'event_name' && events.indexOf(current) === 0 && legacyEventName) legacyEventName.value = current.event_name;
            if (field === 'event_date' || field === 'ingress') {
                current.availability = null;
                current.availabilityMessage = '';
            }
            render();
            if (field === 'event_date' || field === 'ingress') checkAvailability(current);
            else if (field === 'guest_count') checkAvailability(current);
            return;
        }
        const choice = event.target.dataset.choice;
        if (choice && event.target.type === 'checkbox') {
            const selected = getSelected(current, choice);
            if (event.target.checked) selected.add(Number(event.target.value));
            else selected.delete(Number(event.target.value));
            current[choice] = Array.from(selected);
            updateEventTotals();
        }
    });

    eventList.addEventListener('click', event => {
        if (event.target.matches('input[type="date"]')) {
            try {
                if (typeof event.target.showPicker === 'function') {
                    event.target.showPicker();
                }
            } catch (_) {}
            return;
        }
        const detailsButton = event.target.closest('[data-action="view-package-details"]');
        if (detailsButton) {
            event.preventDefault();
            event.stopPropagation();
            const card = detailsButton.closest('.booking-event-card');
            const eventSelection = events.find(item => item.id === card?.dataset.eventId);
            openPackageDetails(getPackage(detailsButton.dataset.packageId), eventSelection);
            return;
        }
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

    const addEvent = () => {
        if (!getPackage(events[0]?.package_id) || events.some(item => !item.event_date)) return;
        const previousEvent = events[events.length - 1];
        const pkg = getPackage(events[0]?.package_id || legacyPackage?.value || window.currentPackageId);
        const next = makeEvent({
            event_name: `Event ${events.length + 1}`, event_type: previousEvent?.event_type || legacyEventTypeSelect?.value || eventType?.value || pkg?.event_type || 'General Catering',
            event_type_other: '', celebrant_name: '', theme_motif: '', event_date: '', ingress: '', egress: '', package_id: pkg?.id || '',
            guest_count: previousEvent?.guest_count || legacyGuests?.value || 1,
            menu_ids: pkg?.included_menu_ids || [],
            equipment_ids: [],
            service_ids: [],
        });
        next.id = nextEventId();
        next.customization = null;
        next.customization_source_event_id = null;
        events.push(next);
        render();
        const eventCard = eventList.lastElementChild;
        eventCard?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        const dateInputEl = document.getElementById(`${next.id}-date`);
        if (dateInputEl) {
            dateInputEl.focus({ preventScroll: true });
            try {
                if (typeof dateInputEl.showPicker === 'function') {
                    dateInputEl.showPicker();
                }
            } catch (_) {}
        }
    };

    form.addEventListener('change', event => {
        if (event.target !== legacyDate && event.target !== legacyTime) return;
        const first = events[0];
        if (!first) return;
        if (event.target === legacyDate) {
            const selectedDate = legacyDate.value || '';
            if (selectedDate) {
                const check = checkDateRestrictions(selectedDate, first, 0);
                if (!check.valid) {
                    legacyDate.setCustomValidity(check.message);
                    legacyDate.reportValidity();
                    legacyDate.value = first.event_date || '';
                    return;
                }
            }
            legacyDate.setCustomValidity('');
            first.event_date = selectedDate;
            first.availability = null;
            first.availabilityMessage = '';
            render();
            if (first.event_date && first.ingress) checkAvailability(first);
        } else if (event.target === legacyTime) {
            first.ingress = legacyTime.value || '';
            first.availability = null;
            first.availabilityMessage = '';
            updateEventTotals();
            render();
            if (first.event_date && first.ingress) checkAvailability(first);
        }
    });

    form.addEventListener('click', event => {
        const button = event.target.closest('[data-action="view-main-package-details"]');
        if (!button) return;
        event.preventDefault();
        openPackageDetails(getPackage(button.dataset.packageId), events[0], events);
    });

    form.querySelector('[data-action="add-event"]')?.addEventListener('click', event => {
        event.preventDefault();
        addEvent();
    });

    document.getElementById('booking-package-details-modal')?.addEventListener('click', event => {
        if (event.target.closest('[data-action="close-package-details"]')) {
            event.currentTarget.close();
        }
    });

    document.addEventListener('click', event => {
        const customizeLink = event.target.closest('.booking-event-customize');
        if (customizeLink) {
            try {
                if (typeof window.saveDetailsFormState === 'function') {
                    window.saveDetailsFormState();
                }
                updateEventTotals();
            } catch (err) {
                console.warn('Could not save details form state before customizing:', err);
            }
            return;
        }

        const summaryBtn = event.target.closest('[data-action="view-booking-summary"]');
        if (summaryBtn) {
            event.preventDefault();
            const modal = document.getElementById('booking-summary-modal');
            if (modal) {
                renderBookingSummaryModal();
                if (!modal.open) {
                    modal.showModal();
                }
            }
            return;
        }

        const closeBtn = event.target.closest('[data-action="close-booking-summary"]');
        if (closeBtn) {
            event.preventDefault();
            const modal = document.getElementById('booking-summary-modal');
            if (modal && modal.open) {
                modal.close();
            }
            return;
        }

        const modal = document.getElementById('booking-summary-modal');
        if (event.target === modal && modal?.open) {
            modal.close();
        }
    });

    form.addEventListener('submit', event => {
        updateEventTotals();
        const error = validateInternalConflicts();
        if (error) {
            event.preventDefault();
            event.stopImmediatePropagation();
            if (window.Swal) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Event Schedule Review',
                    text: error,
                    confirmButtonColor: '#FF7B54'
                });
            } else {
                window.alert(error);
            }
            const submitBtnEl = document.getElementById('submitBtn');
            if (submitBtnEl) {
                submitBtnEl.innerHTML = `Next Step: Identity <i class="fas fa-arrow-right"></i>`;
                submitBtnEl.disabled = false;
                submitBtnEl.classList.remove('is-loading');
            }
            return;
        }
        if (legacyDate && legacyTime && typeof window.checkAvailability === 'function') {
            legacyDate.value = events[0].event_date;
            legacyTime.value = events[0].ingress;
        }
    });

    window.updateEventTotals = updateEventTotals;
    window.renderBookingEvents = render;
    window.renderBookingSummaryModal = renderBookingSummaryModal;
    window.openBookingSummaryModal = () => {
        const modal = document.getElementById('booking-summary-modal');
        if (modal) {
            renderBookingSummaryModal();
            if (!modal.open) modal.showModal();
        }
    };
    render();
    events.forEach(item => {
        if (item.event_date && item.ingress) checkAvailability(item);
    });
});
