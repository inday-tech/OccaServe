/**
 * DIAMOND STANDARD CATERER AUTH LOGIC
 * Handles multi-step navigation and geographic data site-wide.
 */

(function () {
    let currentStepCat = 1;
    const totalStepsCat = 4;

    const LAGUNA_DATA = {
        "Santa Cruz": [
            "Alipit", "Bagumbayan", "Bubukal", "Calios", "Duhat", 
            "Gatid", "Jasaan", "Labuin", "Malinao", "Oogong", 
            "Pagsawitan", "Palasan", "Patimbao", "Poblacion I", 
            "Poblacion II", "Poblacion III", "Poblacion IV", 
            "Poblacion V", "San Jose", "San Juan", "San Pablo Norte", 
            "San Pablo Sur", "Santisima Cruz", "Santo Angel Central", 
            "Santo Angel Norte", "Santo Angel Sur"
        ]
    };

    window.changeStepCat = function(n) {
        const form = document.getElementById('catererForm');
        if (!form) return;
        const steps = form.querySelectorAll('.form-step');
        const pSteps = document.querySelectorAll('.progress-step');
        
        // Progress to next step only if current is valid
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
        if (prevBtn) prevBtn.style.display = currentStepCat === 1 ? 'none' : 'block';
        
        if (nextBtn) {
            const btnText = nextBtn.querySelector('span') || nextBtn;
            if (btnText === nextBtn) {
                 nextBtn.innerText = currentStepCat === totalStepsCat ? 'Complete Registration' : 'Next Step';
            } else {
                 btnText.innerText = currentStepCat === totalStepsCat ? 'Complete Registration' : 'Next Step';
            }
        }
    };

    function validateCurrentStepCat() {
        const step = document.getElementById(`step-${currentStepCat}`);
        if (!step) return true;
        
        // Use Diamond Validation if available
        const inputs = step.querySelectorAll('input[required], select[required]');
        let valid = true;
        
        inputs.forEach(input => {
            // Check if it's an email or password, let its own validator handle it
            const prefix = input.id.replace('_cat', '').replace('_cat', 'Cat'); // Rough prefix mapping
            
            if (!input.value.trim()) {
                valid = false;
                if (window.setDiamondError) {
                    // Try to find if it has a wrapper or just use basic red border
                    const wrapper = document.getElementById(input.id + 'Wrapper') || document.getElementById(prefix + 'Wrapper');
                    if (wrapper) window.setDiamondError(prefix, "Required");
                    else input.style.borderColor = '#ef4444';
                } else {
                    input.style.borderColor = '#ef4444';
                }
            } else {
                // Check for errors already set by diamond_validation.js
                const wrapper = document.getElementById(input.id + 'Wrapper') || document.getElementById(prefix + 'Wrapper');
                if (wrapper && wrapper.classList.contains('error')) {
                    valid = false;
                } else {
                    input.style.borderColor = '';
                }
            }
        });
        return valid;
    }

    async function submitCatererForm() {
        const form = document.getElementById('catererForm');
        if (!form) return;
        const formData = new FormData(form);
        const submitBtn = document.getElementById('nextBtnCat');
        
        if (submitBtn) submitBtn.disabled = true;
        const originalText = submitBtn.innerHTML;
        submitBtn.innerText = 'Creating Account...';

        try {
            updateAddressCat();

            // Sanitize numeric fields (remove commas)
            const numericFields = ['min_pax', 'starting_price', 'years_of_operation'];
            numericFields.forEach(f => {
                const val = formData.get(f);
                if (val) formData.set(f, val.replace(/,/g, ''));
            });

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
                } else {
                    window.location.href = response.url;
                }
            } else {
                const result = await response.json();
                if (window.Swal) {
                    Swal.fire({ icon: 'error', title: 'Registration Failed', text: result.message || 'Please check your information.' });
                }
            }
        } catch (error) {
            console.error('Registration error:', error);
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        }
    }

    function updateAddressCat() {
        const prov = document.getElementById('province_cat')?.value;
        const city = document.getElementById('city_cat')?.value;
        const brgy = document.getElementById('barangay_cat')?.value;
        const street = document.getElementById('street_cat')?.value;
        const hiddenAddress = document.getElementById('address_cat_hidden');
        if (hiddenAddress && city && brgy) {
            hiddenAddress.value = `${street || ''}, ${brgy}, ${city}, ${prov || 'Laguna'}`;
        }
    }

    window.updateFileNameCat = function(input, targetId) {
        const display = document.getElementById(targetId);
        if (display && input.files && input.files[0]) {
            display.innerText = input.files[0].name;
            display.style.color = 'var(--auth-primary)';
        }
    };

    window.previewLogoCat = function(input) {
        const preview = document.getElementById('logoPreviewCat');
        const icon = document.getElementById('logoDefaultIcon');
        const text = document.getElementById('uploadTextCat');
        
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                if (preview) {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                }
                if (icon) icon.style.display = 'none';
                if (text) text.innerText = 'Logo Selected: ' + input.files[0].name;
            }
            reader.readAsDataURL(input.files[0]);
        }
    };

    window.initCatererGeoDropdowns = function() {
        const citySelect = document.getElementById('city_cat');
        const brgySelect = document.getElementById('barangay_cat');
        
        if (citySelect && brgySelect) {
            // Clear and populate cities
            citySelect.innerHTML = '<option value="">-- City --</option>';
            Object.keys(LAGUNA_DATA).sort().forEach(city => {
                const opt = document.createElement('option');
                opt.value = opt.textContent = city;
                citySelect.appendChild(opt);
            });
            
            citySelect.onchange = () => {
                brgySelect.innerHTML = '<option value="">-- Barangay --</option>';
                const city = citySelect.value;
                if (city && LAGUNA_DATA[city]) {
                    LAGUNA_DATA[city].sort().forEach(b => {
                        const opt = document.createElement('option');
                        opt.value = opt.textContent = b;
                        brgySelect.appendChild(opt);
                    });
                }
            };
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        window.initCatererGeoDropdowns();
    });
})();
