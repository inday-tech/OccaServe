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
    const eventType = document.getElementById('event_type_hidden');
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
    const renderEventCalendar = (event, eventIndex) => {
        const monthDate = dateFromIso(event.calendarMonth || event.event_date || minimumEventDate(getPackage(event.package_id))) || new Date();
        const year = monthDate.getFullYear();
        const month = monthDate.getMonth();
        const firstDay = new Date(year, month, 1);
        const offset = (firstDay.getDay() + 6) % 7;
        const { min: minDate, max: maxDate } = eventDateBounds(event, eventIndex);
        const datesUsedElsewhere = new Set(events.filter(item => item.id !== event.id && item.event_date).map(item => item.event_date));
        const cellCount = offset + new Date(year, month + 1, 0).getDate() > 35 ? 42 : 35;
        const days = Array.from({ length: cellCount }, (_, index) => {
            const date = new Date(year, month, index - offset + 1);
            const iso = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
            const outsideMonth = date.getMonth() !== month;
            if (outsideMonth) return '<span class="booking-calendar-empty" aria-hidden="true"></span>';
            const disabled = outsideMonth || iso < minDate || (maxDate && iso > maxDate) || datesUsedElsewhere.has(iso);
            const selected = iso === event.event_date;
            return `<button type="button" class="booking-calendar-day${selected ? ' is-selected' : ''}" data-action="select-event-date" data-date="${iso}" ${disabled ? 'disabled' : ''} aria-pressed="${selected}">${date.getDate()}</button>`;
        }).join('');
        return `<div class="booking-event-calendar" ${event.calendarOpen ? '' : 'hidden'}>
            <div class="booking-calendar-header"><button type="button" data-action="calendar-month" data-offset="-1" aria-label="Previous month">‹</button><strong>${monthDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</strong><button type="button" data-action="calendar-month" data-offset="1" aria-label="Next month">›</button></div>
            <div class="booking-calendar-grid booking-calendar-weekdays" aria-hidden="true">${['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => `<span>${day}</span>`).join('')}</div>
            <div class="booking-calendar-grid">${days}</div>
        </div>`;
    };
    const minimumEventDate = pkg => {
        const now = new Date();
        now.setHours(0, 0, 0, 0);
        const leadTime = Math.max(0, Number(pkg?.booking_lead_time ?? window.bookingLeadTime ?? 0));
        now.setDate(now.getDate() + leadTime);
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    };
    const eventDateBounds = (event, index = events.indexOf(event)) => {
        const previousDate = events.slice(0, index).map(item => item.event_date).filter(Boolean).sort().at(-1) || '';
        const nextDate = events.slice(index + 1).map(item => item.event_date).filter(Boolean).sort()[0] || '';
        const packageMinimum = minimumEventDate(getPackage(event.package_id));
        const afterPrevious = previousDate ? shiftIsoDate(previousDate, 1) : packageMinimum;
        return {
            min: afterPrevious > packageMinimum ? afterPrevious : packageMinimum,
            max: nextDate ? shiftIsoDate(nextDate, -1) : ''
        };
    };
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
            event_date: String(Object.prototype.hasOwnProperty.call(source, 'event_date') ? source.event_date : (source.date || legacyDate?.value || '')),
            ingress: String(Object.prototype.hasOwnProperty.call(source, 'ingress') ? source.ingress : (source.event_time || legacyTime?.value || '')),
            egress: String(Object.prototype.hasOwnProperty.call(source, 'egress') ? source.egress : (source.event_end_time || legacyEndTime?.value || '')),
            guest_count: Math.max(1, Number(source.guest_count || legacyGuests?.value || 1)),
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
    events.forEach((event, index) => {
        const savedEventCustomization = eventCustomizations[event.id];
        event.customization = savedEventCustomization || event.customization || (!index ? options.initial_customization : null) || null;
        if (!index && event.customization && !savedEventCustomization) event.customization_source_event_id = '__initial__';
        if (event.customization && Number(event.customization.package_id) !== Number(event.package_id)) event.customization = null;
    });
    const sharedEventName = legacyEventName?.value || events[0]?.event_name || '';
    const sharedGuestCount = Math.max(1, Number(legacyGuests?.value || legacyGuestDisplay?.value?.replace(/\D/g, '') || events[0]?.guest_count || 1));
    events.forEach(event => {
        event.event_name = sharedEventName;
        event.guest_count = sharedGuestCount;
    });

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
        const customization = event.customization;
        if (String(pkg.pricing_mode || '').toLowerCase() === 'customizable' && customization) {
            const guests = Math.max(1, Number(event.guest_count || 1));
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
                const quantity = ['per_pax', 'per_guest', 'per_person'].some(token => unit.includes(token))
                    ? guests
                    : (unit.includes('hour') ? Math.max(Number(item.qty || 1), Number(pkg.service_duration || 1))
                        : (item.capacity_type === 'staff_based' && Number(item.staff_ratio) > 0
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
                return sum + Number(packageAddon(pkg, 'equipment_addons', item.id)?.price ?? item.price ?? 0);
            }, 0);
            const services = serviceItems.reduce((sum, item) => {
                if (!getSelected(event, 'service_ids').has(Number(item.id)) || isIncluded(pkg, item.id, 'included_service_ids')) return sum;
                const perGuest = ['per_pax', 'per_guest', 'per_person'].includes(String(item.unit_type || '').toLowerCase());
                return sum + Number(packageAddon(pkg, 'service_addons', item.id)?.price ?? item.price ?? 0) * (perGuest ? Number(event.guest_count || 1) : 1);
            }, 0);
            const core = Math.max(0, base + food + extras + customServices + customEquipment - removalCredit);
            return { subtotal: core + equipment + services, package: base, menu: food + extras - removalCredit, equipment: customEquipment + equipment, services: customServices + services };
        }
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
        const count = ['food', 'services', 'equipment'].reduce((total, group) => total + (groups[group] || []).length, 0);
        return count ? `${count} included item${count === 1 ? '' : 's'}` : 'Package inclusions confirmed by caterer';
    };
    const renderPackageDetailGroup = (title, items) => {
        if (!items.length) return '';
        return `<section class="booking-package-modal-group"><h4>${title}</h4><ul>${items.map(item => {
            const quantity = String(item.quantity || item.qty || '').trim();
            const description = String(item.description || '').trim();
            const price = Number(item.subtotal ?? item.price ?? 0);
            return `<li><strong>${escapeHtml(item.name || 'Included item')}</strong>${quantity ? ` × ${escapeHtml(quantity)}` : ''}${price > 0 ? `<span class="booking-package-modal-price">${money(price)}</span>` : ''}${description ? `<div>${escapeHtml(description)}</div>` : ''}</li>`;
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
            const value = selection?.customization || eventCustomizations[selection?.id] || null;
            return isCustomizable && value && Number(value.package_id) === Number(pkg.id) ? value : null;
        };
        const lookupSelections = (source, ids, includedIds = [], addonKey = '', selectedEvent = eventSelection) => {
            const included = new Set(includedIds.map(Number));
            return ids.map(Number).filter(id => !included.has(id))
                .map(id => source.find(item => Number(item.id) === id)).filter(Boolean)
                .map(item => {
                    const configured = addonKey ? packageAddon(pkg, addonKey, item.id) : null;
                    const unit = String(item.pricing_unit || item.unit_type || '').toLowerCase();
                    const perGuest = ['per_pax', 'per_guest', 'per_person'].includes(unit);
                    const quantity = perGuest ? Number(selectedEvent?.guest_count || 1) : 1;
                    const price = Number(configured?.price ?? item.addon_price ?? item.price ?? item.rental_price ?? item.selling_price ?? 0);
                    return { id: Number(item.id), name: item.name, quantity: perGuest ? `${quantity} guests` : '1', price, subtotal: price * quantity, description: item.description || '' };
                });
        };
        const title = document.getElementById('booking-package-details-title');
        const meta = document.getElementById('booking-package-details-meta');
        const description = document.getElementById('booking-package-details-description');
        const content = document.getElementById('booking-package-details-inclusions');
        if (title) title.textContent = pkg.name || 'Package Details';
        if (meta) meta.textContent = `${packageRate(pkg)} · ${Number(pkg.min_guests || 1)}–${Number(pkg.max_guests || 999999)} guests · ${Number(pkg.service_duration || 0)}-hour service`;
        if (description) {
            description.textContent = pkg.description || '';
            description.hidden = !pkg.description;
        }
        if (content) {
            const blocks = [
                renderPackageDetailGroup(isCustomizable ? 'Package inclusions' : 'Included in this fixed package · not editable', inclusions[0]),
                renderPackageDetailGroup('Included services', inclusions[1]),
                renderPackageDetailGroup('Included equipment', inclusions[2]),
            ];
            if (!inclusions.some(items => items.length)) blocks.push('<p class="booking-package-modal-empty">No package inclusions are listed.</p>');
            if (selectionsToShow.length) {
                selectionsToShow.forEach((selection, index) => {
                    const customization = getCustomization(selection);
                    const dayNumber = events.findIndex(item => String(item.id) === String(selection.id)) + 1 || index + 1;
                    const dayTitle = `Day ${dayNumber}`;
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
                    if (selectedGroups.length) blocks.push(`<section class="booking-package-modal-event"><h3>${dayTitle}</h3>${selectedGroups.join('')}</section>`);
                });
            } else if (isSelectedEvent && isCustomizable) {
                blocks.push('<p class="booking-package-modal-empty">Customize this event to view its selected menu, services, and equipment here.</p>');
            }
            content.innerHTML = blocks.filter(Boolean).join('');
        }
        if (!modal.open) modal.showModal();
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
        const pkg = getPackage(event.package_id);
        const isCustomizable = String(pkg?.pricing_mode || '').toLowerCase() === 'customizable';
        const customizeUrl = isCustomizable
            ? `/bookings/customize/${encodeURIComponent(window.catererId)}?package_id=${encodeURIComponent(pkg.id)}&event_id=${encodeURIComponent(event.id)}&guest_count=${encodeURIComponent(event.guest_count || 1)}${event.customization_source_event_id ? `&reuse_from=${encodeURIComponent(event.customization_source_event_id)}` : ''}`
            : '';
        const times = timeOptions.map(option =>
            `<option value="${escapeHtml(option.value)}" ${option.value === event.ingress ? 'selected' : ''}>${escapeHtml(option.label)}</option>`
        ).join('');
        const status = event.availability === null
            ? 'Choose a date and ingress time to check availability.'
            : (event.availability ? (event.availabilityMessage || 'This date and time is available.') : (event.availabilityMessage || 'This date and time is unavailable.'));
        const scheduleFields = index === 0
            ? `<div class="booking-event-schedule-summary"><strong>Day 1</strong><span>${escapeHtml(event.event_date || 'Choose a date above')} · ${escapeHtml(formatDisplayTime(event.ingress) || 'Select ingress')}${event.egress ? ` – ${escapeHtml(formatDisplayTime(event.egress))}` : ''}</span></div>`
            : `<div class="booking-event-fields">
                <div class="booking-field booking-date-field"><label>Event date</label>
                    <div class="booking-date-picker"><button id="${escapeHtml(event.id)}-date-trigger" class="booking-date-picker-trigger" type="button" data-action="toggle-date-calendar" aria-expanded="${Boolean(event.calendarOpen)}">${escapeHtml(formatDisplayDate(event.event_date))}</button>${renderEventCalendar(event, index)}</div></div>
                <div class="booking-field"><label for="${escapeHtml(event.id)}-ingress">Ingress</label>
                    <select id="${escapeHtml(event.id)}-ingress" data-field="ingress" required><option value="">Select time</option>${times}</select></div>
                <div class="booking-field"><label for="${escapeHtml(event.id)}-egress">Egress (automatic)</label>
                    <input id="${escapeHtml(event.id)}-egress" type="time" value="${escapeHtml(event.egress)}" readonly aria-readonly="true"></div>
            </div>`;
        return `<article class="booking-event-card" data-event-id="${escapeHtml(event.id)}" data-event-index="${index}">
            <div class="booking-event-heading">
                <h4 class="booking-event-title">Day ${index + 1}</h4>
                <button class="booking-event-remove" type="button" data-action="remove-event" ${events.length === 1 ? 'disabled' : ''}>Remove event</button>
            </div>
            ${scheduleFields}
            <p class="booking-events-help">Egress is calculated from this event’s selected package duration.</p>
            <div class="booking-event-status${event.availability === false ? ' is-error' : ''}" role="status">${escapeHtml(status)}</div>
            ${pkg ? `<div class="booking-event-package"><div><strong>${escapeHtml(pkg.name)}</strong><span>${packageRate(pkg)} · ${Number(event.guest_count || 1)} guests · ${Number(pkg.service_duration || 0)}-hour service</span></div><button type="button" data-action="view-package-details" data-package-id="${Number(pkg.id)}">View details</button></div>` : '<p class="booking-event-status is-error">Select a package in the previous step before adding event dates.</p>'}
            ${isCustomizable ? `<div class="booking-event-customization"><span>${index === 0
                ? (event.customization ? 'Day 1 choices are from your Step 1 package selection.' : 'Choose or update Day 1 package choices in Step 1.')
                : (event.customization ? 'Custom choices saved for this event.' : 'Select this event’s menu, services, and equipment.')}</span>${index > 0 ? `<a class="booking-event-customize" href="${customizeUrl}">${event.customization ? 'Edit choices for this event' : 'Customize this event'}</a>` : ''}</div>` : ''}
            ${!isCustomizable ? `<details class="booking-event-menu">
                <summary class="booking-menu-heading"><strong>Optional food add-ons</strong><span class="booking-choice-meta">Fixed package inclusions stay unchanged</span></summary>
                ${renderMenuChoices(event)}
            </details>` : ''}
            ${renderAddons(event, 'equipment', 'Equipment & rentals', equipmentItems, 'equipment_ids', 'included_equipment_ids')}
            ${renderAddons(event, 'services', 'Additional services', serviceItems, 'service_ids', 'included_service_ids')}
            <div class="booking-event-subtotal"><span>Day ${index + 1} estimated subtotal</span><strong>${money(price.subtotal)}</strong></div>
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
            event_name: event.event_name,
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
    };

    const render = () => {
        const activeElement = document.activeElement;
        const activeId = activeElement && eventList.contains(activeElement) ? activeElement.id : '';
        eventList.innerHTML = events.map(renderEvent).join('');
        if (activeId) document.getElementById(activeId)?.focus({ preventScroll: true });
        const panel = document.getElementById('booking-events-panel');
        if (panel) panel.hidden = !events[0]?.event_date;
        if (legacyDate) legacyDate.min = minimumEventDate(getPackage(events[0]?.package_id));
        if (legacyDate && events[0]) legacyDate.max = eventDateBounds(events[0], 0).max;
        updateEventTotals();
        const addEventButton = form.querySelector('[data-action="add-event"]');
        if (addEventButton) {
            addEventButton.disabled = !getPackage(events[0]?.package_id) || !events.every(item => item.event_date);
        }
    };

    legacyEventName?.addEventListener('input', () => {
        events.forEach(event => { event.event_name = legacyEventName.value; });
        updateEventTotals();
    });
    legacyGuestDisplay?.addEventListener('input', () => {
        const guestCount = Math.max(1, Math.min(999999, Number(legacyGuestDisplay.value.replace(/\D/g, '') || 1)));
        if (legacyGuests) legacyGuests.value = guestCount;
        events.forEach(event => { event.guest_count = guestCount; });
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
        for (const [index, event] of events.entries()) {
            if (!String(event.event_name || '').trim()) return `Enter a name for Day ${index + 1}.`;
            if (!event.event_date || !event.ingress || !event.egress) return 'Complete each event date and ingress time. Egress is calculated automatically.';
            const start = new Date(`${event.event_date}T${event.ingress}:00`).getTime();
            const end = new Date(`${event.event_date}T${event.egress}:00`).getTime();
            if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return 'Each event egress must follow ingress on the same date.';
            const pkg = getPackage(event.package_id);
            if (!pkg) return 'Choose the main package before setting up event dates.';
            const guests = Number(event.guest_count || 0);
            if (guests < Number(pkg.min_guests || 1) || guests > Number(pkg.max_guests || 999999)) {
                return `${pkg.name} supports ${pkg.min_guests || 1}–${pkg.max_guests || 999999} guests. Adjust this event’s guest count.`;
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
            else if (field === 'event_date' && event.target.value && event.target.value < event.target.min) {
                event.target.setCustomValidity(`Choose a date on or after ${event.target.min}.`);
                event.target.reportValidity();
                event.target.value = '';
                current.event_date = '';
            } else {
                if (field === 'event_date') event.target.setCustomValidity('');
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
            const subtotal = card.querySelector('.booking-event-subtotal strong');
            if (subtotal) subtotal.textContent = money(selectedEventPrice(current).subtotal);
        }
    });

    eventList.addEventListener('click', event => {
        const calendarButton = event.target.closest('[data-action="toggle-date-calendar"], [data-action="calendar-month"], [data-action="select-event-date"]');
        if (calendarButton) {
            event.preventDefault();
            const card = calendarButton.closest('.booking-event-card');
            const currentIndex = Number(card?.dataset.eventIndex);
            const current = Number.isInteger(currentIndex) ? events[currentIndex] : null;
            if (!current) return;
            if (calendarButton.dataset.action === 'toggle-date-calendar') {
                current.calendarOpen = !current.calendarOpen;
                current.calendarMonth = current.event_date || minimumEventDate(getPackage(current.package_id));
            } else if (calendarButton.dataset.action === 'calendar-month') {
                const month = dateFromIso(current.calendarMonth || current.event_date || minimumEventDate(getPackage(current.package_id)));
                month.setMonth(month.getMonth() + Number(calendarButton.dataset.offset || 0));
                current.calendarMonth = `${month.getFullYear()}-${String(month.getMonth() + 1).padStart(2, '0')}-01`;
            } else {
                const chosenDate = calendarButton.dataset.date;
                const { min, max } = eventDateBounds(current, currentIndex);
                const duplicate = events.some(item => item.id !== current.id && item.event_date === chosenDate);
                if (duplicate || chosenDate < min || (max && chosenDate > max)) return;
                current.event_date = chosenDate;
                current.calendarOpen = false;
                current.calendarMonth = chosenDate;
                current.availability = null;
                current.availabilityMessage = '';
                render();
                checkAvailability(current);
                return;
            }
            render();
            document.getElementById(`${current.id}-date-trigger`)?.focus({ preventScroll: true });
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
            event_name: legacyEventName?.value || '', event_date: '', ingress: '', egress: '', package_id: pkg?.id || '',
            guest_count: legacyGuests?.value || previousEvent?.guest_count || 1,
            menu_ids: pkg?.included_menu_ids || [],
            equipment_ids: [],
            service_ids: [],
        });
        next.id = nextEventId();
        next.customization = null;
        next.customization_source_event_id = null;
        next.calendarOpen = true;
        events.push(next);
        render();
        document.getElementById(`${next.id}-date-trigger`)?.focus({ preventScroll: true });
    };

    form.addEventListener('change', event => {
        if (event.target !== legacyDate && event.target !== legacyTime) return;
        const first = events[0];
        if (!first) return;
        const selectedDate = legacyDate?.value || '';
        const firstDateBounds = eventDateBounds(first, 0);
        const duplicateDate = selectedDate && events.some(item => item !== first && item.event_date === selectedDate);
        const outOfOrder = selectedDate && (selectedDate < firstDateBounds.min || (firstDateBounds.max && selectedDate > firstDateBounds.max));
        if (duplicateDate || outOfOrder) {
            legacyDate.setCustomValidity(duplicateDate
                ? 'This date is already selected for another event. Choose a different date.'
                : 'Keep event dates in order: Day 1 must be before the next event date.');
            legacyDate.reportValidity();
            legacyDate.value = first.event_date || '';
            return;
        }
        legacyDate?.setCustomValidity('');
        first.event_date = selectedDate;
        first.ingress = legacyTime?.value || '';
        first.availability = null;
        first.availabilityMessage = '';
        render();
        if (first.event_date && first.ingress) checkAvailability(first);
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
