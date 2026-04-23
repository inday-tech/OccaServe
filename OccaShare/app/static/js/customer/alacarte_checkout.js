document.addEventListener('DOMContentLoaded', function () {
    const itemPrice = window.itemPrice || 0;
    const catererId = window.catererId;
    const menuId = window.menuId;

    let deliveryFee = 150; 
    let currentScreen = 1;

    // --- DELIVERY FEE MAPPING (Sta. Cruz, Marinduque) ---
    const BRGY_FEES = {
        // Near / Town Proper (₱50)
        "Napo": 50, "Pag-asa": 50, "Morales": 50, "Maharlika": 50, "San Antonio": 50,
        "San Isidro": 50, "San Juan": 50, "San Pedro": 50, "San Roque": 50,
        
        // Mid-Distance (₱100 - ₱150)
        "Alobo": 100, "Aturan": 120, "Balogo": 100, "Banahaw": 120, "Hupi": 130, 
        "Ipil": 120, "Lamesa": 150, "Landy": 100, "Matalaba": 150, "Tawiran": 100, "Taytay": 150,
        
        // Far / Remote (₱200 - ₱300)
        "Angas": 200, "Baliis": 250, "Bangcuangan": 200, "Binuangan": 250, "Bocboc": 300,
        "Botilao": 300, "Buyaba": 250, "Caigangan": 200, "Daykitin": 250, "Devilla": 300,
        "Haguimit": 250, "Jolo": 300, "Kilo-kilo": 300, "Makawayan": 300, "Masaguisi": 300,
        "Masalukot": 300, "Tambangan": 250,
        
        // Islands (Special Rate)
        "Maniwaya": 500, "Mongpong": 500, "Polo": 350
    };

    const DEFAULT_FEE = 150;
    
    // RECOVER SESSION: Use a more robust check
    const sessionKey = `alc_draft_${window.catererId}_${window.menuId}`;
    let bookingId = sessionStorage.getItem(sessionKey); 
    
    // Function to ensure we always have the latest ID
    function getActiveBookingId() {
        if (!bookingId) {
            bookingId = sessionStorage.getItem(sessionKey);
        }
        return bookingId;
    }

    if (bookingId) {
        console.log("[CHECKOUT] Found existing session:", bookingId);
    }

    // Webcam Variables
    let videoStream = null;
    let idFile = null;
    let selfieFrames = [];
    let isMobile = () => /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

    // --- SETUP DATE MIN ---
    const dateInput = document.getElementById('delivery_date');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.setAttribute('min', today);
    }

    // --- NAVIGATION LOGIC ---
    window.nextScreen = async function (n, force = false) {
        if (!force && n > currentScreen) {
            if (!validateScreen(currentScreen)) return;
            
            // Create Draft Booking when moving from Step 1 to Step 2
            if (currentScreen === 1 && n === 2) {
                const ok = await createDraftBooking();
                if (!ok) return;
            }
        }

        // Hide all screens, show target
        document.querySelectorAll('.checkout-screen').forEach(s => s.classList.remove('active'));
        const target = document.getElementById(`screen-${n}`);
        if (target) target.classList.add('active');

        // Update Stepper
        updateStepper(n);
        currentScreen = n;

        if (n === 2) populateReview();

        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    function updateStepper(n) {
        document.querySelectorAll('.mini-step').forEach((step, idx) => {
            const stepNum = idx + 1;
            if (stepNum < n) {
                step.classList.add('completed');
                step.classList.remove('active');
            } else if (stepNum === n) {
                step.classList.add('active');
                step.classList.remove('completed');
            } else {
                step.classList.remove('active', 'completed');
            }
        });
    }

    // --- FORM VALIDATION ---
    function validateScreen(n) {
        let isValid = true;
        document.querySelectorAll('.field-error').forEach(el => el.classList.remove('show'));
        document.querySelectorAll('.form-input').forEach(el => el.classList.remove('error'));

        if (n === 1) {
            const fulfillment = document.querySelector('input[name="fulfillment"]:checked').value;
            const required = ['full_name', 'contact_number', 'delivery_date', 'delivery_time'];
            
            if (fulfillment === 'delivery') {
                const brgy = document.getElementById('brgy_select');
                if (!brgy.value) {
                    showError('brgy_select', 'err-brgy_select');
                    isValid = false;
                }
            }

            required.forEach(id => {
                const el = document.getElementById(id);
                if (el && !el.value.trim()) {
                    showError(id, `err-${id}`);
                    isValid = false;
                }
            });
            
            const phone = document.getElementById('contact_number').value.replace(/\D/g, '');
            if (phone.length !== 11 && phone.length > 0) {
                showError('contact_number', 'err-contact_number');
                isValid = false;
            }
        }

        return isValid;
    }

    function showError(inputId, errId) {
        const input = document.getElementById(inputId);
        const err = document.getElementById(errId);
        if (input) input.classList.add('error');
        if (err) err.classList.add('show');
    }

    // --- DRAFT CREATION ---
    async function createDraftBooking() {
        const form = document.getElementById('checkoutForm');
        const formData = new FormData(form);
        formData.append('caterer_id', catererId);
        formData.append('menu_id', menuId);
        formData.append('is_draft', 'true');
        formData.append('total_amount', calculateTotal());

        try {
            const btn = document.querySelector('#screen-1 .btn-wizard-next');
            btn.innerHTML = 'Securing Details... <i class="fas fa-spinner fa-spin"></i>';
            btn.disabled = true;

            const res = await fetch('/bookings/alacarte/checkout/draft', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            
            if (data.success) {
                bookingId = data.booking_id;
                sessionStorage.setItem(sessionKey, bookingId); // Persist ID
                console.log("[CHECKOUT] Draft created/updated:", bookingId);
                return true;
            } else {
                alert("Error creating booking: " + data.message);
                return false;
            }
        } catch (e) {
            console.error(e);
            alert("Connection error occurred.");
            return false;
        } finally {
            const btn = document.querySelector('#screen-1 .btn-wizard-next');
            btn.innerHTML = 'Next Step: Payment <i class="fas fa-chevron-right"></i>';
            btn.disabled = false;
        }
    }

    // --- SUMMARY & FULFILLMENT ---
    window.updateCheckoutSummary = function() {
        const qty = parseInt(document.getElementById('quantity_input').value) || 1;
        const base = itemPrice * qty;
        const total = base + deliveryFee;
        
        document.getElementById('sum-base-price').innerText = '₱' + base.toLocaleString(undefined, { minimumFractionDigits: 2 });
        document.getElementById('sum-qty').innerText = 'x' + qty;
        document.getElementById('sum-delivery-fee').innerText = '₱' + deliveryFee.toLocaleString(undefined, { minimumFractionDigits: 2 });
        document.getElementById('sum-grand-total').innerText = '₱' + total.toLocaleString(undefined, { minimumFractionDigits: 2 });
    };

    window.updateFulfillment = function(el) {
        const selector = el.closest('.fulfillment-selector');
        const opts = selector.querySelectorAll('.fulfillment-opt');
        opts.forEach(o => o.classList.remove('active'));
        el.parentElement.classList.add('active');
        
        const addressSection = document.getElementById('address-section');
        const brgy = document.getElementById('brgy_select').value;

        if (el.value === 'pickup') {
            deliveryFee = 0;
            document.getElementById('delivery-row').style.display = 'none';
            if (addressSection) addressSection.classList.add('hidden-address');
        } else {
            // Restore dynamic fee or default
            deliveryFee = BRGY_FEES[brgy] || DEFAULT_FEE;
            document.getElementById('delivery-row').style.display = 'flex';
            if (addressSection) addressSection.classList.remove('hidden-address');
        }
        updateCheckoutSummary();
    };

    // Initial call to sync UI
    const defaultFulfillment = document.querySelector('input[name="fulfillment"]:checked');
    if (defaultFulfillment) window.updateFulfillment(defaultFulfillment);

    function calculateTotal() {
        return parseFloat(document.getElementById('sum-grand-total').innerText.replace(/[^\d.-]/g, ''));
    }

    function populateReview() {
        const form = document.getElementById('checkoutForm');
        document.getElementById('rev-name').innerText = form.full_name.value;
        document.getElementById('rev-phone').innerText = form.contact_number.value;
        document.getElementById('rev-datetime').innerText = `${form.delivery_date.value} @ ${form.delivery_time.value}`;
        
        const mode = form.fulfillment.value;
        document.getElementById('rev-location').innerText = mode === 'pickup' ? 'STORE PICKUP' : document.getElementById('address').value;
    }

    // --- ADDRESS SYNC & DYNAMIC FEE ---
    window.syncAddress = function() {
        const brgy = document.getElementById('brgy_select').value;
        const street = document.getElementById('street_input').value;
        const hiddenInput = document.getElementById('address');
        
        const fulfillment = document.querySelector('input[name="fulfillment"]:checked').value;

        if (brgy) {
            hiddenInput.value = `${street ? street + ', ' : ''}Brgy. ${brgy}, Sta. Cruz, Marinduque`;
            
            // Update Delivery Fee based on distance
            if (fulfillment === 'delivery') {
                deliveryFee = BRGY_FEES[brgy] || DEFAULT_FEE;
            }
        } else {
            hiddenInput.value = "";
            if (fulfillment === 'delivery') deliveryFee = DEFAULT_FEE;
        }
        updateCheckoutSummary();
    };

    // --- PAYMENT SELECTION ---
    window.selectPayment = function(method, el) {
        document.getElementById('payment_method').value = method;
        document.querySelectorAll('.payment-opt').forEach(opt => opt.classList.remove('active'));
        el.classList.add('active');
        console.log("[CHECKOUT] Payment Method Selected:", method);
    };

    // --- FINAL SUBMIT ---
    window.submitAtaCarteOrder = async function() {
        // Fallback recovery
        const currentId = getActiveBookingId();
        
        if (!currentId) {
            alert("Session lost. Please try going back to the first step to re-save your details.");
            console.error("[CHECKOUT] Submission failed: No bookingId found.");
            return;
        }

        const btn = document.getElementById('final-submit-btn');
        const loader = document.getElementById('place-order-loading');
        btn.disabled = true;
        loader.style.display = 'block';

        const form = document.getElementById('checkoutForm');
        const formData = new FormData(form);
        formData.append('booking_id', currentId);
        formData.append('caterer_id', catererId);
        formData.append('menu_id', menuId);
        formData.append('total_amount', calculateTotal());
        
        try {
            const res = await fetch('/bookings/alacarte/checkout/submit', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.success) {
                sessionStorage.removeItem(sessionKey); // Clear session on success
                nextScreen(3, true);
            } else {
                const errMsg = data.message || (data.detail ? JSON.stringify(data.detail) : "Unknown Error");
                alert("Order Error: " + errMsg);
                btn.disabled = false;
                loader.style.display = 'none';
            }
        } catch (e) {
            alert("Network error.");
            btn.disabled = false;
            loader.style.display = 'none';
        }
    };
});
