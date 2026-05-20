/**
 * DIAMOND STANDARD VALIDATION ENGINE
 * Centralized globally for OccaServe modal and standalone signup support.
 */

(function() {
    // Utility for debouncing
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Comma formatter for numeric inputs
    window.applyCommaFormatting = function(input) {
        if (input.type !== 'text') return;
        
        let cursorPosition = input.selectionStart;
        const originalValue = input.value;
        
        // Split into integer and decimal parts
        let parts = originalValue.split('.');
        let integerPart = parts[0].replace(/\D/g, '');
        let decimalPart = parts.length > 1 ? parts[1].replace(/\D/g, '').slice(0, 2) : null;

        if (integerPart === '' && decimalPart === null) {
            input.value = '';
            return;
        }

        let formattedInteger = integerPart ? new Intl.NumberFormat('en-US').format(parseInt(integerPart)) : '0';
        let formattedValue = decimalPart !== null ? `${formattedInteger}.${decimalPart}` : formattedInteger;
        
        if (input.value !== formattedValue) {
            input.value = formattedValue;
        }
    };

    const getStringSimilarity = (s1, s2) => {
        let longer = s1;
        let shorter = s2;
        if (s1.length < s2.length) {
            longer = s2;
            shorter = s1;
        }
        const longerLength = longer.length;
        if (longerLength === 0) return 1.0;
        return (longerLength - editDistance(longer, shorter)) / parseFloat(longerLength);
    };

    const editDistance = (s1, s2) => {
        s1 = s1.toLowerCase();
        s2 = s2.toLowerCase();
        const costs = [];
        for (let i = 0; i <= s1.length; i++) {
            let lastValue = i;
            for (let j = 0; j <= s2.length; j++) {
                if (i === 0) costs[j] = j;
                else {
                    if (j > 0) {
                        let newValue = costs[j - 1];
                        if (s1.charAt(i - 1) !== s2.charAt(j - 1))
                            newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
                        costs[j - 1] = lastValue;
                        lastValue = newValue;
                    }
                }
            }
            if (i > 0) costs[s2.length] = lastValue;
        }
        return costs[s2.length];
    };

    // --- UI HELPERS ---
    window.setDiamondError = function(fieldId, message, isError = true) {
        const wrapper = document.getElementById(fieldId + 'Wrapper');
        const drawer = document.getElementById(fieldId + 'Error');
        if (!wrapper || !drawer) return;

        if (isError) {
            wrapper.classList.add('error');
            drawer.innerText = message;
        } else {
            wrapper.classList.remove('error');
            drawer.innerText = ''; // Clear text completely when valid
        }
    };

    // --- CORE VALIDATORS ---
    window.diamondValidators = {
        name: (name) => {
            const nameRegex = /^[a-zA-ZñÑ\s\.\-']{2,60}$/;
            const dummyNames = ['test', 'dummy', 'guest', 'demo'];
            const lowerName = name.toLowerCase().trim();

            if (!name.trim()) return { valid: false, message: "Required" };
            if (name.length < 2) return { valid: false, message: "Too short" };
            if (!nameRegex.test(name)) return { valid: false, message: "Letters only" };
            if (dummyNames.includes(lowerName)) return { valid: false, message: "Use your real name" };
            
            // Smart gibberish check (3+ consecutive identical characters)
            if (/(.)\1\1/.test(lowerName)) {
                return { valid: false, message: "No repeating chars" };
            }
            
            return { valid: true };
        },
        middleName: (val) => {
            if (!val) return { valid: true }; // Optional
            return window.diamondValidators.name(val);
        },
        businessNameFormat: (name) => {
            if (!name) return { valid: false, message: "Business Name required" };
            if (name.length < 3) return { valid: false, message: "Too short (min 3)" };
            if (/^\d+$/.test(name)) return { valid: false, message: "Cannot be only numbers" };
            if (/(.)\1\1\1/.test(name.toLowerCase())) return { valid: false, message: "Excessive repetitive characters" };
            return { valid: true };
        },
        email: (email) => {
            const emailRegex = /^[a-zA-Z0-9._%+-]+@gmail\.com$/;
            if (!email) return { valid: false, message: "Required" };
            if (!emailRegex.test(email)) return { valid: false, message: "Gmail only (example@gmail.com)" };
            return { valid: true };
        },
        mobile: (val) => {
            const mobileRegex = /^(09|\+639)\d{9}$/;
            const valClean = val.replace(/\s/g, '');

            if (!valClean) return { valid: false, message: "Required" };
            if (!mobileRegex.test(valClean)) return { valid: false, message: "Format: 09XXXXXXXXX (11 digits)" };
            return { valid: true };
        },
        password: (p) => {
            if (!p) return { valid: false, message: "Required" };
            if (p.length < 8 || !/[A-Z]/.test(p) || !/[0-9]/.test(p) || !/[!@#$%^&*(),.?":{}|<>]/.test(p)) {
                return { valid: false, message: "Min 8 chars, Uppercase, Number & Symbol" };
            }
            return { valid: true };
        },
        years: (v) => {
            const cleanV = String(v).replace(/,/g, '');
            if (cleanV === "" || cleanV === "null" || cleanV === "undefined") return { valid: false, message: "Required" };
            if (!/^[0-9]+$/.test(cleanV)) return { valid: false, message: "Numbers only." };
            const n = parseInt(cleanV);
            if (n < 0 || n > 100) return { valid: false, message: "Enter a valid number (0-100)." };
            return { valid: true };
        },
        minPax: (v) => {
            const cleanV = String(v).replace(/,/g, '');
            if (cleanV === "" || cleanV === "null" || cleanV === "undefined") return { valid: false, message: "Required" };
            if (!/^[0-9]+$/.test(cleanV)) return { valid: false, message: "Whole numbers only." };
            const n = parseInt(cleanV);
            if (n < 1 || n > 5000) return { valid: false, message: "Enter a valid number (1-5000)." };
            return { valid: true };
        },
        price: (v) => {
            const cleanV = String(v).replace(/,/g, '');
            if (cleanV === "" || cleanV === "null" || cleanV === "undefined") return { valid: false, message: "Required" };
            const n = parseFloat(cleanV);
            if (isNaN(n) || n < 300 || n > 1000000) return { valid: false, message: "Price must be between 300 and 1,000,000." };
            return { valid: true };
        }
    };

    // --- BINDING LOGIC ---
    window.initDiamondValidation = function(rootElement = document) {
        console.log("Diamond Validation Initializing...");

        const emailInputs = Array.from(rootElement.querySelectorAll('input[type="email"]')).filter(el => !el.id.includes('login'));
        const mobileInputs = Array.from(rootElement.querySelectorAll('input[type="tel"], input[name="mobile_number"]')).filter(el => !el.id.includes('login'));
        const passInputs = Array.from(rootElement.querySelectorAll('input[type="password"]')).filter(el => !el.id.includes('login'));
        const yearInputs = Array.from(rootElement.querySelectorAll('input[name="years_of_operation"]')).filter(el => !el.id.includes('login'));
        const paxInputs = Array.from(rootElement.querySelectorAll('input[name="min_pax"]')).filter(el => !el.id.includes('login'));
        const priceInputs = Array.from(rootElement.querySelectorAll('input[name="starting_price"]')).filter(el => !el.id.includes('login'));
        const commaInputs = Array.from(rootElement.querySelectorAll('.js-format-comma')).filter(el => !el.id.includes('login'));
        const businessInputs = Array.from(rootElement.querySelectorAll('input[name="business_name"]')).filter(el => !el.id.includes('login'));
        const barangaySelects = Array.from(rootElement.querySelectorAll('select[id*="barangay"]'));

        // Apply formatting listeners
        commaInputs.forEach(input => {
            input.addEventListener('input', function() {
                window.applyCommaFormatting(this);
            });
        });

        // Real-time Barangay Validation (clears error on selection)
        barangaySelects.forEach(select => {
            select.addEventListener('change', function() {
                const fieldIdPrefix = this.id.replace('barangay_', '').replace('_cat', '');
                const errorFieldId = fieldIdPrefix ? `barangay${fieldIdPrefix.charAt(0).toUpperCase() + fieldIdPrefix.slice(1)}` : 'barangay';

                if (this.value && this.value.trim() !== '') {
                    window.setDiamondError(errorFieldId, '', false);
                }
            });
        });

        // Real-time City/Municipality Validation (clears error on selection)
        const citySelects = Array.from(rootElement.querySelectorAll('select[id*="city"]'));
        citySelects.forEach(select => {
            select.addEventListener('change', function() {
                const fieldIdPrefix = this.id.replace('city_', '').replace('_cat', '');
                const errorFieldId = fieldIdPrefix ? `city${fieldIdPrefix.charAt(0).toUpperCase() + fieldIdPrefix.slice(1)}` : 'city';

                if (this.value && this.value.trim() !== '') {
                    window.setDiamondError(errorFieldId, '', false);
                }
            });
        });

        // Real-time Province Validation (clears error on selection)
        const provinceSelects = Array.from(rootElement.querySelectorAll('select[id*="province"]'));
        provinceSelects.forEach(select => {
            select.addEventListener('change', function() {
                const fieldIdPrefix = this.id.replace('province_', '').replace('_cat', '');
                const errorFieldId = fieldIdPrefix ? `province${fieldIdPrefix.charAt(0).toUpperCase() + fieldIdPrefix.slice(1)}` : 'province';

                if (this.value && this.value.trim() !== '') {
                    window.setDiamondError(errorFieldId, '', false);
                }
            });
        });

        // 1. Debounced Email Uniqueness Check (Fires instantly on error, debounces unique query)
        const checkEmailUniqueness = async (input, prefix) => {
            try {
                const response = await fetch(`/auth/check-email?email=${encodeURIComponent(input.value)}`);
                const data = await response.json();
                if (!data.available) {
                    window.setDiamondError(prefix, data.message || "Email already taken");
                } else {
                    window.setDiamondError(prefix, "", false);
                }
            } catch (err) { console.error("Email check failed", err); }
        };
        const debouncedEmailUnique = debounce(checkEmailUniqueness, 500);

        emailInputs.forEach(input => {
            input.addEventListener('input', function() {
                const isCat = this.id.includes('cat');
                const prefix = isCat ? 'emailCat' : 'email';
                
                const { valid, message } = window.diamondValidators.email(this.value);
                if (!valid) {
                    window.setDiamondError(prefix, message);
                } else {
                    window.setDiamondError(prefix, "", false);
                    debouncedEmailUnique(this, prefix);
                }
            });
        });

        // 2. Debounced Mobile Phone Uniqueness Check
        const checkPhoneUniqueness = async (input, prefix) => {
            const val = input.value.replace(/\s/g, '');
            try {
                const response = await fetch(`/auth/check-phone?phone=${encodeURIComponent(val)}`);
                const data = await response.json();
                if (!data.available) {
                    window.setDiamondError(prefix, data.message || "This number is already registered.");
                } else {
                    window.setDiamondError(prefix, "", false);
                }
            } catch (err) { console.error("Phone check failed", err); }
        };
        const debouncedPhoneUnique = debounce(checkPhoneUniqueness, 500);

        mobileInputs.forEach(input => {
            input.addEventListener('input', function() {
                const isCat = this.id.includes('cat');
                const prefix = isCat ? 'mobileCat' : 'mobile';
                
                const { valid, message } = window.diamondValidators.mobile(this.value);
                if (!valid) {
                    window.setDiamondError(prefix, message);
                } else {
                    window.setDiamondError(prefix, "", false);
                    debouncedPhoneUnique(this, prefix);
                }
            });
        });

        // 3. Smart Cross-Field Name Validation (First != Middle != Last)
        const firstNameElements = rootElement.querySelectorAll('input[name="first_name"]');
        const middleNameElements = rootElement.querySelectorAll('input[name="middle_name"]');
        const lastNameElements = rootElement.querySelectorAll('input[name="last_name"]');

        const crossCheckNames = (isCat) => {
            const suffix = isCat ? '_cat' : '';
            const fInput = document.getElementById('first_name' + suffix);
            const mInput = document.getElementById('middle_name' + suffix);
            const lInput = document.getElementById('last_name' + suffix);

            const fVal = (fInput?.value || '').trim();
            const mVal = (mInput?.value || '').trim();
            const lVal = (lInput?.value || '').trim();
            
            const fPrefix = isCat ? 'firstNameCat' : 'firstName';
            const mPrefix = isCat ? 'middleNameCat' : 'middleName';
            const lPrefix = isCat ? 'lastNameCat' : 'lastName';

            // Reset field validations
            const fRes = window.diamondValidators.name(fVal);
            const lRes = window.diamondValidators.name(lVal);
            const mRes = mVal ? window.diamondValidators.name(mVal) : { valid: true };

            if (fInput && (fInput.classList.contains('touched') || fVal)) {
                window.setDiamondError(fPrefix, fRes.message, !fRes.valid);
            } else {
                window.setDiamondError(fPrefix, "", false);
            }

            if (lInput && (lInput.classList.contains('touched') || lVal)) {
                window.setDiamondError(lPrefix, lRes.message, !lRes.valid);
            } else {
                window.setDiamondError(lPrefix, "", false);
            }

            if (mInput && (mInput.classList.contains('touched') || mVal)) {
                window.setDiamondError(mPrefix, mRes.message, !mRes.valid);
            } else {
                window.setDiamondError(mPrefix, "", false);
            }

            // Identical checks First / Middle / Last
            if (fVal && lVal && fVal.toLowerCase() === lVal.toLowerCase()) {
                window.setDiamondError(fPrefix, "First & Last name cannot be identical");
                window.setDiamondError(lPrefix, "First & Last name cannot be identical");
            }
            if (fVal && mVal && fVal.toLowerCase() === mVal.toLowerCase()) {
                window.setDiamondError(fPrefix, "First & Middle name cannot be identical");
                window.setDiamondError(mPrefix, "First & Middle name cannot be identical");
            }
            if (mVal && lVal && mVal.toLowerCase() === lVal.toLowerCase()) {
                window.setDiamondError(mPrefix, "Middle & Last name cannot be identical");
                window.setDiamondError(lPrefix, "Middle & Last name cannot be identical");
            }

            // Sync hidden fullname if on caterer form
            if (isCat && typeof window.composeFullNameCat === 'function') {
                window.composeFullNameCat();
            }
        };

        const setupNameListeners = (inputs) => {
            inputs.forEach(input => {
                input.addEventListener('input', function() {
                    this.classList.add('touched');
                    crossCheckNames(this.id.includes('cat'));
                });
                input.addEventListener('blur', function() {
                    this.classList.add('touched');
                    crossCheckNames(this.id.includes('cat'));
                });
            });
        };

        setupNameListeners(firstNameElements);
        setupNameListeners(middleNameElements);
        setupNameListeners(lastNameElements);

        // 4. Passwords validation
        passInputs.forEach(input => {
            input.addEventListener('input', function() {
                const isCat = this.id.includes('cat');
                const isConfirm = this.id.includes('confirm');
                const prefix = isConfirm ? (isCat ? 'confirmCat' : 'confirm') : (isCat ? 'passwordCat' : 'password');

                if (isConfirm) {
                    const mainPassId = isCat ? 'password_cat' : 'password';
                    const mainPass = document.getElementById(mainPassId)?.value;
                    if (this.value && mainPass && this.value !== mainPass) {
                        window.setDiamondError(prefix, "Passwords do not match");
                    } else {
                        window.setDiamondError(prefix, "", false);
                    }
                } else {
                    const { valid, message } = window.diamondValidators.password(this.value);
                    window.setDiamondError(prefix, message, !valid);

                    // Re-check confirm
                    const confirmId = isCat ? 'confirm_password_cat' : 'confirm_password';
                    const confirmInput = document.getElementById(confirmId);
                    if (confirmInput && confirmInput.value) {
                        const confirmPrefix = isCat ? 'confirmCat' : 'confirm';
                        if (confirmInput.value !== this.value) {
                            window.setDiamondError(confirmPrefix, "Passwords do not match");
                        } else {
                            window.setDiamondError(confirmPrefix, "", false);
                        }
                    }
                }
            });
        });

        // 5. Numerical Inputs (Caterer operation metrics with strict input-blocking)
        yearInputs.forEach(input => {
            let lastValidValue = input.value;

            // Restrict input to digits and range [0-100]
            input.addEventListener('input', function(e) {
                let cleanVal = this.value.replace(/,/g, '');

                if (cleanVal === '') {
                    lastValidValue = '';
                    return;
                }

                // Strip non-digits
                if (!/^[0-9]+$/.test(cleanVal)) {
                    cleanVal = cleanVal.replace(/[^0-9]/g, '');
                }

                const num = parseInt(cleanVal, 10);

                if (isNaN(num)) {
                    this.value = '';
                    lastValidValue = '';
                } else if (num > 100) {
                    // Block input exceeding 100 by reverting to last valid state
                    this.value = lastValidValue;
                } else {
                    this.value = cleanVal;
                    lastValidValue = cleanVal;
                }

                // Maintain comma formatting if necessary
                if (typeof window.applyCommaFormatting === 'function') {
                    window.applyCommaFormatting(this);
                }

                // Show/hide live validation message
                const { valid, message } = window.diamondValidators.years(this.value);
                window.setDiamondError('years', message, !valid);
            });

            // Prevent characters like e, E, +, -, and decimal points .
            input.addEventListener('keydown', function(e) {
                if (['e', 'E', '+', '-', '.'].includes(e.key)) {
                    e.preventDefault();
                }
            });
        });

        paxInputs.forEach(input => {
            let lastValidValue = input.value;

            input.addEventListener('input', function(e) {
                let cleanVal = this.value.replace(/,/g, '');
                if (cleanVal === '') {
                    lastValidValue = '';
                    window.setDiamondError('minPax', "Required", true);
                    return;
                }

                if (!/^[0-9]+$/.test(cleanVal)) {
                    cleanVal = cleanVal.replace(/[^0-9]/g, '');
                }

                const num = parseInt(cleanVal, 10);
                if (isNaN(num)) {
                    this.value = '';
                    lastValidValue = '';
                } else if (num > 5000) {
                    this.value = lastValidValue;
                } else {
                    this.value = cleanVal;
                    lastValidValue = cleanVal;
                }

                if (typeof window.applyCommaFormatting === 'function') {
                    window.applyCommaFormatting(this);
                }

                const { valid, message } = window.diamondValidators.minPax(this.value);
                window.setDiamondError('minPax', message, !valid);
            });

            input.addEventListener('keydown', function(e) {
                if (['e', 'E', '+', '-', '.'].includes(e.key)) {
                    e.preventDefault();
                }
            });
        });

        priceInputs.forEach(input => {
            let lastValidValue = input.value;

            input.addEventListener('input', function(e) {
                let cleanVal = this.value.replace(/,/g, '');
                if (cleanVal === '') {
                    lastValidValue = '';
                    window.setDiamondError('price', "Required", true);
                    return;
                }

                if (!/^[0-9]+$/.test(cleanVal)) {
                    cleanVal = cleanVal.replace(/[^0-9]/g, '');
                }

                const num = parseFloat(cleanVal);
                if (isNaN(num)) {
                    this.value = '';
                    lastValidValue = '';
                } else if (num > 1000000) {
                    this.value = lastValidValue;
                } else {
                    this.value = cleanVal;
                    lastValidValue = cleanVal;
                }

                if (typeof window.applyCommaFormatting === 'function') {
                    window.applyCommaFormatting(this);
                }

                const { valid, message } = window.diamondValidators.price(this.value);
                window.setDiamondError('price', message, !valid);
            });

            input.addEventListener('keydown', function(e) {
                if (['e', 'E', '+', '-', '.'].includes(e.key)) {
                    e.preventDefault();
                }
            });
        });

        // 6. Debounced Business Name Uniqueness Check
        const checkBusinessUniqueness = async (input) => {
            try {
                const response = await fetch(`/auth/check-business-name?name=${encodeURIComponent(input.value)}`);
                const data = await response.json();
                if (!data.available) {
                    window.setDiamondError('businessName', "Business name already registered");
                } else {
                    window.setDiamondError('businessName', "", false);
                }
            } catch (e) { console.warn("Uniqueness check failed", e); }
        };
        const debouncedBusinessUnique = debounce(checkBusinessUniqueness, 500);

        businessInputs.forEach(input => {
            input.addEventListener('input', function() {
                const { valid, message } = window.diamondValidators.businessNameFormat(this.value);
                if (!valid) {
                    window.setDiamondError('businessName', message);
                } else {
                    window.setDiamondError('businessName', "", false);
                    debouncedBusinessUnique(this);
                }
            });
        });
    };

    // Initialize once globally
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => window.initDiamondValidation());
    } else {
        window.initDiamondValidation();
    }
})();
