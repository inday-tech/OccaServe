/**
 * DIAMOND STANDARD VALIDATION ENGINE
 * Ported from standalone auth pages to global scope for modal support.
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
        // Only proceed if it's text type (to support commas)
        if (input.type !== 'text') return;
        
        // Save current cursor position
        let cursorPosition = input.selectionStart;
        const originalValue = input.value;
        const valueBeforeCursor = originalValue.slice(0, cursorPosition);
        const digitsBeforeCursor = valueBeforeCursor.replace(/\D/g, '').length;

        // Clean and format
        let cleanValue = originalValue.replace(/\D/g, '');
        if (cleanValue === '') {
            input.value = '';
            return;
        }

        let formattedValue = new Intl.NumberFormat('en-US').format(parseInt(cleanValue));
        input.value = formattedValue;

        // Restore cursor position based on digit count
        let newCursorPos = 0;
        let digitsMatched = 0;
        for (let i = 0; i < formattedValue.length; i++) {
            if (/\d/.test(formattedValue[i])) {
                digitsMatched++;
            }
            newCursorPos = i + 1;
            if (digitsMatched === digitsBeforeCursor) break;
        }
        input.setSelectionRange(newCursorPos, newCursorPos);
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
        }
    };

    // --- CORE VALIDATORS ---
    window.diamondValidators = {
        name: (name) => {
            const nameRegex = /^[a-zA-Z\s\.\-']{2,60}$/;
            const dummyNames = ['test', 'dummy', 'guest', 'demo'];
            const lowerName = name.toLowerCase().trim();

            if (!name.trim()) return { valid: false, message: "Required" };
            if (name.length < 2) return { valid: false, message: "Too short" };
            if (!nameRegex.test(name)) return { valid: false, message: "Letters/spaces only" };
            if (dummyNames.includes(lowerName)) return { valid: false, message: "Use your real name" };
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
            const repetitiveRegex = /(.)\1\1/;
            const valClean = val.replace(/\s/g, '');

            if (!valClean) return { valid: false, message: "Required" };
            if (!mobileRegex.test(valClean)) return { valid: false, message: "11 digits (09XXXXXXXXX)" };
            if (repetitiveRegex.test(valClean)) return { valid: false, message: "Invalid repetitive digits" };
            return { valid: true };
        },
        password: (p) => {
            if (!p) return { valid: false, message: "Required" };
            if (p.length < 8) return { valid: false, message: "At least 8 characters" };
            if (!/[A-Z]/.test(p)) return { valid: false, message: "Needs an uppercase letter" };
            if (!/[0-9]/.test(p)) return { valid: false, message: "Needs a number" };
            if (!/[!@#$%^&*(),.?":{}|<>]/.test(p)) return { valid: false, message: "Needs a special character" };
            return { valid: true };
        },
        years: (v) => {
            const cleanV = String(v).replace(/,/g, '');
            if (cleanV === "" || cleanV === "null" || cleanV === "undefined") return { valid: false, message: "Years in Business is required." };
            if (!/^[0-9]+$/.test(cleanV)) return { valid: false, message: "Numbers only." };
            const n = parseInt(cleanV);
            if (n < 0 || n > 100) return { valid: false, message: "Enter a valid number (0-100)." };
            return { valid: true };
        },
        minPax: (v) => {
            const cleanV = String(v).replace(/,/g, '');
            if (cleanV === "" || cleanV === "null" || cleanV === "undefined") return { valid: false, message: "Minimum Pax is required." };
            if (!/^[0-9]+$/.test(cleanV)) return { valid: false, message: "Whole numbers only." };
            const n = parseInt(cleanV);
            if (n < 1 || n > 5000) return { valid: false, message: "Enter a valid number (1-5000)." };
            return { valid: true };
        },
        price: (v) => {
            const cleanV = String(v).replace(/,/g, '');
            if (cleanV === "" || cleanV === "null" || cleanV === "undefined") return { valid: false, message: "Starting Price is required." };
            const n = parseFloat(cleanV);
            if (isNaN(n) || n < 300 || n > 1000000) return { valid: false, message: "Price must be between 300 and 1,000,000." };
            return { valid: true };
        }
    };

    // --- BINDING LOGIC ---
    window.initDiamondValidation = function(rootElement = document) {
        console.log("Diamond Validation Initializing...");
        
        const emailInputs = rootElement.querySelectorAll('input[type="email"]');
        const nameInputs = rootElement.querySelectorAll('input[name="full_name"]');
        const mobileInputs = rootElement.querySelectorAll('input[type="tel"]');
        const passInputs = rootElement.querySelectorAll('input[type="password"]');
        const yearInputs = rootElement.querySelectorAll('input[name="years_of_operation"]');
        const paxInputs = rootElement.querySelectorAll('input[name="min_pax"]');
        const priceInputs = rootElement.querySelectorAll('input[name="starting_price"]');
        const commaInputs = rootElement.querySelectorAll('.js-format-comma');

        // Apply formatting listeners
        commaInputs.forEach(input => {
            input.addEventListener('input', function() {
                window.applyCommaFormatting(this);
            });
        });

        const debouncedEmailCheck = debounce(async (input) => {
            const { valid, message } = window.diamondValidators.email(input.value);
            const isCat = input.id.includes('cat');
            const prefix = isCat ? 'emailCat' : 'email';
            
            if (!valid) {
                window.setDiamondError(prefix, message);
                return;
            }

            try {
                const response = await fetch(`/auth/check-email?email=${encodeURIComponent(input.value)}`);
                const data = await response.json();
                if (!data.available) {
                    window.setDiamondError(prefix, data.message || "Email already taken");
                } else {
                    window.setDiamondError(prefix, "", false);
                }
            } catch (err) { console.error("Email check failed", err); }
        }, 500);

        emailInputs.forEach(input => {
            input.addEventListener('input', () => debouncedEmailCheck(input));
        });

        nameInputs.forEach(input => {
            input.addEventListener('input', function() {
                const prefix = this.id.includes('cat') ? 'fullNameCat' : 'name';
                const { valid, message } = window.diamondValidators.name(this.value);
                window.setDiamondError(prefix, message, !valid);
            });
        });

        mobileInputs.forEach(input => {
            input.addEventListener('input', function() {
                const prefix = this.id.includes('cat') ? 'mobileCat' : 'mobile';
                const { valid, message } = window.diamondValidators.mobile(this.value);
                window.setDiamondError(prefix, message, !valid);
            });
        });

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
                    // Main password validation
                    const { valid, message } = window.diamondValidators.password(this.value);
                    window.setDiamondError(prefix, message, !valid);

                    // Re-check confirm if it exists
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

        yearInputs.forEach(input => {
            input.addEventListener('input', function() {
                const { valid, message } = window.diamondValidators.years(this.value);
                window.setDiamondError('years', message, !valid);
            });
        });

        paxInputs.forEach(input => {
            input.addEventListener('input', function() {
                const { valid, message } = window.diamondValidators.minPax(this.value);
                window.setDiamondError('minPax', message, !valid);
            });
        });

        priceInputs.forEach(input => {
            input.addEventListener('input', function() {
                const { valid, message } = window.diamondValidators.price(this.value);
                window.setDiamondError('price', message, !valid);
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
