window.formatGuestCount = function(input) {
    try {
        let val = input.value.replace(/[^0-9]/g, '');
        if (val) val = parseInt(val, 10).toLocaleString('en-US');
        input.value = val;
        const hidden = document.getElementById('guest_count');
        if (hidden) hidden.value = val.replace(/,/g, '');
    } catch(e) { console.error('formatGuestCount error:', e); }
};

window.toggleCardSelection = function(card) {
    try {
        const checkbox = card.querySelector('input[type="checkbox"]');
        if (!checkbox) return;
        const selectionGroup = card.closest('.selection-group');
        if (selectionGroup) {
            const limit = parseInt(selectionGroup.getAttribute('data-limit')) || 0;
            const cat = selectionGroup.getAttribute('data-category');
            const counter = document.getElementById('counter-' + cat);
            if (!checkbox.checked) {
                const currentlySelected = selectionGroup.querySelectorAll('input[type="checkbox"]:checked').length;
                if (currentlySelected >= limit) {
                    alert(`You can only select up to ${limit} items for this category.`);
                    return;
                }
            }
            checkbox.checked = !checkbox.checked;
            if (checkbox.checked) card.classList.add('selected');
            else card.classList.remove('selected');
            const newlySelected = selectionGroup.querySelectorAll('input[type="checkbox"]:checked').length;
            if (counter) counter.innerText = `${newlySelected} / ${limit} Selected`;
        } else {
            checkbox.checked = !checkbox.checked;
            if (checkbox.checked) card.classList.add('selected');
            else card.classList.remove('selected');
        }
        if (typeof window.updateCalculator === 'function') window.updateCalculator();
    } catch(e) { console.error('toggleCardSelection error:', e); }
};

window.openSwapModal = function(category, slotIdx) {
    try {
        const modal = document.getElementById('swapModal');
        const title = document.getElementById('modalCategoryTitle');
        const container = document.getElementById('swapOptionsContainer');
        if (!modal || !window.allMenuItems) return;
        title.innerText = `Swap ${category}`;
        container.innerHTML = '';
        const options = window.allMenuItems.filter(i => i.category === category && !i.is_addon);
        if (options.length === 0) {
            container.innerHTML = '<p style="padding: 1rem; color: #64748b; text-align: center;">No alternative items available for this category.</p>';
        } else {
            options.forEach(opt => {
                const div = document.createElement('div');
                div.className = 'swap-option-card';
                const safeName = opt.name.replace(/'/g, "\\'").replace(/"/g, "&quot;");
                div.innerHTML = `
                    <div class="soc-info">
                        <span class="soc-name">${opt.name}</span>
                    </div>
                    <button type="button" class="btn-wizard-next" style="padding: 0.4rem 0.8rem; font-size: 0.75rem;" 
                        onclick="window.selectSwapOption(${opt.id}, '${safeName}', '${slotIdx}')">Select</button>
                `;
                container.appendChild(div);
            });
        }
        modal.classList.add('active');
    } catch(e) { console.error('openSwapModal error:', e); }
};

window.closeSwapModal = function() {
    const modal = document.getElementById('swapModal');
    if (modal) modal.classList.remove('active');
};

window.selectSwapOption = function(itemId, itemName, slotIdx) {
    try {
        const nameEl = document.getElementById('name-' + slotIdx);
        const slotInput = document.querySelector(`#slot-${slotIdx} .slot-input`);
        const statusEl = document.querySelector(`#slot-${slotIdx} .mic-status`);
        if (nameEl) nameEl.innerText = itemName;
        if (slotInput) slotInput.value = itemId;
        if (statusEl) {
            statusEl.innerText = 'Swapped';
            statusEl.style.color = '#f59e0b';
        }
        window.closeSwapModal();
    } catch(e) { console.error('selectSwapOption error:', e); }
};

window.checkAvailability = async function () {
    try {
        const dateInput = document.getElementById('event_date');
        const chip = document.getElementById('availability-chip');
        if (!dateInput || !dateInput.value || !chip) return;

        chip.style.display = 'inline-flex';
        chip.className = 'availability-chip checking';
        chip.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking availability...';

        const response = await fetch(`/caterers/${window.catererId}/check-availability?date=${dateInput.value}`);
        const data = await response.json();

        if (data.available) {
            chip.className = 'availability-chip available';
            chip.innerHTML = '<i class="fas fa-check-circle"></i> Date Available';
        } else {
            chip.className = 'availability-chip booked';
            chip.innerHTML = '<i class="fas fa-times-circle"></i> Date Fully Booked';
        }
    } catch (error) {
        console.error('Availability check failed:', error);
        const chip = document.getElementById('availability-chip');
        if (chip) chip.style.display = 'none';
    }
};

document.addEventListener('DOMContentLoaded', function () {
    try {
        const guestInput = document.getElementById('guest_count');
        const pricePerHead = window.pricePerHead || 0;

        const eventTypeSelect = document.getElementById('event_type_select');
        const otherEventTypeWrap = document.getElementById('other-event-wrap');
        const otherEventTypeInput = document.getElementById('other_event_type');

        if (eventTypeSelect) {
            eventTypeSelect.addEventListener('change', function () {
                if (this.value === 'Other') {
                    otherEventTypeWrap.classList.add('visible');
                    otherEventTypeInput.required = true;
                } else {
                    otherEventTypeWrap.classList.remove('visible');
                    otherEventTypeInput.required = false;
                    otherEventTypeInput.value = '';
                }
            });
        }

        window.updateCalculator = function () {
            const calcGuests = document.getElementById('calc-guests');
            const calcAddonsCount = document.getElementById('calc-addons-count');
            const calcAddonsTotal = document.getElementById('calc-addons-total');
            const calcTotal = document.getElementById('calc-grand-total');
            const totalPriceInput = document.getElementById('total_price_input');
            const reservationFeeInput = document.getElementById('reservation_fee_input');

            if (!guestInput || !calcGuests || !calcTotal) return;

            const guests = parseInt(guestInput.value) || 0;
            calcGuests.innerText = guests;

            let total = guests * pricePerHead;

            const allAddonCheckboxes = document.querySelectorAll('input[name="selected_addons"], input[name="selected_equipment_addons"], input[name="selected_service_addons"]');
            let addonsTotal = 0;
            let checkedCount = 0;

            allAddonCheckboxes.forEach(cb => {
                if (cb.name === 'selected_service_addons') {
                    const card = cb.closest('.menu-item-card');
                    const reqLabel = card.querySelector('.staff-req-label');
                    const qtyValSpan = card.querySelector('.qty-val');
                    const priceSpan = card.querySelector('.mic-price');
                    
                    let qty = 1;
                    const capacityType = cb.getAttribute('data-capacity-type') || 'unit_based';
                    const staffRatio = parseInt(cb.getAttribute('data-staff-ratio')) || 0;
                    const minStaff = parseInt(cb.getAttribute('data-min-staff')) || 1;
                    const basePrice = parseFloat(priceSpan ? priceSpan.getAttribute('data-base-price') : 0) || parseFloat(cb.getAttribute('data-price')) || 0;
                    
                    if (capacityType === 'staff_based' && staffRatio > 0) {
                        qty = Math.max(minStaff, Math.ceil(guests / staffRatio));
                        if (reqLabel && qtyValSpan) {
                            reqLabel.style.display = 'block';
                            qtyValSpan.innerText = qty;
                        }
                        if (priceSpan) {
                            priceSpan.innerText = '+₱' + (basePrice * qty).toLocaleString(undefined, { minimumFractionDigits: 2 });
                        }
                        cb.setAttribute('data-price', basePrice * qty);
                    }
                }
                if (cb.checked) {
                    checkedCount++;
                    const price = parseFloat(cb.getAttribute('data-price')) || 0;
                    addonsTotal += price;
                }
            });

            if (calcAddonsCount) calcAddonsCount.innerText = checkedCount;
            if (calcAddonsTotal) calcAddonsTotal.innerText = '+₱' + addonsTotal.toLocaleString(undefined, { minimumFractionDigits: 2 });
            total += addonsTotal;
            calcTotal.innerText = '₱' + total.toLocaleString(undefined, { minimumFractionDigits: 2 });

            if (totalPriceInput) totalPriceInput.value = total;
            if (reservationFeeInput) reservationFeeInput.value = (total * 0.3).toFixed(2);
        };
        window.updateCalculator();

        const provinceSelect = document.getElementById('province_select');
        const citySelect = document.getElementById('city_select');
        const barangaySelect = document.getElementById('barangay_select');
        const venueAddressHidden = document.getElementById('venue_address_hidden');

        const lagunaData = {
            "Binan": ["Binan", "Canlalay", "Casile", "De La Paz", "Dila", "Langkiwa", "Loma", "Malaban", "Malamig", "Mamplasan", "Platero", "Poblacion", "San Antonio", "San Jose", "San Vicente", "Santo Tomas", "Soro-soro", "Timbao", "Zapote"],
            "Cabuyao": ["Banay-Banay", "Banlic", "Bigaa", "Butong", "Casile", "Gulod", "Mamatid", "Marinig", "Niugan", "Pittland", "Pulo", "Sala", "San Isidro"],
            "Calamba": ["Bagong Kalsada", "Banadero", "Barandal", "Batino", "Bubuyan", "Bucal", "Bunggo", "Burol", "Camaligan", "Canlubang", "Halang", "Hornalan", "Laguerta", "La Mesa", "Lawa", "Lecheria", "Lingga", "Looc", "Mabato", "Majada Labas", "Makiling", "Mapagong", "Masili", "Maunong", "Mayapa", "Milagrosa", "Palingon", "Palo-Alto", "Pansol", "Parian", "Prinza", "Punla", "Putho Tuntungin", "Real", "Saimsim", "Sampiruhan", "San Cristobal", "San Jose", "San Juan", "Sirang Lupa", "Sucol", "Turbina", "Ulango"],
            "San Pedro": ["Bagong Silang", "Chrysanthemum", "Cuyab", "Estrella", "Fatima", "G.S.I.S.", "Holiday Hills", "Langgam", "Laram", "Magsaysay", "Maharlika", "Narra", "Nueva", "Pacita I", "Pacita II", "Poblacion", "Riviera", "Rosario", "Sampaguita", "San Antonio", "San Lorenzo Christian", "San Roque", "San Vicente", "Santa Elena", "Santo Nino", "United Bayanihan", "United Better Living", "Victoria"],
            "Santa Rosa": ["Aplaya", "Balibago", "Caingin", "Dila", "Ditas", "Don Jose", "Ibaba", "Kanluran", "Labas", "Macabling", "Malitlit", "Market Area", "Pooc", "Pulong Santa Cruz", "Santo Domingo", "Sinalhan", "Tagapo"]
        };

        function populateCities() {
            if (!citySelect) return;
            citySelect.innerHTML = '<option value="">-- Select City --</option>';
            Object.keys(lagunaData).sort().forEach(city => {
                const opt = document.createElement('option');
                opt.value = city;
                opt.textContent = city;
                citySelect.appendChild(opt);
            });
            citySelect.disabled = false;
            if(barangaySelect) barangaySelect.disabled = true;
        }

        if (citySelect && barangaySelect) {
            citySelect.addEventListener('change', function () {
                const city = this.value;
                barangaySelect.innerHTML = '<option value="">-- Select Barangay --</option>';
                if (city && lagunaData[city]) {
                    lagunaData[city].forEach(brgy => {
                        const opt = document.createElement('option');
                        opt.value = brgy;
                        opt.textContent = brgy;
                        barangaySelect.appendChild(opt);
                    });
                    barangaySelect.disabled = false;
                } else {
                    barangaySelect.disabled = true;
                }
                updateHiddenAddress();
            });
        }

        if (provinceSelect) {
            provinceSelect.addEventListener('change', function() {
                if (this.value === 'Laguna') populateCities();
                updateHiddenAddress();
            });
            if (provinceSelect.value === 'Laguna') populateCities();
        }

        if (barangaySelect) {
            barangaySelect.addEventListener('change', updateHiddenAddress);
        }

        function updateHiddenAddress() {
            if (!venueAddressHidden || !provinceSelect || !citySelect || !barangaySelect) return;
            const p = provinceSelect.value;
            const c = citySelect.value;
            const b = barangaySelect.value;
            if (p && c && b) {
                venueAddressHidden.value = `${b}, ${c}, ${p}`;
            }
        }

        function validateField(input, errorId, validationFn, customErrorText = null) {
            if (!input) return true;
            const errSpan = document.getElementById(errorId);
            const isValid = validationFn(input.value);
            if (isValid) {
                input.classList.remove('error');
                if (errSpan) errSpan.classList.remove('show');
            } else {
                input.classList.add('error');
                if (errSpan) {
                    if (customErrorText) errSpan.innerText = customErrorText;
                    errSpan.classList.add('show');
                }
            }
            return isValid;
        }

        const eventName = document.getElementById('event_name');
        if (eventName) {
            eventName.addEventListener('input', () => validateField(eventName, 'err-name', v => v.trim().length > 0));
            eventName.addEventListener('change', () => validateField(eventName, 'err-name', v => v.trim().length > 0));
        }

        if (eventTypeSelect) {
            eventTypeSelect.addEventListener('change', () => validateField(eventTypeSelect, 'err-type', v => v !== ''));
        }

        const guestDisplay = document.getElementById('guest_count_display');
        const validateGuestCount = () => {
            if (!guestDisplay) return true;
            const g = parseInt(guestDisplay.value.replace(/,/g, '')) || 0;
            let valid = g >= (window.minGuests || 1);
            if (window.maxGuests > 0) valid = valid && g <= window.maxGuests;
            
            let errorText = `Minimum requirement is ${window.minGuests || 1} pax.`;
            if (window.maxGuests > 0 && g > window.maxGuests) errorText = `Maximum limit is ${window.maxGuests} pax.`;
            
            return validateField(guestDisplay, 'err-guests', () => valid, errorText);
        };
        if (guestDisplay) {
            guestDisplay.addEventListener('input', validateGuestCount);
            guestDisplay.addEventListener('change', validateGuestCount);
        }

        const eventDate = document.getElementById('event_date');
        if (eventDate) {
            const leadTime = window.bookingLeadTime || 7;
            const minDateObj = new Date();
            minDateObj.setDate(minDateObj.getDate() + leadTime - 1);
            const yyyy = minDateObj.getFullYear();
            const mm = String(minDateObj.getMonth() + 1).padStart(2, '0');
            const dd = String(minDateObj.getDate()).padStart(2, '0');
            eventDate.min = `${yyyy}-${mm}-${dd}`;
        }
        
        const validateEventDate = () => {
            if (!eventDate) return true;
            return validateField(eventDate, 'err-date', v => {
                if (!v) return false;
                const parts = v.split('-');
                if(parts.length !== 3) return false;
                const selectedDate = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
                
                const minDate = new Date();
                const leadTime = window.bookingLeadTime || 7;
                minDate.setDate(minDate.getDate() + (leadTime - 1));
                minDate.setHours(0,0,0,0);
                return selectedDate > minDate;
            }, `Please select a date at least ${window.bookingLeadTime || 7} days in advance.`);
        };
        if (eventDate) {
            eventDate.addEventListener('input', validateEventDate);
            eventDate.addEventListener('change', validateEventDate);
        }

        const eventTime = document.getElementById('event_time');
        let minTime = "08:00";
        let maxTime = "20:00";
        if (window.catererRules && window.catererRules.operating_hours) {
            minTime = window.catererRules.operating_hours.start || minTime;
            maxTime = window.catererRules.operating_hours.end || maxTime;
        }
        if (eventTime) {
            eventTime.min = minTime;
            eventTime.max = maxTime;
        }
        const validateEventTime = () => {
            if (!eventTime) return true;
            return validateField(eventTime, 'err-time', v => {
                if (!v) return false;
                return v >= minTime && v <= maxTime;
            }, `Please choose a time between ${minTime} and ${maxTime}.`);
        };
        if (eventTime) {
            eventTime.addEventListener('input', validateEventTime);
            eventTime.addEventListener('change', validateEventTime);
        }

        if (provinceSelect) provinceSelect.addEventListener('change', () => validateField(provinceSelect, 'err-province', v => v !== ''));
        if (citySelect) citySelect.addEventListener('change', () => validateField(citySelect, 'err-city', v => v !== ''));
        if (barangaySelect) barangaySelect.addEventListener('change', () => validateField(barangaySelect, 'err-barangay', v => v !== ''));

        const form = document.getElementById('detailsForm');
        if (form) {
            form.addEventListener('submit', function(e) {
                const results = [];
                if (eventName) results.push(validateField(eventName, 'err-name', v => v.trim().length > 0));
                if (eventTypeSelect) results.push(validateField(eventTypeSelect, 'err-type', v => v !== ''));
                if (eventDate) results.push(validateEventDate());
                if (eventTime) results.push(validateEventTime());
                if (provinceSelect) results.push(validateField(provinceSelect, 'err-province', v => v !== ''));
                if (citySelect) results.push(validateField(citySelect, 'err-city', v => v !== ''));
                if (barangaySelect) results.push(validateField(barangaySelect, 'err-barangay', v => v !== ''));
                if (guestDisplay) results.push(validateGuestCount());

                const isValid = results.every(r => r === true);
                if (!isValid) {
                    e.preventDefault();
                    const firstError = document.querySelector('.form-input.error');
                    if (firstError) firstError.scrollIntoView({behavior: 'smooth', block: 'center'});
                }
            });
        }

        const urlParams = new URLSearchParams(window.location.search);
        const bookingError = urlParams.get('booking_error');
        if (bookingError) {
            const errDate = document.getElementById('err-date');
            if (errDate && eventDate) {
                errDate.innerText = decodeURIComponent(bookingError);
                errDate.classList.add('show');
                eventDate.classList.add('error');
                eventDate.scrollIntoView({behavior: 'smooth', block: 'center'});
            }
            const url = new URL(window.location.href);
            url.searchParams.delete('booking_error');
            window.history.replaceState({}, document.title, url.pathname + url.search + url.hash);
        }
    } catch(err) {
        console.error("Error inside DOMContentLoaded:", err);
    }
});
