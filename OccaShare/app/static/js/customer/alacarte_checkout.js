document.addEventListener('DOMContentLoaded', function () {
    const itemPrice = window.itemPrice || 0;
    const catererId = window.catererId;
    const menuId = window.menuId;

    let deliveryFee = 150; 
    window.currentScreen = 1;

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

    // --- COMBO BUILDER LOGIC ---
    window.handleComboSelection = function(checkbox) {
        const grid = checkbox.closest('.combo-options-grid');
        const limit = parseInt(grid.dataset.limit) || 0;
        const itemId = grid.dataset.id;
        
        const checked = grid.querySelectorAll('.combo-checkbox:checked');
        const count = checked.length;
        
        const counterEl = document.getElementById(`counter-combo-${itemId}`);
        if (counterEl) {
            counterEl.innerText = `${count} / ${limit} Selected`;
            if (count === limit) {
                counterEl.style.background = '#dcfce7';
                counterEl.style.color = '#166534';
            } else {
                counterEl.style.background = '#ccfbf1';
                counterEl.style.color = '#0f766e';
            }
        }
        
        const allBoxes = grid.querySelectorAll('.combo-checkbox');
        if (count >= limit) {
            allBoxes.forEach(cb => {
                if (!cb.checked) cb.disabled = true;
            });
        } else {
            allBoxes.forEach(cb => cb.disabled = false);
        }
    };

    // LOAD CART
    let parsedCart = [];
    try {
        parsedCart = JSON.parse(sessionStorage.getItem('alacarte_cart_' + window.catererId));
        if (!Array.isArray(parsedCart)) parsedCart = [];
    } catch (e) {
        parsedCart = [];
    }
    window.cartItems = parsedCart;
    
    // Fallback if cartItems is empty but backendMenuItems has items (e.g., direct navigation)
    if (window.cartItems.length === 0 && window.backendMenuItems) {
        window.backendMenuItems.forEach(item => {
            window.cartItems.push({ id: String(item.id), name: item.name, price: item.price, qty: 1 });
        });
    }

    function applyDynamicTerminology() {
        const hasFood = window.cartItems.some(cItem => {
            const backendList = window.backendMenuItems || [];
            const bItem = backendList.find(i => String(i.id) === String(cItem.id)) || cItem;
            return !bItem.is_rental;
        });

        // If it's pure rentals (no food), change the wordings
        const isRentalOnly = !hasFood && window.cartItems.length > 0;

        const lblDelDate = document.getElementById('lbl_delivery_date');
        if (lblDelDate) lblDelDate.innerText = isRentalOnly ? 'Delivery & Setup Date' : 'Delivery Date';
        
        const lblDelTime = document.getElementById('lbl_delivery_time');
        if (lblDelTime) lblDelTime.innerText = isRentalOnly ? 'Setup Time' : 'Delivery Time';

        const lblFulfillDel = document.getElementById('lbl_fulfill_del');
        if (lblFulfillDel) lblFulfillDel.innerText = isRentalOnly ? 'Delivery & Setup' : 'Delivery';

        const lblFulfillPick = document.getElementById('lbl_fulfill_pick');
        if (lblFulfillPick) lblFulfillPick.innerText = isRentalOnly ? 'Self-Collect' : 'Pickup';

        const subtitle1 = document.getElementById('subtitle_step1');
        if (subtitle1) subtitle1.innerText = isRentalOnly ? 'Please tell us how you want to receive your equipment.' : 'Please tell us how you want to receive your order.';

        const subtitle3 = document.getElementById('subtitle_step3');
        if (subtitle3) subtitle3.innerText = isRentalOnly ? 'Your equipment request has been sent to' : 'Your food order has been sent to';
        
        const btnSubmit = document.getElementById('final-submit-btn');
        if (btnSubmit) btnSubmit.innerHTML = isRentalOnly ? 'CONFIRM RENTAL <i class="fas fa-check" style="margin-left: 0.75rem;"></i>' : 'PLACE ORDER NOW <i class="fas fa-check" style="margin-left: 0.75rem;"></i>';
    }

    // MAP items
    window.renderBillItems = function() {
        applyDynamicTerminology();
        const container = document.getElementById('dynamic-bill-items');
        if (!container) return;
        
        let html = '';
        let baseTotal = 0;

        window.cartItems.forEach((cItem, index) => {
            const backendList = window.backendMenuItems || [];
            const bItem = backendList.find(i => String(i.id) === String(cItem.id)) || cItem;
            const price = parseFloat(cItem.price || bItem.price) || 0;
            const qty = parseInt(cItem.qty) || 1;
            const isRental = bItem.is_rental;
            const unitLabel = isRental ? '/ Unit' : (bItem.is_combo ? '(Platter)' : '/ Tray');
            
            baseTotal += (price * qty);

            html += `
                <div class="bill-item-wrap" style="align-items: start;">
                    <div class="bill-item-thumb">
                         <img src="${bItem.image_url || '/static/images/placeholder_dish.jpg'}" alt="${bItem.name}">
                    </div>
                    <div class="bill-item-info" style="flex: 1;">
                        <h4>${bItem.name}</h4>
                        <p style="margin-bottom: 0.5rem;">₱${price.toLocaleString(undefined, { minimumFractionDigits: 0 })} ${unitLabel}</p>
                        
                        <div style="display: flex; align-items: center; gap: 0.5rem; background: #f1f5f9; width: fit-content; border-radius: 6px; padding: 2px;">
                            <button type="button" onclick="updateItemQty(${index}, -1)" style="border: none; background: white; width: 24px; height: 24px; border-radius: 4px; cursor: pointer; color: #64748b; font-weight: bold;">-</button>
                            <span style="font-size: 0.8rem; font-weight: 800; width: 20px; text-align: center;">${qty}</span>
                            <button type="button" onclick="updateItemQty(${index}, 1)" style="border: none; background: white; width: 24px; height: 24px; border-radius: 4px; cursor: pointer; color: #64748b; font-weight: bold;">+</button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
        window.updateCheckoutSummary(baseTotal);
    };

    window.updateItemQty = function(index, delta) {
        let newQty = (parseInt(window.cartItems[index].qty) || 1) + delta;
        if (newQty < 1) newQty = 1;
        if (newQty > 99) {
            Swal.fire({icon: 'info', title: 'Limit Reached', text: 'Maximum quantity limit reached.', confirmButtonColor: '#10b981'});
            return;
        }
        window.cartItems[index].qty = newQty;
        sessionStorage.setItem('alacarte_cart_' + window.catererId, JSON.stringify(window.cartItems));
        window.renderBillItems();
    };

    function buildCartData() {
        const cart = [];
        window.cartItems.forEach(cItem => {
            const id = cItem.id;
            const qty = cItem.qty;
            const choices = [];
            const grid = document.querySelector(`.combo-options-grid[data-id="${id}"]`);
            if (grid) {
                grid.querySelectorAll('.combo-checkbox:checked').forEach(cb => {
                    choices.push(cb.value);
                });
            }
            cart.push({
                id: id,
                quantity: qty,
                choices: choices
            });
        });
        return JSON.stringify(cart);
    }

    // --- NAVIGATION LOGIC ---
    window.nextScreen = async function (n, force = false) {
        if (!force && n > window.currentScreen) {
            if (!validateScreen(window.currentScreen)) return;
            
            // Create Draft Booking when moving from Step 1 to Step 2
            if (window.currentScreen === 1 && n === 2) {
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
        window.currentScreen = n;

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
            if ((phone.length !== 11 || !phone.startsWith('09')) && phone.length > 0) {
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

    function clearError(inputId, errId) {
        const input = document.getElementById(inputId);
        const err = document.getElementById(errId);
        if (input) input.classList.remove('error');
        if (err) err.classList.remove('show');
    }

    function bindRealTimeValidation() {
        const required = ['full_name', 'delivery_date', 'delivery_time'];
        
        required.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('input', function() {
                    if (!this.value.trim()) {
                        showError(id, `err-${id}`);
                    } else {
                        clearError(id, `err-${id}`);
                    }
                });
            }
        });

        const phone = document.getElementById('contact_number');
        if (phone) {
            phone.addEventListener('input', function() {
                const val = this.value.replace(/\D/g, '');
                if (val.length === 0 || val.length !== 11 || !val.startsWith('09')) {
                    showError('contact_number', 'err-contact_number');
                } else {
                    clearError('contact_number', 'err-contact_number');
                }
            });
        }

        const brgy = document.getElementById('brgy_select');
        if (brgy) {
            brgy.addEventListener('change', function() {
                const fulfillment = document.querySelector('input[name="fulfillment"]:checked').value;
                if (fulfillment === 'delivery' && !this.value) {
                    showError('brgy_select', 'err-brgy_select');
                } else {
                    clearError('brgy_select', 'err-brgy_select');
                }
            });
        }
    }

    function bindDatePicker() {
        const dateInput = document.getElementById('delivery_date');
        if (!dateInput) return;
        
        const leadTime = window.bookingLeadTime || 7;
        const today = new Date();
        today.setDate(today.getDate() + leadTime);
        
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const dd = String(today.getDate()).padStart(2, '0');
        
        const minDate = `${yyyy}-${mm}-${dd}`;
        dateInput.setAttribute('min', minDate);
        
        dateInput.addEventListener('change', function() {
            if (this.value && this.value < minDate) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Invalid Date',
                    text: `Based on the caterer's policy, bookings must be made at least ${leadTime} days in advance (earliest is ${minDate}).`,
                    confirmButtonColor: '#10b981'
                });
                this.value = ''; // Reset invalid selection
                showError('delivery_date', 'err-delivery_date');
            } else if (this.value) {
                clearError('delivery_date', 'err-delivery_date');
            }
        });
    }

    function validateCombos() {
        let valid = true;
        document.querySelectorAll('.combo-options-grid').forEach(grid => {
            const limit = parseInt(grid.dataset.limit) || 0;
            const itemId = grid.dataset.id;
            const count = grid.querySelectorAll('.combo-checkbox:checked').length;
            if (count !== limit && limit > 0) {
                valid = false;
                const counterEl = document.getElementById(`counter-combo-${itemId}`);
                if (counterEl) {
                    counterEl.style.background = '#fee2e2';
                    counterEl.style.color = '#b91c1c';
                }
            }
        });
        if (!valid) {
            Swal.fire({icon: 'warning', title: 'Incomplete Selection', text: 'Please complete your platter selections.', confirmButtonColor: '#10b981'});
        }
        return valid;
    }

    // --- DRAFT CREATION ---
    async function createDraftBooking() {
        if (!validateCombos()) return false;

        const form = document.getElementById('checkoutForm');
        const formData = new FormData(form);
        formData.append('caterer_id', catererId);
        formData.append('menu_id', menuId);
        formData.append('cart_data', buildCartData());
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
                Swal.fire({icon: 'error', title: 'Booking Failed', text: data.message, confirmButtonColor: '#10b981'});
                return false;
            }
        } catch (e) {
            console.error(e);
            Swal.fire({icon: 'error', title: 'Network Error', text: 'Connection error occurred while saving draft.', confirmButtonColor: '#10b981'});
            return false;
        } finally {
            const btn = document.querySelector('#screen-1 .btn-wizard-next');
            btn.innerHTML = 'Next Step: Payment <i class="fas fa-chevron-right"></i>';
            btn.disabled = false;
        }
    }

    // --- SUMMARY & FULFILLMENT ---
    window.updateCheckoutSummary = function(calculatedBaseTotal = null) {
        let base = calculatedBaseTotal;
        if (base === null) {
            base = 0;
            window.cartItems.forEach(cItem => {
                const price = parseFloat(cItem.price) || 0;
                const qty = parseInt(cItem.qty) || 1;
                base += (price * qty);
            });
        }
        const total = base + deliveryFee;
        
        const sumBaseEl = document.getElementById('sum-base-price');
        if (sumBaseEl) sumBaseEl.innerText = '₱' + base.toLocaleString(undefined, { minimumFractionDigits: 2 });
        
        const feeEl = document.getElementById('sum-delivery-fee');
        if (feeEl) feeEl.innerText = '₱' + deliveryFee.toLocaleString(undefined, { minimumFractionDigits: 2 });
        
        const grandEl = document.getElementById('sum-grand-total');
        if (grandEl) grandEl.innerText = '₱' + total.toLocaleString(undefined, { minimumFractionDigits: 2 });
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

    // Render dynamic items on load
    window.renderBillItems();

    // Bind real-time validation listeners
    bindRealTimeValidation();
    bindDatePicker();

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
        // Terms & Conditions Validation
        const termsCheckbox = document.getElementById('alacarteTermsAgreement');
        if (termsCheckbox && !termsCheckbox.checked) {
            Swal.fire({
                title: 'Action Required',
                text: 'You must agree to the caterer\'s Terms & Conditions before placing your order.',
                icon: 'warning',
                confirmButtonColor: 'var(--up-emerald-500)'
            });
            return;
        }

        // Fallback recovery
        const currentId = getActiveBookingId();
        
        if (!currentId) {
            Swal.fire({icon: 'error', title: 'Session Lost', text: 'Please try going back to the first step to re-save your details.', confirmButtonColor: '#10b981'});
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
        formData.append('cart_data', buildCartData());
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
                Swal.fire({icon: 'error', title: 'Checkout Failed', text: errMsg, confirmButtonColor: '#10b981'});
                btn.disabled = false;
                loader.style.display = 'none';
            }
        } catch (e) {
            Swal.fire({icon: 'error', title: 'Network Error', text: 'A network error occurred.', confirmButtonColor: '#10b981'});
            btn.disabled = false;
            loader.style.display = 'none';
        }
    };
});
