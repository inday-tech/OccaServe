document.addEventListener('DOMContentLoaded', function () {
    const pricePerHead = Number(window.pricePerHead || 0);
    const catererId = Number(window.catererId || 0);
    const minGuests = Number(window.minGuests || 1);
    const phCities = window.PH_CITIES || [];

    // --- Selectors ---
    const form = document.getElementById('detailsForm');
    const guestInput = document.getElementById('guest_count');
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

    // --- Location Data (Laguna Focus) ---
    const LAGUNA_DATA = {
        "Alaminos": ["Barangay I", "Barangay II", "Barangay III", "Barangay IV", "Del Carmen", "Palma", "San Agustin", "San Andres", "San Benito", "San Gregorio", "San Juan", "San Miguel", "San Roque", "Santa Rosa", "Victoria"],
        "Bay": ["Bitin", "Calo", "Dila", "Maitim", "Puypuy", "San Antonio", "San Isidro", "Santa Cruz", "Santo Domingo", "Tagapo"],
        "Biñan": ["Biñan (Poblacion)", "Bungahan", "Canlalay", "Casile", "De La Paz", "Dela Paz", "Ganado", "Langkiwa", "Loma", "Malaban", "Malamig", "Mamplasan", "Platero", "Poblacion", "San Antonio", "San Francisco", "San Jose", "San Vicente", "Santo Niño", "Santo Tomas", "Soro-soro", "Timbao", "Tubigan", "Zapote"],
        "Cabuyao": ["Baclaran", "Banay-Banay", "Banlic", "Bigaa", "Butong", "Casile", "Diezmo", "Gulod", "Mamatid", "Marinig", "Niugan", "Pittland", "Pulo", "Sala", "San Isidro"],
        "Calamba": ["Bagong Kalsada", "Bañadero", "Banlic", "Barandal", "Barangay 1", "Barangay 2", "Barangay 3", "Barangay 4", "Barangay 5", "Barangay 6", "Barangay 7", "Batino", "Bubuyan", "Bucal", "Bunggo", "Burol", "Camaligan", "Canlubang", "Halang", "Hornalan", "Kay-Anlog", "Laguerta", "La Mesa", "Lawa", "Lecheria", "Lingga", "Looc", "Mabato", "Majada Labas", "Makiling", "Mapagong", "Masili", "Maunong", "Mayapa", "Milagrosa", "Palingon", "Palo-Alto", "Pansol", "Parian", "Prinza", "Punta", "Putho Tuntungin", "Real", "Saimsim", "Sampiruhan", "San Cristobal", "San Jose", "San Juan", "Sirang Lupa", "Sucol", "Turbina", "Uwisan"],
        "Calauan": ["Balayhangin", "Bangyas", "Dayap", "Hanggan", "Imok", "Kanluran", "Lamot 1", "Lamot 2", "Limao", "Mabacan", "Masiit", "Paliparan", "Pérez", "Prinza", "San Isidro", "Santo Tomas"],
        "Cavinti": ["Anglas", "Bangco", "Bukal", "Bulajo", "Cansuso", "Duhat", "Inao-Awan", "Labayo", "Layasin", "Layug", "Mahipon", "Paowin", "Poblacion", "Sisilmin", "Sumucab", "Tibatib", "Udia"],
        "Famy": ["Asana", "Bacong-Sangi", "Balitoc", "Banaba", "Batuhan", "Bulihan", "Caballero", "Calumpang", "Kapatalan", "Kataypuanan", "Liyang", "Maatubang", "Mag-Ampon", "Minayutan", "Poblacion", "Salangbato", "Tunhac"],
        "Kalayaan": ["Longos", "San Juan", "San Antonio"],
        "Liliw": ["Bagong Anyo", "Bayate", "Bongkol", "Bubukal", "Cabuyew", "Calumpang", "Culit", "Dagatan", "Daniw", "Dita", "Ibabang Palina", "Ibabang San Roque", "Ibabang Taykin", "Ilayang Palina", "Ilayang San Roque", "Ilayang Taykin", "Kanluran", "Luquin", "Malabo-Kalantukan", "Masikap", "Novillos", "Oogong", "Pag-Asa", "Poblacion", "Rizal", "San Isidro", "Santa Lucia", "Tibatib", "Tuy-Baanan"],
        "Los Baños": ["Anos", "Bagong Silang", "Bambang", "Batong Malake", "Baybayin", "Bayog", "Lalakay", "Maahas", "Malinta", "Mayondon", "Putho Tuntungin", "San Antonio", "Tadlac", "Timugan"],
        "Luisiana": ["De La Paz", "San Antonio", "San Buenaventura", "San Diego", "San Isidro", "San Jose", "San Juan", "San Lorenzo", "San Pablo", "San Pedro", "San Rafael", "San Roque", "San Sebastian", "Santa Catalina", "Santa Lucia", "Santo Domingo", "Santo Tomas"],
        "Lumban": ["Bagong Silang", "Balayu", "Concepcion", "Lewin", "Maytalang I", "Maytalang II", "Maracta", "Poblacion", "Primera Parang", "Primera Pulo", "Salac", "Santo Niño", "Segunda Parang", "Segunda Pulo", "Talahib", "Wawa"],
        "Mabitac": ["Amuyong", "Lambac", "Lucong", "Matalatala", "Nangun", "Pag-Asa", "Poblacion", "San Antonio", "San Francisco", "San Jose", "San Miguel", "San Nicolas", "San Pedro", "San Roque", "San Vicente", "Santa Maria"],
        "Magdalena": ["Alipit", "Baanan", "Balanac", "Bucal", "Buenavista", "Bungkol", "Burol", "Ibabang Atingay", "Ibabang Butnong", "Ilayang Atingay", "Ilayang Butnong", "Malaking Ambling", "Mali-Mali", "Munting Ambling", "Poblacion", "Sabang", "Salasad", "Tanawan", "Tipunan"],
        "Majayjay": ["Amonoy", "Bakia", "Balanac", "Bukal", "Bunga", "Butnong", "Gagalot", "Ibabang Banga", "Ibabang Bayucain", "Ilayang Banga", "Ilayang Bayucain", "Isabang", "Malinao", "May-It", "Munting Kawayan", "Olla", "Oobi", "Pangil", "Panglan", "Piit", "Poblacion", "Rizal", "Suba", "Talortor", "Taytay"],
        "Nagcarlan": ["Abo", "Alibungbungan", "Alumbrado", "Antipolo", "Balayhangin", "Balimbing", "Balinacon", "Bambang", "Banago", "Banca-Banca", "Bangcuro", "Banilad", "Bayaquitos", "Buboy", "Buenavista", "Bunga", "Cabuyew", "Calumpang", "Kanluran Lazaan", "Kanluran Kabubuhayan", "Labangan", "Lawaguin", "Malinao", "Malipunyo", "Manaol", "Maravilla", "Nagcalit", "Oogong", "Poblacion", "Sabang", "San Francisco", "Santa Lucia", "Sulsuguin", "Talahib", "Talangan", "Taytay", "Tibatib", "Wakat"],
        "Paete": ["Barangay 1 - Ibaba", "Barangay 2 - Maytoong", "Barangay 3 - Ermita", "Barangay 4 - Quinale", "Barangay 5 - Ilaya", "Barangay 6 - Ilaya", "Barangay 7 - Bagumbayan", "Barangay 8 - Bangkusay", "Barangay 9 - Ibaba"],
        "Pagsanjan": ["Anahaw", "Barangay I", "Barangay II", "Barangay III", "Bubukal", "Cabanbanan", "Calusiche", "Dingin", "Lambac", "Layugan", "Magdapio", "Maulawin", "Pinagsanjan", "Sabang", "Sampaloc", "San Isidro"],
        "Pakil": ["Baño", "Banilan", "Burgos", "Casa Real", "Casinsin", "Dorado", "Gonzales", "Kabulusan", "Matikiw", "Pangil", "Rizal", "Saray", "Taft", "Tavera"],
        "Pangil": ["Balian", "Isla", "Natividad", "Poblacion", "Sulib", "Galas"],
        "Pila": ["Aplaya", "Bagong Pook", "Bukal", "Bulilan Sur", "Concepcion", "Labuin", "Linga", "Masico", "Mojon", "Pansol", "Poblacion", "San Antonio", "Santa Clara"],
        "Rizal": ["Antipolo", "Entablado", "Laguan", "Pauli 1", "Pauli 2", "Poblacion", "Puypuy", "Talaga", "Talaoc", "Tuy"],
        "San Pablo": ["Barangay I-A", "Barangay I-B", "Barangay II-A", "Barangay II-B", "Barangay III-A", "Barangay III-B", "Barangay IV-A", "Barangay IV-B", "Barangay V-A", "Barangay V-B", "Barangay VI-A", "Barangay VI-B", "Barangay VII-A", "Barangay VII-B", "Atisan", "Bautista", "Concepcion", "Del Remedio", "Dolores", "San Antonio", "San Buenaventura", "San Cristobal", "San Francisco", "San Gabriel", "San Gregorio", "San Ignacio", "San Isidro", "San Jose", "San Juan", "San Lucas", "San Marcos", "San Mateo", "San Miguel", "San Nicolas", "San Pedro", "San Rafael", "San Roque", "San Vicente", "Santa Ana", "Santa Catalina", "Santa Cruz", "Santa Elena", "Santa Filomena", "Santa Maria", "Santa Maria Magdalena", "Santa Monica", "Santa Veronica", "Santiago", "Santisimo Rosario", "Soledad"],
        "San Pedro": ["Bagong Silang", "Chrysanthemum", "Cuyab", "Estrella", "Fatima", "G.S.I.S.", "Holiday Hills", "Lハンドゥング", "Langgam", "Laram", "Magsaysay", "Maharlika", "Narra", "Nueva", "Pacita 1", "Pacita 2", "Poblacion", "Riverside", "Sampaguita Village", "San Antonio", "San Roque", "San Vicente", "Santa Felomina", "Santo Niño", "United Bayanihan", "United Better Living", "Vicente Leyos"],
        "Santa Cruz": ["Alipit", "Bagumbayan", "Bubukal", "Calios", "Duhat", "Gatid", "Jasaan", "Labuin", "Malinao", "Oogong", "Pagsawitan", "Palasan", "Patimbao", "Poblacion", "San Jose", "San Juan", "San Pablo Norte", "San Pablo Sur", "San Pedro", "Santa Cruz", "Santisteban", "Santo Angel Central", "Santo Angel Norte", "Santo Angel Sur"],
        "Santa Maria": ["Bagong Pook", "Bubukal", "Cabooan", "Calangay", "Cambuja", "Coralan", "Juan Santiago", "Kayhakat", "Lungsod", "Macasipac", "Masinao", "Matalatala", "Pao-o", "Parang Ng Buho", "Poblacion", "Real Velasquez", "Santiago", "Talahiban"],
        "Santa Rosa": ["Aplaya", "Balibago", "Caingin", "Dila", "Ditam", "Don Jose", "Ibaba", "Kanluran", "Labas", "Macabling", "Malitlit", "Market Area", "Pook", "Pulong Santa Cruz", "Santo Domingo", "Sinalhan", "Tagapo"],
        "Siniloan": ["Acevida", "Bagong Pag-Asa", "Buhay", "Gen. Luna", "G. Redor", "Halayhayin", "L. De Leon", "Laguio", "Magsaysay", "M. Pandeño", "North Poblacion", "P. Burgos", "Salubungan", "Sambat", "South Poblacion", "Wawa"],
        "Victoria": ["Daniw", "Masapang", "Nanhaya", "Pagalangan", "Poblacion", "San Francisco", "San Roque", "Santa Cruz"]
    };

    // --- 1. Set Min Date to Today ---
    const today = new Date().toISOString().split('T')[0];
    dateInput.setAttribute('min', today);

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

    // --- 5. Cascading Location Choice ---
    function populateCities(province, selectedCity = null) {
        citySelect.innerHTML = '<option value="">-- Select City --</option>';
        barangaySelect.innerHTML = '<option value="">-- Select Barangay --</option>';
        barangaySelect.disabled = true;

        if (province === 'Laguna') {
            citySelect.disabled = false;
            const cities = Object.keys(LAGUNA_DATA).sort();
            cities.forEach(city => {
                const opt = document.createElement('option');
                opt.value = city;
                opt.textContent = city;
                if (city === selectedCity) opt.selected = true;
                citySelect.appendChild(opt);
            });
            if (selectedCity && LAGUNA_DATA[selectedCity]) {
                populateBarangays(selectedCity);
            }
        } else {
            citySelect.disabled = true;
        }
    }

    function populateBarangays(city, selectedBrgy = null) {
        barangaySelect.innerHTML = '<option value="">-- Select Barangay --</option>';
        if (city && LAGUNA_DATA[city]) {
            barangaySelect.disabled = false;
            const barangays = LAGUNA_DATA[city].sort();
            barangays.forEach(brgy => {
                const opt = document.createElement('option');
                opt.value = brgy;
                opt.textContent = brgy;
                if (brgy === selectedBrgy) opt.selected = true;
                barangaySelect.appendChild(opt);
            });
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
            populateBarangays(this.value);
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

                // Set province
                for (let i = 0; i < provinceSelect.options.length; i++) {
                    if (provinceSelect.options[i].value === prov) {
                        provinceSelect.selectedIndex = i;
                        break;
                    }
                }

                // Populate and set city/barangay
                populateCities(prov, city);
                populateBarangays(city, brgy);
            }
        } else if (provinceSelect.value === 'Laguna') {
            // Default Laguna population if selected but no full address yet
            populateCities('Laguna');
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
            if (guests < minGuests) {
                isValid = false;
                document.getElementById('err-guests').classList.add('show');
                guestInput.classList.add('error');
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

    // Initial run
    updateCalculator();
    loadExistingLocation();
});
