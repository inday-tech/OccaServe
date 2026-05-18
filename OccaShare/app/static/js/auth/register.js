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

    // Real-time validations are centralized globally in diamond_validation.js

    const regForm = document.getElementById('regForm') || document.querySelector('form[action="/auth/register"]');
    if (regForm) {
        regForm.onsubmit = async function (e) {
            e.preventDefault();
            
            const firstNameEl = regForm.querySelector('input[name="first_name"]');
            const middleNameEl = regForm.querySelector('input[name="middle_name"]');
            const lastNameEl = regForm.querySelector('input[name="last_name"]');
            const emailEl = regForm.querySelector('input[name="email"]');
            const passEl = regForm.querySelector('input[name="password"]');
            const confirmEl = regForm.querySelector('input[name="confirm_password"]');
            const mobileEl = regForm.querySelector('input[name="mobile_number"]');
            const provEl = regForm.querySelector('#province_cust');
            const cityEl = regForm.querySelector('#city_cust');
            const brgyEl = regForm.querySelector('#barangay_cust');
            const streetEl = regForm.querySelector('#street_cust');

            // Force all fields to mark as touched and validate
            [firstNameEl, middleNameEl, lastNameEl, emailEl, passEl, confirmEl, mobileEl, provEl, cityEl, brgyEl, streetEl].forEach(input => {
                if (input) {
                    input.classList.add('touched');
                    input.dispatchEvent(new Event('input', { bubbles: true }));

                    // If required select/input is empty, flag unified error drawer
                    if (input.hasAttribute('required') && (!input.value || input.value.trim() === '')) {
                        let prefix = input.id;
                        if (input.id === 'first_name') prefix = 'firstName';
                        else if (input.id === 'middle_name') prefix = 'middleName';
                        else if (input.id === 'last_name') prefix = 'lastName';
                        else if (input.id === 'province_cust') prefix = 'provinceCust';
                        else if (input.id === 'city_cust') prefix = 'cityCust';
                        else if (input.id === 'barangay_cust') prefix = 'barangayCust';
                        else if (input.id === 'street_cust') prefix = 'streetCust';
                        
                        if (typeof window.setDiamondError === 'function') {
                            window.setDiamondError(prefix, "Required");
                        }
                    }
                }
            });

            // Perform synchronous uniqueness checks to prevent timing race conditions
            if (emailEl && emailEl.value && !regForm.querySelector('#emailWrapper.error')) {
                try {
                    const res = await fetch(`/auth/check-email?email=${encodeURIComponent(emailEl.value)}`);
                    const data = await res.json();
                    if (!data.available) {
                        window.setDiamondError('email', data.message || "Email already taken");
                    }
                } catch (err) { console.error(err); }
            }

            if (mobileEl && mobileEl.value && !regForm.querySelector('#mobileWrapper.error')) {
                const val = mobileEl.value.replace(/\s/g, '');
                try {
                    const res = await fetch(`/auth/check-phone?phone=${encodeURIComponent(val)}`);
                    const data = await res.json();
                    if (!data.available) {
                        window.setDiamondError('mobile', data.message || "This number is already registered.");
                    }
                } catch (err) { console.error(err); }
            }

            // Check if there are any error wrappers currently active
            const errorWrappers = regForm.querySelectorAll('.input-wrapper.error');
            if (errorWrappers.length > 0) {
                // Focus on the first error field
                errorWrappers[0].querySelector('input, select')?.focus();
                return false;
            }

            const firstName = firstNameEl ? firstNameEl.value.trim() : "";
            const middleName = middleNameEl ? middleNameEl.value.trim() : "";
            const lastName = lastNameEl ? lastNameEl.value.trim() : "";
            const fullName = `${firstName} ${middleName ? middleName + ' ' : ''}${lastName}`.trim();

            const formData = new FormData(regForm);
            formData.set('first_name', firstName);
            formData.set('middle_name', middleName);
            formData.set('last_name', lastName);
            formData.set('full_name', fullName);

            const submitBtn = regForm.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.style.opacity = '0.7';
            submitBtn.style.cursor = 'wait';
            submitBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> <span>Creating Secure Account...</span>';

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
        // Clear address errors on change/input
        ['province_cust', 'city_cust', 'barangay_cust'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('change', function() {
                    const prefix = id === 'province_cust' ? 'provinceCust' : (id === 'city_cust' ? 'cityCust' : 'barangayCust');
                    if (this.value) {
                        window.setDiamondError(prefix, "", false);
                    }
                });
            }
        });
        const streetEl = document.getElementById('street_cust');
        if (streetEl) {
            streetEl.addEventListener('input', function() {
                if (this.value.trim()) {
                    window.setDiamondError('streetCust', "", false);
                }
            });
        }
        };
    }
})();
