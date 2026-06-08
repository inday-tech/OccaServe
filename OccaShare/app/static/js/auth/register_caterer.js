(function () {
    let currentStepCat = 1;
    const totalStepsCat = 4;

    function setError(fieldId, message, isError = true) {
        const wrapper = document.getElementById(fieldId + 'Wrapper');
        const drawer = document.getElementById(fieldId + 'Error');
        if (!wrapper || !drawer) return;

        if (isError) {
            wrapper.classList.add('error');
            drawer.innerText = message;
            drawer.style.display = 'block';
            const input = wrapper.querySelector('input');
            if (input) input.style.borderColor = '#ef4444';
        } else {
            wrapper.classList.remove('error');
            drawer.style.display = 'none';
            const input = wrapper.querySelector('input');
            if (input) input.style.borderColor = '';
        }
    }

    const validateName = (name) => {
        const nameRegex = /^[a-zA-Z\s\.\-']{2,60}$/;
        const dummyNames = ['test', 'dummy', 'guest', 'demo'];
        const lowerName = name.toLowerCase().trim();

        if (!name.trim()) return { valid: false, message: "Required" };
        if (name.length < 2) return { valid: false, message: "Too short" };
        if (name.length > 60) return { valid: false, message: "Too long" };
        if (!nameRegex.test(name)) return { valid: false, message: "Letters/spaces/dots only" };

        if (dummyNames.includes(lowerName)) {
            return { valid: false, message: "Please use your real name" };
        }

        const parts = lowerName.split(/\s+/).filter(p => p.length > 0);
        if (parts.length >= 2) {
            for (let i = 0; i < parts.length; i++) {
                for (let j = i + 1; j < parts.length; j++) {
                    const p1 = parts[i];
                    const p2 = parts[j];
                    if (p1 === p2) {
                        return { valid: false, message: "Avoid repetitive names (e.g. Pepito Pepito)" };
                    }
                }
            }
        }

        return { valid: true };
    };

    const validateSingleName = (input, fieldId, isRequired = true) => {
        if (!input) return { valid: true };
        const val = input.value.trim();

        if (!val) {
            if (isRequired && input.classList.contains('touched')) {
                setError(fieldId, "Required");
                return { valid: false };
            } else {
                setError(fieldId, "", false);
                return { valid: true };
            }
        }

        const result = validateName(val);
        if (!result.valid) {
            setError(fieldId, result.message);
            return { valid: false };
        } else {
            setError(fieldId, "", false);
            return { valid: true };
        }
    };

    const performNameValidation = (e) => {
        const fnInput = document.getElementById('first_name_cat');
        const mnInput = document.getElementById('middle_name_cat');
        const lnInput = document.getElementById('last_name_cat');

        if (e && e.target) {
            e.target.classList.add('touched');
        }

        const fnVal = fnInput ? fnInput.value.trim() : '';
        const lnVal = lnInput ? lnInput.value.trim() : '';

        const fnValid = validateSingleName(fnInput, 'firstNameCat', true);
        const lnValid = validateSingleName(lnInput, 'lastNameCat', true);

        // Use initial validator for M.I.
        if (mnInput) {
            const mnVal = mnInput.value.trim();
            if (mnVal) {
                const res = diamondValidators.middleName(mnVal);
                setError('middleNameCat', res.message, !res.valid);
            } else {
                setError('middleNameCat', "", false);
            }
        }

        if (fnVal && lnVal) {
            if (fnVal.toLowerCase() === lnVal.toLowerCase()) {
                setError('firstNameCat', "First Name and Last Name cannot be identical");
                setError('lastNameCat', "First Name and Last Name cannot be identical");
            } else {
                if (fnValid.valid) setError('firstNameCat', "", false);
                if (lnValid.valid) setError('lastNameCat', "", false);
            }
        }
    };

    const attachNameListeners = () => {
        const fnInput = document.getElementById('first_name_cat');
        const mnInput = document.getElementById('middle_name_cat');
        const lnInput = document.getElementById('last_name_cat');

        if (fnInput) {
            fnInput.addEventListener('input', performNameValidation);
            fnInput.addEventListener('blur', performNameValidation);
        }
        if (mnInput) {
            mnInput.addEventListener('input', performNameValidation);
            mnInput.addEventListener('blur', performNameValidation);
        }
        if (lnInput) {
            lnInput.addEventListener('input', performNameValidation);
            lnInput.addEventListener('blur', performNameValidation);
        }
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', attachNameListeners);
    } else {
        attachNameListeners();
    }

    const LOCATION_DATA = {
        "Laguna": {
            "Alaminos": ["Barangay I", "Barangay II", "Barangay III", "Barangay IV", "Del Carmen", "Palma", "San Agustin", "San Andres", "San Benito", "San Gregorio", "San Juan", "San Miguel", "San Roque", "Santa Rosa", "Victoria"],
            "Bay": ["Bitin", "Calo", "Dila", "Maitim", "Puypuy", "San Antonio", "San Isidro", "Santa Cruz", "Santo Domingo", "Tagapo"],
            "Biñan": ["Biñan (Poblacion)", "Bungahan", "Canlalay", "Casile", "De La Paz", "Dela Paz", "Ganado", "Langkiwa", "Loma", "Malaban", "Malamig", "Mamplasan", "Platero", "Poblacion", "San Antonio", "San Francisco", "San Jose", "San Vicente", "Santo Niño", "Santo Tomas", "Soro-soro", "Timbao", "Tubigan", "Zapote"],
            "Cabuyao": ["Baclaran", "Banay-Banay", "Banlic", "Bigaa", "Butong", "Casile", "Diezmo", "Gulod", "Mamatid", "Marinig", "Niugan", "Pittland", "Pulo", "Sala", "San Isidro"],
            "Calamba": ["Bagong Kalsada", "Bañadero", "Banlic", "Barandal", "Barangay 1", "Barangay 2", "Barangay 3", "Barangay 4", "Barangay 5", "Barangay 6", "Barangay 7", "Batino", "Bubuyan", "Bucal", "Bunggo", "Burol", "Camaligan", "Canlubang", "Halang", "Hornalan", "Kay-Anlog", "Laguerta", "La Mesa", "Lawa", "Lecheria", "Lingga", "Looc", "Mabato", "Majada Labas", "Makiling", "Mapagong", "Masili", "Maunong", "Mayapa", "Milagrosa", "Palingon", "Palo-Alto", "Pansol", "Parian", "Prinza", "Punta", "Putho Tuntungin", "Real", "Saimsim", "Sampiruhan", "San Cristobal", "San Jose", "San Juan", "Sirang Lupa", "Sucol", "Turbina", "Uwisan"],
            "Santa Rosa": ["Aplaya", "Balibago", "Caingin", "Dila", "Ditam", "Don Jose", "Ibaba", "Kanluran", "Labas", "Macabling", "Malitlit", "Market Area", "Pook", "Pulong Santa Cruz", "Santo Domingo", "Sinalhan", "Tagapo"],
            "Los Baños": ["Anos", "Bagong Silang", "Bambang", "Batong Malake", "Baybayin", "Bayog", "Lalakay", "Maahas", "Malinta", "Mayondon", "Putho Tuntungin", "San Antonio", "Tadlac", "Timugan"],
            "San Pedro": ["Bagong Silang", "Chrysanthemum", "Cuyab", "Estrella", "Fatima", "G.S.I.S.", "Holiday Hills", "Lハンドゥング", "Langgam", "Laram", "Magsaysay", "Maharlika", "Narra", "Nueva", "Pacita 1", "Pacita 2", "Poblacion", "Riverside", "Sampaguita Village", "San Antonio", "San Roque", "San Vicente", "Santa Felomina", "Santo Niño", "United Bayanihan", "United Better Living", "Vicente Leyos"]
        },
        "Cavite": {
            "Bacoor": ["Molino I", "Molino II", "Molino III", "Molino IV", "San Nicolas"],
            "Dasmariñas": ["Salawag", "Paliparan I", "Paliparan II", "Sampaloc I", "Sampaloc II"],
            "Imus": ["Anabu I", "Anabu II", "Bucandala I", "Bucandala II", "Poblacion"],
            "Tagaytay": ["Mendez", "San Jose", "Sungay East", "Sungay West", "Silang Junction"]
        },
        "Batangas": {
            "Batangas City": ["Bolbok", "Calicanto", "Kumintang Ibaba", "Kumintang Ilaya", "Poblacion"],
            "Lipa": ["Balintawak", "Marawoy", "Sabang", "Tambo", "Poblacion"],
            "Tanauan": ["Poblacion I", "Poblacion II", "Darasa", "Bagumbayan", "Trapiche"],
            "Sto. Tomas": ["San Bartolome", "San Felix", "San Jose", "San Roque", "Poblacion"]
        },
        "Rizal": {
            "Antipolo": ["San Jose", "San Roque", "Dela Paz", "Dalig", "Mayamot"],
            "Cainta": ["San Andres", "San Juan", "San Roque", "Santo Domingo", "Santa Rosa"],
            "Taytay": ["Dolores", "Muzon", "San Juan", "Santa Ana", "San Isidro"],
            "Binangonan": ["Calumpang", "Layunan", "Libid", "Pila-pila", "Tatala"]
        }
    };

    window.changeStepCat = function (n) {
        const form = document.getElementById('catererForm');
        if (!form) return;
        const steps = form.querySelectorAll('.form-step');
        const pSteps = document.querySelectorAll('.progress-step');

        if (n === 1 && !validateCurrentStepCat()) return;

        steps[currentStepCat - 1].classList.remove('active');
        currentStepCat += n;

        if (currentStepCat > totalStepsCat) {
            submitCatererForm();
            currentStepCat = totalStepsCat;
            return;
        }

        steps[currentStepCat - 1].classList.add('active');

        // Update Progress Tracker
        pSteps.forEach((s, idx) => {
            if (idx + 1 < currentStepCat) s.className = 'progress-step completed';
            else if (idx + 1 === currentStepCat) s.className = 'progress-step active';
            else s.className = 'progress-step';
        });

        // Update Buttons
        const prevBtn = document.getElementById('prevBtnCat');
        const nextBtn = document.getElementById('nextBtnCat');
        if (prevBtn) prevBtn.style.display = currentStepCat === 1 ? 'none' : 'inline-block';

        if (nextBtn) {
            const btnText = nextBtn.querySelector('span');
            const btnIcon = nextBtn.querySelector('i');
            if (btnText) {
                btnText.innerText = currentStepCat === totalStepsCat ? 'Complete Registration' : 'Next Step';
            }
            if (btnIcon) {
                btnIcon.className = currentStepCat === totalStepsCat ? 'fas fa-check-circle' : 'fas fa-chevron-right';
            }
        }
    };

    function validateCurrentStepCat() {
        const step = document.getElementById(`step-${currentStepCat}`);
        if (!step) return true;
        const inputs = step.querySelectorAll('input[required], select[required]');
        let valid = true;

        inputs.forEach(input => {
            if (!input.value.trim()) {
                valid = false;
                input.classList.add('input-error');
                input.style.borderColor = '#ef4444';
            } else {
                input.classList.remove('input-error');
                input.style.borderColor = '';
            }
        });

        // Check for real-time validation errors
        const errorWrappers = step.querySelectorAll('.input-wrapper.error');
        if (errorWrappers.length > 0) {
            valid = false;
        }

        // Security Verification Validation Rule
        if (currentStepCat === 2) {
            const yearsInput = document.getElementById('years_of_operation');
            if (yearsInput) {
                const years = parseInt(yearsInput.value.replace(/,/g, ''));
                if (isNaN(years) || years < 0 || years > 100) {
                    valid = false;
                    setError('years', "Must be between 0 and 100");
                } else {
                    setError('years', "", false);
                }
            }
        }

        if (currentStepCat === 3) {
            // Event Types Validation
            const eventCheckboxes = step.querySelectorAll('input[name="event_type_choice"]:checked');
            const eventErrorDrawer = document.getElementById('eventTypeError');
            if (eventCheckboxes.length === 0) {
                valid = false;
                if (eventErrorDrawer) {
                    eventErrorDrawer.innerText = "Please select at least one event type";
                    eventErrorDrawer.style.display = 'block';
                }
            } else {
                let otherError = false;
                const otherCheck = document.getElementById('eventOtherCheck');
                if (otherCheck && otherCheck.checked) {
                    const otherInput = document.getElementById('event_type_other');
                    if (!otherInput || !otherInput.value.trim()) {
                        valid = false;
                        otherError = true;
                        if (eventErrorDrawer) {
                            eventErrorDrawer.innerText = "Please specify the other event type";
                            eventErrorDrawer.style.display = 'block';
                        }
                        if (otherInput) otherInput.style.borderColor = '#ef4444';
                    } else {
                        if (otherInput) otherInput.style.borderColor = '';
                    }
                }

                if (!otherError && eventErrorDrawer) {
                    eventErrorDrawer.style.display = 'none';
                }
            }



            const minPaxInput = document.getElementById('min_pax');
            const priceInput = document.getElementById('starting_price');

            if (minPaxInput) {
                const pax = parseInt(minPaxInput.value.replace(/,/g, ''));
                if (isNaN(pax) || pax < 1 || pax > 5000) {
                    valid = false;
                    setError('minPax', "Must be between 1 and 5,000");
                } else {
                    setError('minPax', "", false);
                }
            }

            if (priceInput) {
                const price = parseFloat(priceInput.value.replace(/,/g, ''));
                if (isNaN(price) || price < 300 || price > 1000000) {
                    valid = false;
                    setError('price', "Must be between ₱300 and ₱1,000,000");
                } else {
                    setError('price', "", false);
                }
            }
        }

        if (currentStepCat === 4) {
            const permitBox = document.getElementById('permitBoxCat');
            const govIdBox = document.getElementById('govIdBoxCat');

            const permitVerified = permitBox && permitBox.classList.contains('scanned-success');
            const idVerified = govIdBox && govIdBox.classList.contains('scanned-success');

            if (!permitVerified || !idVerified) {
                valid = false;
                alert("⚠️ Verification Required: Please upload and successfully scan your Business Permit and Government ID first.");
            }
        }

        return valid;
    }

    async function submitCatererForm() {
        const form = document.getElementById('catererForm');
        const formData = new FormData(form);
        const submitBtn = document.getElementById('nextBtnCat');
        const btnText = submitBtn?.querySelector('span');
        const originalText = btnText ? btnText.innerText : 'Complete Registration';

        if (submitBtn) submitBtn.disabled = true;
        if (btnText) btnText.innerText = 'Creating Account...';

        // Check for real-time validation errors
        const errorWrappers = form.querySelectorAll('.input-wrapper.error');
        if (errorWrappers.length > 0) {
            if (submitBtn) submitBtn.disabled = false;
            if (btnText) btnText.innerText = originalText;
            return false;
        }

        try {
            updateAddressCat();

            const fn = document.getElementById('first_name_cat')?.value.trim() || '';
            const mn = document.getElementById('middle_name_cat')?.value.trim() || '';
            const ln = document.getElementById('last_name_cat')?.value.trim() || '';
            formData.set('full_name', `${fn} ${mn ? mn + ' ' : ''}${ln}`.trim());
            formData.set('middle_name', mn);

            // Handle Event Types Normalization
            const eventChoices = [];
            document.querySelectorAll('input[name="event_type_choice"]:checked').forEach(cb => {
                if (cb.value !== 'Other') {
                    eventChoices.push(cb.value);
                }
            });
            const otherVal = document.getElementById('event_type_other')?.value.trim();
            if (document.getElementById('eventOtherCheck')?.checked && otherVal) {
                // Split by comma if multiple other events provided
                const others = otherVal.split(',').map(s => s.trim()).filter(s => s.length > 0);
                others.forEach(o => {
                    if (!eventChoices.includes(o)) eventChoices.push(o);
                });
            }
            formData.set('event_types', eventChoices.join(','));

            const response = await fetch('/auth/register', {
                method: 'POST',
                body: formData
            });

            if (response.redirected) {
                const url = new URL(response.url);
                const email = url.searchParams.get('email');

                if (window.openAuthModal) {
                    const emailDisplay = document.getElementById('email-display');
                    const emailField = document.getElementById('emailField');
                    if (emailDisplay) emailDisplay.innerText = email;
                    if (emailField) emailField.value = email;

                    openAuthModal('verify');

                    if (window.Swal) {
                        Swal.fire({
                            icon: 'success',
                            title: 'Almost There!',
                            text: 'Please check your email for the 6-digit verification code.',
                            timer: 5000,
                            showConfirmButton: false,
                            toast: true,
                            position: 'top-end',
                            timerProgressBar: true
                        });
                    }
                } else {
                    window.location.href = response.url;
                }
            } else {
                const result = await response.json();
                if (window.Swal) {
                    Swal.fire({ icon: 'error', title: 'Registration Failed', text: result.message || 'Please check your information and try again.' });
                }
            }
        } catch (error) {
            console.error('Registration error:', error);
        } finally {
            if (submitBtn) submitBtn.disabled = false;
            if (btnText) btnText.innerText = originalText;
        }
    }

    function updateAddressCat() {
        const prov = document.getElementById('province_cat')?.value;
        const city = document.getElementById('city_cat')?.value;
        const brgy = document.getElementById('barangay_cat')?.value;
        const street = document.getElementById('street_cat')?.value;
        const hiddenAddress = document.getElementById('address_cat_hidden');
        if (hiddenAddress) {
            hiddenAddress.value = `${street}, ${brgy}, ${city}, ${prov}`;
        }
    }

    window.updateFileNameCat = function (input, id) {
        const p = document.getElementById(id);
        if (p && input.files.length > 0) p.innerText = input.files[0].name;
    };

    window.previewLogoCat = function (input) {
        const preview = document.getElementById('logoPreviewCat');
        const icon = document.getElementById('uploadIconCat');
        const text = document.getElementById('uploadTextCat');
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = function (e) {
                if (preview) {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                }
                if (icon) icon.style.display = 'none';
                if (text) text.style.display = 'none';
            };
            reader.readAsDataURL(input.files[0]);
        }
    };

    // Relying on inline location_data.js script logic in template forms

    // Make functions available globally for modal buttons
    window.toggleEventOther = function (checkbox) {
        const container = document.getElementById('eventOtherContainer');
        if (container) {
            container.style.display = checkbox.checked ? 'block' : 'none';
            if (checkbox.checked) {
                const input = document.getElementById('event_type_other');
                if (input) input.focus();
            } else {
                // Clear the value and error if unchecked
                const input = document.getElementById('event_type_other');
                if (input) {
                    input.value = '';
                    input.style.borderColor = '';
                }
                const eventErrorDrawer = document.getElementById('eventTypeError');
                if (eventErrorDrawer && eventErrorDrawer.innerText === "Please specify the other event type") {
                    eventErrorDrawer.style.display = 'none';
                }
            }
        }
        if (checkbox && checkbox.parentElement) {
            checkbox.parentElement.classList.toggle('checked', checkbox.checked);
        }
    };

    window.changeStepCat = changeStepCat;

    // Set up real-time error clearing for Step 3
    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('input[name="event_type_choice"]').forEach(cb => {
            cb.addEventListener('change', () => {
                const eventErrorDrawer = document.getElementById('eventTypeError');
                const checked = document.querySelectorAll('input[name="event_type_choice"]:checked');
                if (eventErrorDrawer && checked.length > 0) {
                    // Only hide if the error is about selecting at least one
                    if (eventErrorDrawer.innerText === "Please select at least one event type") {
                        eventErrorDrawer.style.display = 'none';
                    }
                }
            });
        });

        const eventOtherInput = document.getElementById('event_type_other');
        if (eventOtherInput) {
            eventOtherInput.addEventListener('input', () => {
                const eventErrorDrawer = document.getElementById('eventTypeError');
                if (eventOtherInput.value.trim()) {
                    eventOtherInput.style.borderColor = '';
                    if (eventErrorDrawer && eventErrorDrawer.innerText === "Please specify the other event type") {
                        eventErrorDrawer.style.display = 'none';
                    }
                }
            });
        }


    });
})();
