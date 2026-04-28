(function () {
    let currentStepCat = 1;
    const totalStepsCat = 4;

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

    window.changeStepCat = function(n) {
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
        if (prevBtn) prevBtn.style.display = currentStepCat === 1 ? 'none' : 'block';
        
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

        // Strict Name Validation Rule for Presentation
        if (currentStepCat === 1) {
            const fn = document.getElementById('first_name_cat');
            const ln = document.getElementById('last_name_cat');
            if (fn && ln) {
                const firstName = fn.value.trim().toLowerCase();
                const lastName = ln.value.trim().toLowerCase();
                if (firstName && lastName && firstName === lastName) {
                    valid = false;
                    fn.style.borderColor = '#ef4444';
                    ln.style.borderColor = '#ef4444';
                    alert("❌ Mismatch Detected: First Name and Last Name cannot be identical (e.g., Pepito Pepito). Please use your real name.");
                }
            }
        }

        // Security Verification Validation Rule
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

        // Security Check: Ensure no duplicate names
        const fn = document.getElementById('first_name_cat');
        const ln = document.getElementById('last_name_cat');
        if (fn && ln) {
            const firstName = fn.value.trim().toLowerCase();
            const lastName = ln.value.trim().toLowerCase();
            if (firstName && lastName && firstName === lastName) {
                if (submitBtn) submitBtn.disabled = false;
                if (btnText) btnText.innerText = originalText;
                alert("❌ Mismatch Detected: First Name and Last Name cannot be identical (e.g., Pepito Pepito).");
                return false;
            }
        }

        try {
            updateAddressCat();
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

    window.updateFileNameCat = function(input, id) {
        const p = document.getElementById(id);
        if (p && input.files.length > 0) p.innerText = input.files[0].name;
    };

    window.previewLogoCat = function(input) {
        const preview = document.getElementById('logoPreviewCat');
        const icon = document.getElementById('uploadIconCat');
        const text = document.getElementById('uploadTextCat');
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
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
    window.changeStepCat = changeStepCat;
})();
