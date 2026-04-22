(function () {
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

    // New UI Helper: Toggle Error Drawer
    function setError(fieldId, message, isError = true) {
        const wrapper = document.getElementById(fieldId + 'Wrapper');
        const drawer = document.getElementById(fieldId + 'Error');
        if (!wrapper || !drawer) return;

        if (isError) {
            wrapper.classList.add('error');
            wrapper.classList.remove('warning');
            drawer.innerText = message;
        } else {
            wrapper.classList.remove('error');
            wrapper.classList.remove('warning');
        }
    }

    function setWarning(fieldId, message) {
        const wrapper = document.getElementById(fieldId + 'Wrapper');
        const drawer = document.getElementById(fieldId + 'Error');
        if (!wrapper || !drawer) return;

        wrapper.classList.add('warning');
        wrapper.classList.remove('error');
        drawer.innerText = message;
    }

    window.updateUI = function (role) {
        const welcomeText = document.getElementById('welcomeText');
        const roleLabel = document.getElementById('roleLabel');
        const roleToggleLink = document.getElementById('roleToggleLink');
        const roleInput = document.getElementById('roleInput');

        if (role === 'caterer') {
            welcomeText.innerText = 'Partner with OccaServe and grow your catering business';
            roleLabel.innerText = 'Regular customer?';
            roleToggleLink.innerText = 'Switch to Customer';
            roleInput.value = 'caterer';
        } else {
            welcomeText.innerText = 'Start your extraordinary event journey today';
            roleLabel.innerText = 'Business owner?';
            roleToggleLink.innerText = 'Switch to Caterer';
            roleInput.value = 'customer';
        }
    };

    window.switchRole = function () {
        const currentRole = document.getElementById('roleInput').value;
        if (currentRole === 'customer') {
            window.location.href = "/auth/register/caterer";
        } else {
            window.updateUI('customer');
        }
    };

    window.onload = function () {
        const urlParams = new URLSearchParams(window.location.search);
        const role = urlParams.get('role');
        if (role) window.updateUI(role);
    };

    const mobileInput = document.getElementById('mobile_number');
    if (mobileInput) {
        mobileInput.oninput = function () {
            const val = this.value.replace(/\s/g, '');
            const mobileRegex = /^(09|\+639)\d{9}$/;
            const repetitiveRegex = /(.)\1\1/;
            const dummyNums = ['09123456789', '09111111111', '09000000000', '09999999999'];
            
            if (val.length > 0 && !mobileRegex.test(val)) {
                setError('mobile', "Format: 09XXXXXXXXX (11 digits)");
            } else if (repetitiveRegex.test(val)) {
                setError('mobile', "Too many repetitive digits (e.g., 111)");
            } else if (dummyNums.includes(val)) {
                setError('mobile', "Please use a real, active mobile number");
            } else {
                setError('mobile', "", false);
            }
        };
    }

    const checkStrength = (p) => {
        let strength = 0;
        let hints = [];
        if (p.length >= 8) strength++; else hints.push("8+ chars");
        if (p.length >= 10) strength++;
        if (/[A-Z]/.test(p)) strength++; else hints.push("uppercase");
        if (/[a-z]/.test(p)) strength++;
        if (/[0-9]/.test(p)) strength++; else hints.push("number");
        if (/[^A-Za-z0-9]/.test(p)) strength++; else hints.push("special char");

        return { strength, hints };
    };

    const validatePasswords = () => {
        const pass = document.getElementById('password');
        const confirm = document.getElementById('confirm_password');

        if (pass && pass.value) {
            const { strength, hints } = checkStrength(pass.value);
            if (pass.value.length < 8) {
                setError('password', "At least 8 characters");
            } else if (!/[A-Z]/.test(pass.value)) {
                setError('password', "Must have uppercase letter");
            } else if (!/[a-z]/.test(pass.value)) {
                setError('password', "Must have lowercase letter");
            } else if (!/[0-9]/.test(pass.value)) {
                setError('password', "Must have a number");
            } else if (!/[!@#$%^&*(),.?":{}|<>]/.test(pass.value)) {
                setError('password', "Must have special character");
            } else {
                setError('password', "", false);
            }
        } else {
            setError('password', "", false);
        }

        if (confirm && pass && confirm.value && pass.value !== confirm.value) {
            setError('confirm', "Passwords do not match");
        } else if (confirm) {
            setError('confirm', "", false);
        }
    };

    const passInput = document.getElementById('password');
    const confirmInput = document.getElementById('confirm_password');
    if (passInput) passInput.oninput = validatePasswords;
    if (confirmInput) confirmInput.oninput = validatePasswords;

    const getEntropy = (str) => {
        const len = str.length;
        if (len === 0) return 0;
        const counts = {};
        for (let char of str) counts[char] = (counts[char] || 0) + 1;
        let entropy = 0;
        for (let char in counts) {
            const p = counts[char] / len;
            entropy -= p * Math.log2(p);
        }
        return entropy;
    };

    const isGibberish = (str) => {
        const s = str.toLowerCase().replace(/[^a-z]/g, '');
        if (s.length === 0) return false;

        // Vowel/Consonant Ratio
        const vowels = s.match(/[aeiouy]/g) || [];
        const consonants = s.match(/[bcdfghjklmnpqrstvwxz]/g) || [];
        const ratio = consonants.length / (vowels.length || 1);

        // Relaxed ratio from 3 to 10 to allow consonant-heavy handles/names
        if (ratio > 10 || (vowels.length === 0 && s.length > 4)) return true;

        // Entropy check for randomness - relaxed to 4.0
        const entropy = getEntropy(s);
        if (s.length > 6 && entropy > 4.0) return true;

        return false;
    };

    const isKeyboardWalk = (str) => {
        const walks = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm', '1234567890', 'poiuytrewq', 'lkjhgfdsa', 'mnbvcxz'];
        const s = str.toLowerCase();
        if (s.length < 3) return false;
        for (let walk of walks) {
            for (let i = 0; i <= walk.length - 3; i++) {
                const sub = walk.substring(i, i + 3);
                if (s.includes(sub)) return true;
            }
        }
        return false;
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

    const validateEmail = (email) => {
        const emailRegex = /^[a-zA-Z0-9._%+-]+@gmail\.com$/;
        if (!email) return { valid: false, message: "Required" };
        if (!emailRegex.test(email)) return { valid: false, message: "Gmail only (example@gmail.com)" };
        
        const local = email.split('@')[0].toLowerCase();
        const dummyPatterns = ['dummy', 'asdf', 'qwerty', '123456', 'demo'];
        
        if (local.length < 3 && /^\d+$/.test(local)) {
            return { valid: false, message: "Please use a more descriptive email address" };
        }
        if (local.length < 2) {
            return { valid: false, message: "Email prefix too short" };
        }
        if (dummyPatterns.includes(local) || ['123', 'abc', 'aaa', 'qwe'].includes(local)) {
            return { valid: false, message: "Placeholder emails not allowed" };
        }
        return { valid: true };
    };

    const emailInput = document.getElementById('email');
    if (emailInput) {
        const checkEmail = async (email) => {
            const { valid, message } = validateEmail(email);
            if (!valid) {
                setError('email', message);
                return;
            }

            try {
                const response = await fetch(`/auth/check-email?email=${encodeURIComponent(email)}`);
                const data = await response.json();
                if (!data.available) {
                    setError('email', data.message || "Email already registered");
                } else {
                    setError('email', "", false);
                }
            } catch (err) {
                console.error("Email check failed", err);
            }
        };

        const debouncedEmailCheck = debounce(checkEmail, 500);
        emailInput.oninput = function () {
            debouncedEmailCheck(this.value);
        };
    }

    const validateName = (name) => {
        const nameRegex = /^[a-zA-Z\s\.\-']{2,60}$/; // Changed min from 3 to 2
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
                    if (p1.length > 3 && p2.length > 3 && getStringSimilarity(p1, p2) > 0.8) {
                        return { valid: false, message: "Names appear repetitive or contain typos" };
                    }
                }
            }
        }

        return { valid: true };
    };

    const validateAddressStr = (addr) => {
        const addrRegex = /^[a-zA-Z0-9\s\.\,\#\-\(\)\/\@]{10,500}$/;
        if (!addr.trim()) return { valid: false, message: "Required" };
        if (addr.length < 10) return { valid: false, message: "Detailed address required (min 10 chars)" };

        const cleanAddr = addr.replace(/[\s\.\,\#\-\(\)\/\@]/g, '');
        
        // Relaxed checks for addresses - removed keyboard walks and number requirements
        if (!addr.trim().includes(' ')) return { valid: false, message: "Address must contain spaces" };
        if (!addrRegex.test(addr)) return { valid: false, message: "Invalid characters in address" };
        if (/(.)\1\1/.test(addr)) return { valid: false, message: "No repeating characters" };

        return { valid: true };
    };

    const nameInput = document.getElementById('full_name');
    if (nameInput) {
        nameInput.oninput = function () {
            const { valid, message } = validateName(this.value);
            if (!valid) {
                setError('name', message);
            } else {
                setError('name', "", false);
            }
        };
    }

    const addressInput = document.getElementById('address');
    if (addressInput) {
        addressInput.oninput = function () {
            const { valid, message } = validateAddressStr(this.value);
            if (!valid) {
                setError('address', message);
            } else {
                setError('address', "", false);
            }
        };
    }

    const regForm = document.getElementById('regForm') || document.querySelector('form[action="/auth/register"]');
    if (regForm) {
        regForm.onsubmit = async function (e) {
            e.preventDefault();
            const fullNameEl = regForm.querySelector('input[name="full_name"]');
            const emailEl = regForm.querySelector('input[name="email"]');
            const passEl = regForm.querySelector('input[name="password"]');
            const confirmEl = regForm.querySelector('input[name="confirm_password"]');
            const mobileEl = regForm.querySelector('input[name="mobile_number"]');

            const pass = passEl ? passEl.value : "social_login_auto";
            const confirm = confirmEl ? confirmEl.value : "social_login_auto";
            const mobile = mobileEl ? mobileEl.value.replace(/\s/g, '') : "";

            const emailRegex = /^[a-zA-Z0-9._%+-]+@gmail\.com$/;
            const mobileRegex = /^(09|\+639)\d{9}$/;
            let hasError = false;

            if (pass !== "social_login_auto") {
                if (pass.length < 8) {
                    setError('password', "At least 8 characters");
                    hasError = true;
                } else if (!/[A-Z]/.test(pass)) {
                    setError('password', "Must have uppercase letter");
                    hasError = true;
                } else if (!/[a-z]/.test(pass)) {
                    setError('password', "Must have lowercase letter");
                    hasError = true;
                } else if (!/[0-9]/.test(pass)) {
                    setError('password', "Must have a number");
                    hasError = true;
                } else if (!/[!@#$%^&*(),.?":{}|<>]/.test(pass)) {
                    setError('password', "Must have special character");
                    hasError = true;
                }
            }
            
            if (pass !== "social_login_auto" && pass !== confirm) {
                setError('confirm', "Passwords do not match");
                hasError = true;
            } else if (mobile && (!mobileRegex.test(mobile) || /(.)\1\1/.test(mobile))) {
                const repetitiveRegex = /(.)\1\1/;
                if (repetitiveRegex.test(mobile)) {
                    setError('mobile', "Repetitive digits not allowed (e.g. 111)");
                } else {
                    setError('mobile', "Invalid number format (11 digits required)");
                }
                hasError = true;
            }

            const errorWrappers = document.querySelectorAll('.input-wrapper.error');
            if (errorWrappers.length > 0) {
                hasError = true;
            }

            if (hasError) {
                return false;
            }

            const fullName = fullNameEl?.value || "";
            const nameParts = fullName.trim().split(/\s+/);
            const firstName = nameParts[0] || "";
            const lastName = nameParts.length > 1 ? nameParts.slice(1).join(" ") : ".";

            const formData = new FormData(regForm);
            formData.set('first_name', firstName);
            formData.set('last_name', lastName);

            const submitBtn = regForm.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';

            try {
                const response = await fetch('/auth/register', {
                    method: 'POST',
                    body: formData
                });

                if (response.redirected) {
                    const isVerify = response.url.includes('/auth/verify');
                    if (isVerify) {
                        const emailInputVal = emailEl ? emailEl.value : "";
                        const emailDisplay = document.getElementById('email-display');
                        const emailHidden = document.getElementById('emailField');
                        
                        if (emailDisplay) emailDisplay.innerText = emailInputVal;
                        if (emailHidden) emailHidden.value = emailInputVal;
                        
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalBtnText;

                        if (typeof window.openAuthModal === 'function' && document.getElementById('authModalOverlay')) {
                            window.openAuthModal('verify');
                            if (typeof window.initVerifyPolling === 'function') {
                                window.initVerifyPolling();
                            }
                            if (typeof window.startTimer === 'function') {
                                window.startTimer();
                            }
                        } else {
                            window.location.href = response.url;
                        }
                    } else {
                        if (window.Swal) {
                            await Swal.fire({
                                icon: 'success',
                                title: 'Registration Successful!',
                                text: 'Your account has been created. Redirecting...',
                                timer: 3000,
                                showConfirmButton: false,
                                confirmButtonColor: '#FF7B54'
                            });
                        }
                        window.location.href = response.url;
                    }
                } else {
                    const contentType = response.headers.get("content-type");
                    if (contentType && contentType.indexOf("application/json") !== -1) {
                        const result = await response.json();
                        if (response.ok) {
                            if (window.Swal) {
                                await Swal.fire({
                                    icon: 'success',
                                    title: 'Success!',
                                    text: 'Registration successful.',
                                    timer: 1500,
                                    showConfirmButton: false
                                });
                            }
                            window.location.href = result.redirect || "/customer/dashboard";
                        } else {
                            submitBtn.disabled = false;
                            submitBtn.innerHTML = originalBtnText;
                            if (window.Swal) {
                                Swal.fire({
                                    icon: 'error',
                                    title: 'Registration Failed',
                                    text: result.message || "Please check your information and try again.",
                                    confirmButtonColor: '#FF7B54'
                                });
                            } else {
                                alert(result.message || "Registration failed.");
                            }
                        }
                    } else {
                        // Backend likely returned TemplateResponse for validation errors
                        // We must NOT reload as it clears the POST result.
                        // Instead, we let the form submit naturally to show the backend template.
                        regForm.onsubmit = null; 
                        regForm.submit();
                    }
                }
            } catch (error) {
                console.error('Error during registration:', error);
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
                if (window.Swal) {
                    Swal.fire({
                        icon: 'error',
                        title: 'Unexpected Error',
                        text: 'A connection error occurred. Please try again.',
                        confirmButtonColor: '#FF7B54'
                    });
                } else {
                    alert("An unexpected error occurred. Please try again later.");
                }
            }
        };
    }
})();
