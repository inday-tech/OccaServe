document.addEventListener('DOMContentLoaded', function () {
    const pricePerHead = Number(window.pricePerHead || 0);
    const catererId = Number(window.catererId || 0);
    const minGuests = Number(window.minGuests || 1);
    const phCities = window.PH_CITIES || [];

    // --- Selectors ---
    const form = document.getElementById('detailsForm');
    const guestInput = document.getElementById('guest_count');
    const guestDisplay = document.getElementById('guest_count_display');
    const dateInput = document.getElementById('event_date');
    const timeInput = document.getElementById('event_time');
    const provinceSelect = document.getElementById('province_select');
    const citySelect = document.getElementById('city_select');
    const barangaySelect = document.getElementById('barangay_select');
    const venueHidden = document.getElementById('venue_address_hidden');
    const eventTypeSelect = document.getElementById('event_type_select');
    const otherEventWrap = document.getElementById('other-event-wrap');
    const otherEventInput = document.getElementById('other_event_type');
    const submitBtn = document.getElementById('submitBtn');

    // --- Dynamic Location Data via PSGC ---
    const PROVINCE_CODES = {
        "Batangas": "041000000",
        "Cavite": "042100000",
        "Laguna": "043400000",
        "Quezon": "045600000",
        "Rizal": "045800000"
    };

    let cachedCities = {};
    let cachedBarangays = {};

    // --- 1. Set Min Date to Today ---
    const today = new Date().toISOString().split('T')[0];
    dateInput.setAttribute('min', today);

    // --- 1.5 Format Guest Count ---
    window.formatGuestCount = function (input) {
        let rawValue = input.value.replace(/\D/g, '');
        if (!rawValue) {
            guestInput.value = "";
            input.value = "";
            return;
        }
        let num = parseInt(rawValue, 10);
        if (num > 1000) num = 1000;
        guestInput.value = num;
        input.value = num.toLocaleString();
    };

    // --- 2. Update Calculator ---
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

        // Base package price
        let total = guests * pricePerHead;

        // Add-ons price
        const checkedAddons = document.querySelectorAll('input[name="selected_addons"]:checked');
        let addonsTotal = 0;
        checkedAddons.forEach(cb => {
            const price = parseFloat(cb.getAttribute('data-price')) || 0;
            addonsTotal += price;
        });

        if (calcAddonsCount) calcAddonsCount.innerText = checkedAddons.length;
        if (calcAddonsTotal) calcAddonsTotal.innerText = '+₱' + addonsTotal.toLocaleString(undefined, { minimumFractionDigits: 2 });
        
        total += addonsTotal;

        calcTotal.innerText = '₱' + total.toLocaleString(undefined, { minimumFractionDigits: 2 });

        if (totalPriceInput) totalPriceInput.value = total;
        if (reservationFeeInput) reservationFeeInput.value = total * 0.3; // 30% reservation
    };

    window.handleMenuCardToggle = function(checkbox) {
        const card = checkbox.closest('.menu-item-card');
        if (checkbox.checked) {
            card.classList.add('selected');
        } else {
            card.classList.remove('selected');
        }
        updateCalculator();
    };

    // --- 3. Check Date Availability ---
    window.checkAvailability = async function () {
        const chip = document.getElementById('availability-chip');
        if (!dateInput || !dateInput.value) return;

        const date = dateInput.value;
        chip.className = 'availability-chip checking';
        chip.style.display = 'inline-flex';
        chip.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking...';

        try {
            const response = await fetch(`/packages/api/check-availability?caterer_id=${catererId}&date_str=${date}`);
            const data = await response.json();

            if (data.available) {
                chip.className = 'availability-chip available';
                chip.innerHTML = '<i class="fas fa-check-circle"></i> Date Available';
                submitBtn.disabled = false;
            } else {
                chip.className = 'availability-chip booked';
                chip.innerHTML = '<i class="fas fa-times-circle"></i> Fully Booked';
                submitBtn.disabled = true;
            }
        } catch (error) {
            chip.innerHTML = 'Error checking date';
        }
    };

    // --- 4. Other Event Type Toggle ---
    if (eventTypeSelect) {
        eventTypeSelect.addEventListener('change', function () {
            if (this.value === 'Other') {
                otherEventWrap.classList.add('visible');
                otherEventInput.required = true;
                setTimeout(() => otherEventInput.focus(), 100);
            } else {
                otherEventWrap.classList.remove('visible');
                otherEventInput.required = false;
                otherEventInput.value = '';
                document.getElementById('err-other-type').classList.remove('show');
            }
        });
    }

    // --- 5. Cascading Location Choice (PSGC API) ---
    async function populateCities(province, selectedCity = null, selectedBrgy = null) {
        citySelect.innerHTML = '<option value="">-- Select City --</option>';
        barangaySelect.innerHTML = '<option value="">-- Select Barangay --</option>';
        barangaySelect.disabled = true;

        if (PROVINCE_CODES[province]) {
            citySelect.disabled = true;
            try {
                const code = PROVINCE_CODES[province];
                let cities = cachedCities[code];
                if (!cities) {
                    citySelect.innerHTML = '<option value="">Loading...</option>';
                    const res = await fetch(`https://psgc.gitlab.io/api/provinces/${code}/cities-municipalities/`);
                    cities = await res.json();
                    cities.sort((a, b) => a.name.localeCompare(b.name));
                    cachedCities[code] = cities;
                }
                
                citySelect.innerHTML = '<option value="">-- Select City --</option>';
                cities.forEach(city => {
                    const opt = document.createElement('option');
                    opt.value = city.name;
                    opt.textContent = city.name;
                    opt.dataset.code = city.code;
                    if (city.name === selectedCity) opt.selected = true;
                    citySelect.appendChild(opt);
                });
                citySelect.disabled = false;
                
                if (selectedCity) {
                    const matchedCity = cities.find(c => c.name === selectedCity);
                    if (matchedCity) {
                        populateBarangays(matchedCity.code, selectedBrgy);
                    }
                }
            } catch (e) {
                console.error('API Error:', e);
            }
        } else {
            citySelect.disabled = true;
        }
    }

    async function populateBarangays(cityCode, selectedBrgy = null) {
        barangaySelect.innerHTML = '<option value="">-- Select Barangay --</option>';
        if (cityCode) {
            barangaySelect.disabled = true;
            try {
                let brgys = cachedBarangays[cityCode];
                if (!brgys) {
                    barangaySelect.innerHTML = '<option value="">Loading...</option>';
                    const res = await fetch(`https://psgc.gitlab.io/api/cities-municipalities/${cityCode}/barangays/`);
                    brgys = await res.json();
                    brgys.sort((a, b) => a.name.localeCompare(b.name));
                    cachedBarangays[cityCode] = brgys;
                }
                
                barangaySelect.innerHTML = '<option value="">-- Select Barangay --</option>';
                brgys.forEach(b => {
                    const opt = document.createElement('option');
                    opt.value = b.name;
                    opt.textContent = b.name;
                    if (b.name === selectedBrgy) opt.selected = true;
                    barangaySelect.appendChild(opt);
                });
                barangaySelect.disabled = false;
            } catch (e) {
                console.error('API Error:', e);
            }
        } else {
            barangaySelect.disabled = true;
        }
    }

    if (provinceSelect) {
        provinceSelect.addEventListener('change', function () {
            populateCities(this.value);
            updateHiddenVenue();
        });

        citySelect.addEventListener('change', function () {
            const selOpt = this.options[this.selectedIndex];
            const code = selOpt ? selOpt.dataset.code : null;
            populateBarangays(code);
            updateHiddenVenue();
        });

        barangaySelect.addEventListener('change', updateHiddenVenue);
    }

    function updateHiddenVenue() {
        const p = provinceSelect.value;
        const c = citySelect.value;
        const b = barangaySelect.value;
        if (p && c && b) {
            venueHidden.value = `${b}, ${c}, ${p}`;
        } else {
            venueHidden.value = "";
        }
    }

    // --- 5.1 Load Existing Location Data ---
    function loadExistingLocation() {
        const existing = venueHidden.value; // Format: "Barangay, City, Province"
        if (existing && existing.includes(',')) {
            const parts = existing.split(',').map(s => s.trim());
            if (parts.length >= 3) {
                const brgy = parts[0];
                const city = parts[1];
                const prov = parts[2];

                for (let i = 0; i < provinceSelect.options.length; i++) {
                    if (provinceSelect.options[i].value === prov) {
                        provinceSelect.selectedIndex = i;
                        break;
                    }
                }

                populateCities(prov, city, brgy);
            }
        } else if (provinceSelect.value) {
            populateCities(provinceSelect.value);
        }
    }

    // --- 6. Form Submission Validation ---
    if (form) {
        form.addEventListener('submit', function (e) {
            let isValid = true;

            // Reset errors
            document.querySelectorAll('.field-error').forEach(el => el.classList.remove('show'));
            document.querySelectorAll('.form-input').forEach(el => el.classList.remove('error'));

            // Name
            const name = form.event_name.value.trim();
            if (!name) {
                isValid = false;
                document.getElementById('err-name').classList.add('show');
                form.event_name.classList.add('error');
            }

            // Event Type
            if (!eventTypeSelect.value) {
                isValid = false;
                document.getElementById('err-type').classList.add('show');
                eventTypeSelect.classList.add('error');
            } else if (eventTypeSelect.value === 'Other' && !otherEventInput.value.trim()) {
                isValid = false;
                document.getElementById('err-other-type').classList.add('show');
                otherEventInput.classList.add('error');
            }

            // Guests
            const guests = parseInt(guestInput.value) || 0;
            if (guests < minGuests || guests > 1000) {
                isValid = false;
                document.getElementById('err-guests').classList.add('show');
                if (guestDisplay) guestDisplay.classList.add('error');
            }

            // Date
            if (!dateInput.value || new Date(dateInput.value) < new Date(today)) {
                isValid = false;
                document.getElementById('err-date').classList.add('show');
                dateInput.classList.add('error');
            }

            // Time (Required)
            const time = timeInput.value;
            if (!time) {
                isValid = false;
                document.getElementById('err-time').classList.add('show');
                timeInput.classList.add('error');
            }

            // Location Validation
            if (!provinceSelect.value) {
                isValid = false;
                document.getElementById('err-province').classList.add('show');
                provinceSelect.classList.add('error');
            }
            if (!citySelect.value) {
                isValid = false;
                document.getElementById('err-city').classList.add('show');
                citySelect.classList.add('error');
            }
            if (!barangaySelect.value) {
                isValid = false;
                document.getElementById('err-barangay').classList.add('show');
                barangaySelect.classList.add('error');
            }

            if (!isValid) {
                e.preventDefault();
                // Scroll to first error
                const firstError = document.querySelector('.field-error.show');
                if (firstError) {
                    firstError.parentElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });
    }

    // --- 7. Menu Swapping Logic ---
    let activeSlotIndex = null;

    window.openSwapModal = function(category, slotIndex) {
        activeSlotIndex = slotIndex;
        const modal = document.getElementById('swapModal');
        const container = document.getElementById('swapOptionsContainer');
        const title = document.getElementById('modalCategoryTitle');

        title.innerText = `Swap ${category}`;
        container.innerHTML = '<p class="form-subtitle">Loading items...</p>';
        modal.style.display = 'flex';

        // Filter items by category
        const options = window.allMenuItems.filter(i => i.category === category && !i.is_addon);

        if (options.length === 0) {
            container.innerHTML = `<p class="form-subtitle">No other ${category} options available from this caterer.</p>`;
            return;
        }

        container.innerHTML = '';
        options.forEach(item => {
            const card = document.createElement('div');
            card.className = 'swap-option-card';
            card.innerHTML = `
                <div class="soc-info">
                    <span class="soc-name">${item.name}</span>
                    <span class="soc-cat">${item.category}</span>
                </div>
                <button type="button" class="btn-select-swap" onclick="selectSwapItem(${item.id}, '${item.name.replace(/'/g, "\\'")}')">Select</button>
            `;
            card.onclick = () => selectSwapItem(item.id, item.name);
            container.appendChild(card);
        });
    };

    window.closeSwapModal = function() {
        document.getElementById('swapModal').style.display = 'none';
        activeSlotIndex = null;
    };

    window.selectSwapItem = function(itemId, itemName) {
        if (!activeSlotIndex) return;

        const slot = document.getElementById(`slot-${activeSlotIndex}`);
        const input = slot.querySelector('.slot-input');
        const nameSpan = document.getElementById(`name-${activeSlotIndex}`);

        if (input && nameSpan) {
            input.value = itemId;
            nameSpan.innerText = itemName;
            
            // Visual feedback
            slot.style.borderColor = 'var(--wiz-primary)';
            slot.style.background = 'rgba(255, 123, 84, 0.05)';
            setTimeout(() => {
                slot.style.background = 'var(--wiz-slate-50)';
            }, 500);
        }

        closeSwapModal();
    };

    // Close modal on click outside
    window.onclick = function(event) {
        const modal = document.getElementById('swapModal');
        if (event.target == modal) {
            closeSwapModal();
        }
    };

    // Initial run
    updateCalculator();
    loadExistingLocation();
});
