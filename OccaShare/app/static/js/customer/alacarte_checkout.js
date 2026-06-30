document.addEventListener('DOMContentLoaded', function () {
    const itemPrice = window.itemPrice || 0;
    const catererId = window.catererId;
    const menuId = window.menuId;

    let deliveryFee = 150; 
    window.currentScreen = 1;

    // Delivery Fee logic will be determined by server.
    const DEFAULT_FEE = window.catererBaseDeliveryFee || 150;
    
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
            window.cartItems.push({ id: String(item.id), type: item.type, name: item.name, price: item.price, qty: 1 });
        });
    }

    // Define applyDynamicTerminology before calling it
    function applyDynamicTerminology() {
        const hasFood = window.cartItems.some(cItem => {
            const backendList = window.backendMenuItems || [];
            const bItem = backendList.find(i => String(i.id) === String(cItem.id) && (cItem.type ? i.type === cItem.type : true)) || cItem;
            return bItem && bItem.type === 'Menu';
        });

        const hasRental = window.cartItems.some(cItem => {
            const backendList = window.backendMenuItems || [];
            const bItem = backendList.find(i => String(i.id) === String(cItem.id) && (cItem.type ? i.type === cItem.type : true)) || cItem;
            return bItem && bItem.type === 'Equipment';
        });

        const hasService = window.cartItems.some(cItem => {
            const backendList = window.backendMenuItems || [];
            const bItem = backendList.find(i => String(i.id) === String(cItem.id) && (cItem.type ? i.type === cItem.type : true)) || cItem;
            return bItem && bItem.type === 'Service';
        });

        window.isRentalOnly = hasRental && !hasFood && !hasService;
        window.isServiceOnly = hasService && !hasFood && !hasRental;

        const lblDelDate = document.getElementById('lbl_delivery_date');
        if (lblDelDate) lblDelDate.innerText = window.isServiceOnly ? 'Event Date' : (window.isRentalOnly ? 'Delivery / Setup Date' : 'Delivery Date');
        
        const lblDelTime = document.getElementById('lbl_delivery_time');
        if (lblDelTime) lblDelTime.innerText = window.isServiceOnly ? 'Call Time' : (window.isRentalOnly ? 'Delivery / Setup Time' : 'Delivery Time');

        const lblFulfillDel = document.getElementById('lbl_fulfill_del');
        if (lblFulfillDel) lblFulfillDel.innerText = window.isServiceOnly ? 'On-Site Service' : (window.isRentalOnly ? 'Delivery & Setup' : 'Delivery');

        const lblFulfillPick = document.getElementById('lbl_fulfill_pick');
        if (lblFulfillPick) lblFulfillPick.innerText = window.isRentalOnly ? 'Self-Collect' : 'Pickup';

        const subtitle1 = document.getElementById('subtitle_step1');
        if (subtitle1) subtitle1.innerText = window.isServiceOnly ? 'Please provide the venue address where the service will take place.' : (window.isRentalOnly ? 'Please tell us how you want to receive your equipment.' : 'Please tell us how you want to receive your order.');

        const subtitle3 = document.getElementById('subtitle_step3');
        if (subtitle3) subtitle3.innerText = window.isServiceOnly ? 'Your service request has been sent to' : (window.isRentalOnly ? 'Your equipment request has been sent to' : 'Your food order has been sent to');
        
        const btnSubmit = document.getElementById('final-submit-btn');
        if (btnSubmit) {
            btnSubmit.innerHTML = window.isServiceOnly ? 'CONFIRM BOOKING <i class="fas fa-check" style="margin-left: 0.75rem;"></i>' : 
                                  (window.isRentalOnly ? 'CONFIRM RENTAL <i class="fas fa-check" style="margin-left: 0.75rem;"></i>' : 'PLACE ORDER NOW <i class="fas fa-check" style="margin-left: 0.75rem;"></i>');
        }
    }

    // Call it immediately so variables are ready
    applyDynamicTerminology();

    // applyDynamicTerminology is already defined and called above

    // MAP items
    const UNIT_MAP = {
        'per_serving': '', 'per_tray': ' / Tray', 'per_bilao': ' / Bilao',
        'per_pax': ' / Pax', 'per_hour': ' / Hr', 'per_unit': ' / Unit', 'per_set': ' / Set',
        'per_kg': ' / Kg', 'whole': ' / Whole', 'per_size': ''
    };

    window.renderBillItems = function() {
        const container = document.getElementById('dynamic-bill-items');
        if (!container) return;
        
        let html = '';
        let baseTotal = 0;

        window.cartItems.forEach((cItem, index) => {
            const backendList = window.backendMenuItems || [];
            const bItem = backendList.find(i => String(i.id) === String(cItem.id) && (cItem.type ? i.type === cItem.type : true)) || cItem;
            let itemPrice = parseFloat(cItem.price);
            if (isNaN(itemPrice) || itemPrice === 0) {
                itemPrice = bItem ? parseFloat(bItem.price) || 0 : 0;
            }
            const isFixedQty = ['whole', 'per_event', 'per event', 'package'].includes(String(bItem.pricing_unit).toLowerCase());
            const qty = isFixedQty ? 1 : (parseInt(cItem.qty) || 1);
            const itemName = cItem.name || bItem.name;
            const unitLabel = bItem.pricing_unit ? (UNIT_MAP[bItem.pricing_unit] || ' / ' + bItem.pricing_unit) : (bItem.is_rental ? '/ Unit' : (bItem.is_combo ? '(Platter)' : '/ Tray'));
            
            baseTotal += (itemPrice * qty);

            html += `
                <div class="bill-item-wrap" style="align-items: start;">
                    <div class="bill-item-thumb">
                         <img src="${bItem.image_url || '/static/images/placeholder_dish.jpg'}" alt="${itemName}">
                    </div>
                    <div class="bill-item-info" style="flex: 1;">
                        <h4>${itemName}</h4>
                        <p style="margin-bottom: 0.5rem;">₱${itemPrice.toLocaleString(undefined, { minimumFractionDigits: 0 })} ${unitLabel}</p>
                        
                        ${isFixedQty ? 
                            `<span style="font-size: 0.85rem; font-weight: 700; color: #64748b; background: #f1f5f9; padding: 4px 12px; border-radius: 6px; display: inline-block;">Qty: 1</span>` 
                            : 
                            `<div style="display: flex; align-items: center; gap: 0.5rem; background: #f1f5f9; width: fit-content; border-radius: 6px; padding: 2px;">
                                <button type="button" onclick="updateItemQty(${index}, -1)" style="border: none; background: white; width: 24px; height: 24px; border-radius: 4px; cursor: pointer; color: #64748b; font-weight: bold;">-</button>
                                <span style="font-size: 0.8rem; font-weight: 800; width: 20px; text-align: center;">${qty}</span>
                                <button type="button" onclick="updateItemQty(${index}, 1)" style="border: none; background: white; width: 24px; height: 24px; border-radius: 4px; cursor: pointer; color: #64748b; font-weight: bold;">+</button>
                            </div>`
                        }
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
            
            // Derive price accurately (handling dynamic prices for variable weight/size)
            const backendList = window.backendMenuItems || [];
            const bItem = backendList.find(i => String(i.id) === String(id) && (cItem.type ? i.type === cItem.type : true)) || cItem;
            let itemPrice = parseFloat(cItem.price);
            if (isNaN(itemPrice) || itemPrice === 0) {
                itemPrice = bItem ? parseFloat(bItem.price) || 0 : 0;
            }

            cart.push({
                id: id,
                type: cItem.type || 'Menu',
                quantity: qty,
                choices: choices,
                price: itemPrice
            });
        });
        return JSON.stringify(cart);
    }


    // Real-Time Validation Listeners
    const reqFields = ['full_name', 'contact_number', 'delivery_date', 'delivery_time', 'delivery_address'];
    reqFields.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', function() {
                if (this.value.trim() === '') {
                    showError(id, `err-${id}`);
                } else {
                    clearError(id, `err-${id}`);
                }
            });
            el.addEventListener('change', function() {
                if (this.value.trim() === '') {
                    showError(id, `err-${id}`);
                } else {
                    clearError(id, `err-${id}`);
                }
            });
        }
    });


    // Real-Time Inventory Validation
    const dateInputInv = document.getElementById('delivery_date');
    const timeInputInv = document.getElementById('delivery_time');
    
    async function checkInventoryAvailability() {
        if (!dateInputInv || !timeInputInv) return;
        const dateVal = dateInputInv.value;
        const timeVal = timeInputInv.value;
        
        if (!dateVal || !timeVal || window.cartItems.length === 0) return;
        
        const invErrId = 'err-inventory';
        let errEl = document.getElementById(invErrId);
        if (!errEl) {
            errEl = document.createElement('div');
            errEl.id = invErrId;
            errEl.className = 'invalid-feedback';
            timeInputInv.parentNode.appendChild(errEl);
        }

        // Standard catering operations: 6:00 AM to 9:00 PM (21:59)
        const [hours, mins] = timeVal.split(':').map(Number);
        if (hours < 6 || hours > 21) {
            errEl.innerText = "Invalid Time: Please select a time between 6:00 AM and 9:00 PM.";
            errEl.style.display = 'block';
            timeInputInv.classList.add('is-invalid');
            window.inventoryConflict = true;
            return;
        } else {
            errEl.style.display = 'none';
            timeInputInv.classList.remove('is-invalid');
            window.inventoryConflict = false;
        }
        
        try {
            const res = await fetch('/customer/api/check-inventory', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    caterer_id: window.catererId,
                    date: dateVal,
                    time: timeVal,
                    items: window.cartItems.map(i => ({ id: i.id, qty: i.qty }))
                })
            });
            const data = await res.json();
            
            const invErrId = 'err-inventory';
            let errEl = document.getElementById(invErrId);
            if (!errEl) {
                errEl = document.createElement('div');
                errEl.id = invErrId;
                errEl.className = 'invalid-feedback';
                // Append under time
                timeInputInv.parentNode.appendChild(errEl);
            }
            
            if (data.status === 'error') {
                errEl.innerText = data.error_text;
                errEl.style.display = 'block';
                dateInputInv.classList.add('is-invalid');
                timeInputInv.classList.add('is-invalid');
                // Block next step if inventory conflict
                window.inventoryConflict = true;
            } else {
                errEl.style.display = 'none';
                dateInputInv.classList.remove('is-invalid');
                timeInputInv.classList.remove('is-invalid');
                window.inventoryConflict = false;
            }
        } catch (e) {
            console.error("Inventory check failed", e);
        }
    }
    
    if (dateInputInv) dateInputInv.addEventListener('change', checkInventoryAvailability);
    if (timeInputInv) timeInputInv.addEventListener('change', checkInventoryAvailability);

    // --- NAVIGATION LOGIC ---
    window.nextScreen = async function (n, force = false) {
        if (!force && n > window.currentScreen) {
            if (window.currentScreen === 2 && n === 3) {
                if (typeof window.submitAtaCarteOrder === 'function') {
                    window.submitAtaCarteOrder();
                }
                return;
            }
            if (!validateScreen(window.currentScreen)) return;
            if (window.currentScreen === 2 && window.inventoryConflict) {
                if (typeof Swal !== 'undefined') {
                    Swal.fire('Inventory Conflict', 'Some items requested are out of stock for this date. Please adjust quantities or choose another date.', 'error');
                } else {
                    alert('Inventory Conflict: Some items requested are out of stock for this date.');
                }
                return;
            }
            
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
        
        const sidebarBtn = document.getElementById('sidebar-next-btn');
        if (sidebarBtn) {
            if (n === 1) {
                sidebarBtn.innerHTML = 'PROCEED TO PAYMENT <i class="fas fa-arrow-right" style="margin-left: 0.5rem;"></i>';
                sidebarBtn.style.display = 'block';
            } else if (n === 2) {
                sidebarBtn.innerHTML = 'CONFIRM & CHECKOUT <i class="fas fa-check" style="margin-left: 0.5rem;"></i>';
                sidebarBtn.style.display = 'block';
            } else {
                sidebarBtn.style.display = 'none';
            }
        }

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
            if (document.getElementById('pullout_time')) required.push('pullout_time');
            if (document.getElementById('event_duration')) required.push('event_duration');
            
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
            
            // Time Window Validation (6:00 AM to 9:00 PM)
            const dTime = document.getElementById('delivery_time');
            if (dTime && dTime.value) {
                const parts = dTime.value.split(':');
                if (parts.length === 2) {
                    const hour = parseInt(parts[0]);
                    if (hour < 6 || hour > 21) {
                        Swal.fire({icon: 'error', title: 'Invalid Time', text: 'Please select a time between 6:00 AM and 9:00 PM.'});
                        showError('delivery_time', 'err-delivery_time');
                        isValid = false;
                    }
                }
            }
            
            const phone = document.getElementById('contact_number').value.replace(/\D/g, '');
            if ((phone.length !== 11 || !phone.startsWith('09')) && phone.length > 0) {
                showError('contact_number', 'err-contact_number');
                isValid = false;
            }
        }
        
        if (window.inventoryConflict) {
            isValid = false;
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
        if (document.getElementById('pullout_time')) required.push('pullout_time');
        if (document.getElementById('event_duration')) required.push('event_duration');
        
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
                // Check if caterer operates on this day
                if (window.catererRules && window.catererRules.business_hours && window.catererRules.business_hours.operating_days) {
                    const opDays = window.catererRules.business_hours.operating_days;
                    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
                    const selectedDate = new Date(this.value);
                    const selectedDayName = dayNames[selectedDate.getDay()];
                    if (!opDays.includes(selectedDayName)) {
                        Swal.fire({
                            icon: 'warning',
                            title: 'Caterer Unavailable',
                            text: `This caterer does not operate on ${selectedDayName}s. Please select a different date.`,
                            confirmButtonColor: '#10b981'
                        });
                        this.value = '';
                        showError('delivery_date', 'err-delivery_date');
                        return;
                    }
                }
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
        formData.append('items', menuId);
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
        let securityDepositTotal = 0;
        
        if (base === null) {
            base = 0;
            window.cartItems.forEach(cItem => {
                const backendList = window.backendMenuItems || [];
                const bItem = backendList.find(i => String(i.id) === String(cItem.id) && (cItem.type ? i.type === cItem.type : true));
                const itemPrice = parseFloat(cItem.price || (bItem && bItem.price)) || 0;
                const qty = parseInt(cItem.qty) || 1;
                base += (itemPrice * qty);
            });
        }
        
        // Always recalculate deposit
        window.cartItems.forEach(cItem => {
            const backendList = window.backendMenuItems || [];
            const bItem = backendList.find(i => String(i.id) === String(cItem.id) && (cItem.type ? i.type === cItem.type : true));
            if (bItem && bItem.is_rental) {
                const cost = parseFloat(bItem.cost_value) || 0;
                const pct = parseFloat(bItem.security_deposit_pct) || 0;
                const qty = parseInt(cItem.qty) || 1;
                if (cost > 0 && pct > 0) {
                    securityDepositTotal += (cost * (pct / 100)) * qty;
                }
            }
        });
        
        window.currentSecurityDeposit = securityDepositTotal;

        const total = base + deliveryFee + securityDepositTotal;
        
        const sumBaseEl = document.getElementById('sum-base-total');
        if (sumBaseEl) sumBaseEl.innerText = '₱' + base.toLocaleString(undefined, { minimumFractionDigits: 2 });
        
        const depositRow = document.getElementById('deposit-row');
        const sumDepositEl = document.getElementById('sum-deposit-fee');
        if (depositRow && sumDepositEl) {
            if (securityDepositTotal > 0) {
                depositRow.style.display = 'flex';
                sumDepositEl.innerText = '₱' + securityDepositTotal.toLocaleString(undefined, { minimumFractionDigits: 2 });
            } else {
                depositRow.style.display = 'none';
            }
        }
        
        const feeRow = document.getElementById('delivery-row');
        const feeEl = document.getElementById('sum-delivery-fee');
        if (feeRow) {
            feeRow.querySelector('span:first-child').innerText = window.isServiceOnly ? 'Travel Fee' : 'Delivery Fee';
        }
        if (feeEl) {
            if (window.isManualQuote) {
                feeEl.innerText = '₱0.00 (TBD)';
            } else {
                feeEl.innerText = '₱' + deliveryFee.toLocaleString(undefined, { minimumFractionDigits: 2 });
            }
        }
        
        const grandEl = document.getElementById('sum-grand-total');
        if (grandEl) grandEl.innerText = '₱' + total.toLocaleString(undefined, { minimumFractionDigits: 2 });
    };

    window.updateFulfillment = function(el) {
        const selector = el.closest('.fulfillment-selector');
        const opts = selector.querySelectorAll('.fulfillment-opt');
        opts.forEach(o => o.classList.remove('active'));
        el.parentElement.classList.add('active');
        
        const addressSection = document.getElementById('address-section');
        const lblDelDate = document.getElementById('lbl_delivery_date');
        const lblDelTime = document.getElementById('lbl_delivery_time');

        if (el.value === 'pickup') {
            deliveryFee = 0;
            document.getElementById('delivery-row').style.display = 'none';
            if (addressSection) addressSection.classList.add('hidden-address');
            if (lblDelDate) lblDelDate.innerText = 'Pickup Date';
            if (lblDelTime) lblDelTime.innerText = 'Pickup Time';
            updateCheckoutSummary();
        } else {
            if (window.isServiceOnly) {
                deliveryFee = 0;
            }
            document.getElementById('delivery-row').style.display = 'flex';
            if (addressSection) addressSection.classList.remove('hidden-address');
            if (lblDelDate) lblDelDate.innerText = window.isServiceOnly ? 'Event Date' : (window.isRentalOnly ? 'Delivery & Setup Date' : 'Delivery Date');
            if (lblDelTime) lblDelTime.innerText = window.isServiceOnly ? 'Call Time' : (window.isRentalOnly ? 'Setup Time' : 'Delivery Time');
            if (typeof window.syncAddress === 'function') window.syncAddress(); 
        }
    };

    // Initialization moved to the bottom of the file

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
        const dateObj = new Date(form.delivery_date.value);
        const dateStr = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        let timeStr = form.delivery_time.value;
        if (timeStr) {
            const [hours, minutes] = timeStr.split(':');
            const h = parseInt(hours, 10);
            const ampm = h >= 12 ? 'PM' : 'AM';
            const h12 = h % 12 || 12;
            timeStr = `${h12}:${minutes} ${ampm}`;
        } else {
            timeStr = 'TBD';
        }
        document.getElementById('rev-datetime').innerText = `${dateStr} @ ${timeStr}`;
        
        const mode = form.fulfillment.value;
        document.getElementById('rev-location').innerText = mode === 'pickup' ? 'STORE PICKUP' : document.getElementById('address').value;
    }

    // --- ADDRESS SYNC & DYNAMIC FEE ---
    
    // PSGC Initial Load
    async function initPSGC() {
        const provSelect = document.getElementById('prov_select');
        if (!provSelect) return;
        
        provSelect.innerHTML = '<option value="">-- Select Province --</option>';
        
        const allowedProvinces = [
            { code: "130000000", name: "NATIONAL CAPITAL REGION (NCR)" },
            { code: "043400000", name: "Laguna" },
            { code: "041000000", name: "Batangas" },
            { code: "045600000", name: "Quezon" }
        ];
        
        allowedProvinces.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.code;
            opt.textContent = p.name;
            provSelect.appendChild(opt);
        });
    }
    
    function fallbackToTextInputs() {
        // Change selects to text inputs to allow manual entry if API fails
        const provGroup = document.getElementById('prov_select').parentElement;
        provGroup.innerHTML = '<label>Province</label><input type="text" id="prov_select" class="form-input" placeholder="e.g. Laguna" required oninput="handleProvinceChange()">';
        
        const cityGroup = document.getElementById('city_select').parentElement;
        cityGroup.innerHTML = '<label>Municipality / City</label><input type="text" id="city_select" class="form-input" placeholder="e.g. Santa Cruz" required oninput="handleCityChange()">';
        
        const brgyGroup = document.getElementById('brgy_select').parentElement;
        brgyGroup.innerHTML = '<label>Barangay</label><input type="text" id="brgy_select" class="form-input" placeholder="e.g. Patimbao" required oninput="syncAddress()">';
    }
    initPSGC();

    window.handleProvinceChange = async function() {
        const provSelect = document.getElementById('prov_select');
        const code = provSelect.value;
        const name = provSelect.options[provSelect.selectedIndex]?.text || '';
        document.getElementById('hidden_province').value = name;
        
        const citySelect = document.getElementById('city_select');
        const brgySelect = document.getElementById('brgy_select');
        
        citySelect.innerHTML = '<option value="">-- Select Municipality --</option>';
        brgySelect.innerHTML = '<option value="">-- Select Barangay --</option>';
        citySelect.disabled = true;
        brgySelect.disabled = true;

        if (!code) {
            if (typeof window.syncAddress === 'function') window.syncAddress();
            return;
        }

        try {
            citySelect.innerHTML = '<option value="">Loading...</option>';
            let endpoint = `https://psgc.gitlab.io/api/provinces/${code}/cities-municipalities/`;
            if (code === "130000000") endpoint = `https://psgc.gitlab.io/api/regions/${code}/cities-municipalities/`;
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2500);

            const res = await fetch(endpoint, { signal: controller.signal });
            clearTimeout(timeoutId);
            const cities = await res.json();
            
            citySelect.innerHTML = '<option value="">-- Select Municipality --</option>';
            cities.sort((a, b) => a.name.localeCompare(b.name)).forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.code;
                opt.textContent = c.name;
                citySelect.appendChild(opt);
            });
            citySelect.disabled = false;
        } catch (e) { 
            console.warn('Failed to load cities, falling back:', e);
            fallbackToTextInputs();
        }
        if (typeof window.syncAddress === 'function') window.syncAddress();
    };

    window.handleCityChange = async function() {
        const citySelect = document.getElementById('city_select');
        const code = citySelect.value;
        const name = citySelect.options[citySelect.selectedIndex]?.text || '';
        document.getElementById('hidden_municipality').value = name;
        
        const brgySelect = document.getElementById('brgy_select');
        brgySelect.innerHTML = '<option value="">-- Select Barangay --</option>';
        brgySelect.disabled = true;

        if (!code) {
            if (typeof window.syncAddress === 'function') window.syncAddress();
            return;
        }

        try {
            brgySelect.innerHTML = '<option value="">Loading...</option>';
            const res = await fetch(`https://psgc.gitlab.io/api/cities-municipalities/${code}/barangays/`);
            const brgys = await res.json();
            
            brgySelect.innerHTML = '<option value="">-- Select Barangay --</option>';
            brgys.sort((a, b) => a.name.localeCompare(b.name)).forEach(b => {
                const opt = document.createElement('option');
                opt.value = b.code;
                opt.textContent = b.name;
                brgySelect.appendChild(opt);
            });
            brgySelect.disabled = false;
        } catch (e) { console.error('Failed to load barangays:', e); }
        if (typeof window.syncAddress === 'function') window.syncAddress();
    };

    window.syncAddress = async function() {
        const provEl = document.getElementById('prov_select');
        const cityEl = document.getElementById('city_select');
        const brgyEl = document.getElementById('brgy_select');
        
        const prov = provEl ? (provEl.tagName === 'SELECT' ? (provEl.options[provEl.selectedIndex]?.text || '') : provEl.value) : '';
        const city = cityEl ? (cityEl.tagName === 'SELECT' ? (cityEl.options[cityEl.selectedIndex]?.text || '') : cityEl.value) : '';
        const brgy = brgyEl ? (brgyEl.tagName === 'SELECT' ? (brgyEl.options[brgyEl.selectedIndex]?.text || '') : brgyEl.value) : '';
        const street = document.getElementById('street_input') ? document.getElementById('street_input').value : '';
        
        const hiddenInput = document.getElementById('address');
        const fulfillInput = document.querySelector('input[name="fulfillment"]:checked');
        const fulfillment = fulfillInput ? fulfillInput.value : '';
        
        if (brgyEl) document.getElementById('hidden_barangay').value = brgy;
        
        const addressParts = [];
        if (street) addressParts.push(street);
        if (brgy && !brgy.includes('--')) addressParts.push("Brgy. " + brgy);
        if (city && !city.includes('--')) addressParts.push(city);
        if (prov && !prov.includes('--')) addressParts.push(prov);

        if (addressParts.length > 0) {
            hiddenInput.value = addressParts.join(', ') + ', Philippines';
            
            if (fulfillment === 'delivery' && city && !city.includes('--') && prov && !prov.includes('--')) {
                // Fetch dynamic fee
                try {
                    const res = await fetch(`/customer/api/caterer/${window.catererId}/delivery-fee?province=${encodeURIComponent(prov)}&municipality=${encodeURIComponent(city)}`);
                    if (res.ok) {
                        const data = await res.json();
                        if (data.found) {
                            if (data.is_manual_quote) {
                                window.isManualQuote = true;
                                document.getElementById('sum-delivery-fee').innerText = '₱0.00 (TBD)';
                                deliveryFee = 0;
                            } else {
                                window.isManualQuote = false;
                                deliveryFee = data.fee;
                            }
                        } else {
                            if (data.out_of_coverage_action === 'manual') {
                                window.isManualQuote = true;
                                document.getElementById('sum-delivery-fee').innerText = '₱0.00 (TBD)';
                                deliveryFee = 0;
                            } else {
                                // Default/reject - fallback to base fee
                                window.isManualQuote = false;
                                deliveryFee = data.base_fee || DEFAULT_FEE;
                            }
                        }
                    }
                } catch (e) { console.error('Fee fetch error', e); }
            }
        } else {
            hiddenInput.value = "";
            if (fulfillment === 'delivery') {
                deliveryFee = window.isServiceOnly ? 0 : DEFAULT_FEE;
                window.isManualQuote = false;
            }
        }
        
        if (window.isManualQuote) {
             const feeEl = document.getElementById('sum-delivery-fee');
             if (feeEl) feeEl.innerText = '₱0.00 (TBD)';
        }
        
        updateCheckoutSummary();
    };

    // --- PAYMENT SELECTION ---
    window.selectPayment = function(method, el) {
        document.getElementById('payment_method').value = method;
        document.querySelectorAll('.payment-opt').forEach(opt => opt.classList.remove('active'));
        el.classList.add('active');
        
        // Removed modal display logic - user uploads proof on dedicated page
        console.log("[CHECKOUT] Payment Method Selected:", method);
    };

    window.closePaymentModal = function() {
        const overlay = document.getElementById('paymentModalOverlay');
        if (overlay) overlay.style.display = 'none';
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
                confirmButtonColor: 'var(--hub-emerald-500)'
            });
            return;
        }

        const paymentMethod = document.getElementById('payment_method').value;
        
        if (paymentMethod !== 'CASH') {
            window.openPaymentModal(paymentMethod);
            return;
        }
        
        await window.finalSubmitOrder();
    };
    
    window.openPaymentModal = function(method) {
        document.getElementById('paymentModalOverlay').style.display = 'flex';
        document.getElementById('modalContentGCASH').style.display = 'none';
        document.getElementById('modalContentMAYA').style.display = 'none';
        document.getElementById('modalContentBANK').style.display = 'none';
        
        // Update AI modal amount
        const amountEl = document.getElementById('ai-modal-amount');
        if(amountEl && window.lastCalculatedTotal) {
            amountEl.innerText = window.lastCalculatedTotal.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
        
        const contentEl = document.getElementById('modalContent' + method);
        if(contentEl) contentEl.style.display = 'block';
    };
    
    window.closePaymentModal = function() {
        document.getElementById('paymentModalOverlay').style.display = 'none';
    };
    
    window.selectPayment = function(method, element) {
        document.querySelectorAll('.payment-opt').forEach(opt => opt.classList.remove('active'));
        if (element) {
            element.classList.add('active');
        }
        document.getElementById('payment_method').value = method;
        
        if (method !== 'CASH') {
            window.openPaymentModal(method);
        }
    };
    
    window.finalSubmitOrder = async function() {
        const paymentMethod = document.getElementById('payment_method').value;
        const proofInput = document.getElementById('proofImageInput');
        
        if (paymentMethod !== 'CASH' && proofInput && proofInput.files.length === 0) {
            const err = document.getElementById('uploadErrorMsg');
            if(err) {
                err.style.display = 'block';
                err.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Please select a receipt image to upload.';
            }
            return;
        }

        // Fallback recovery
        const currentId = getActiveBookingId();
        
        if (!currentId) {
            Swal.fire({icon: 'error', title: 'Session Lost', text: 'Please try going back to the first step to re-save your details.', confirmButtonColor: '#10b981'});
            console.error("[CHECKOUT] Submission failed: No bookingId found.");
            return;
        }

        // KYC Verification Check
        let requiresKyc = false;
        window.cartItems.forEach(cItem => {
            const backendList = window.backendMenuItems || [];
            const bItem = backendList.find(i => String(i.id) === String(cItem.id) && (cItem.type ? i.type === cItem.type : true));
            if (cItem.type === 'Equipment' || (bItem && bItem.requires_kyc)) {
                requiresKyc = true;
            }
        });

        if (requiresKyc && !window.isVerified) {
            Swal.fire({
                title: 'ID Verification Required',
                text: 'You are renting high-value equipment. Please verify your ID in your Customer Profile before proceeding.',
                icon: 'warning',
                confirmButtonText: 'Go to Profile',
                showCancelButton: true,
                confirmButtonColor: 'var(--hub-emerald-500)'
            }).then((result) => {
                if (result.isConfirmed) {
                    window.location.href = '/customer/settings#verification';
                }
            });
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
        formData.append('items', menuId);
        formData.append('cart_data', buildCartData());
        formData.append('total_amount', calculateTotal());
        formData.append('security_deposit_amount', window.currentSecurityDeposit || 0);
        
        // Add payment proof from the Modal
        if (proofInput && proofInput.files.length > 0) {
            formData.append('payment_proof', proofInput.files[0]);
        }
        
        const modalBtn = document.getElementById('submit-payment-btn');
        if (modalBtn) {
            modalBtn.disabled = true;
            modalBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Validating Receipt with AI...';
            modalBtn.style.opacity = '0.8';
        }
        
        try {
            const res = await fetch('/bookings/alacarte/checkout/submit', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.success) {
                sessionStorage.removeItem(sessionKey); 
                window.closePaymentModal();
                nextScreen(3, true); // Go to success screen! No redirect!
            } else {
                if (paymentMethod !== 'CASH') {
                    const err = document.getElementById('uploadErrorMsg');
                    if(err) {
                        err.style.display = 'block';
                        err.innerHTML = `<i class="fas fa-robot"></i> ${data.message}`;
                    }
                    if (modalBtn) {
                        modalBtn.disabled = false;
                        modalBtn.innerHTML = 'Upload Proof & Finish Booking';
                        modalBtn.style.opacity = '1';
                    }
                } else {
                    const errMsg = data.message || "Unknown Error";
                    Swal.fire({icon: 'error', title: 'Checkout Failed', text: errMsg, confirmButtonColor: '#10b981'});
                }
                btn.disabled = false;
                loader.style.display = 'none';
            }
        } catch (e) {
            Swal.fire({icon: 'error', title: 'Network Error', text: 'A network error occurred.', confirmButtonColor: '#10b981'});
            btn.disabled = false;
            loader.style.display = 'none';
            if (modalBtn) {
                modalBtn.disabled = false;
                modalBtn.innerHTML = 'Upload Proof & Finish Booking';
                modalBtn.style.opacity = '1';
            }
        }
    };

    // Initial call to sync UI & Render dynamic items on load
    const defaultFulfillment = document.querySelector('input[name="fulfillment"]:checked');
    if (defaultFulfillment) window.updateFulfillment(defaultFulfillment);
    window.renderBillItems();
});


// Universal Scheduling Validation
function validateSchedulingRules() {
    if (!window.catererRules) return true;
    
    let isValid = true;
    const rules = window.catererRules;
    
    // Clear previous errors
    document.querySelectorAll('.schedule-rule-error').forEach(e => e.remove());
    
    const showError = (inputId, message) => {
        const input = document.getElementById(inputId);
        if (input) {
            input.style.borderColor = '#ef4444';
            const err = document.createElement('div');
            err.className = 'schedule-rule-error field-error show';
            err.style.color = '#ef4444';
            err.style.fontSize = '0.75rem';
            err.style.marginTop = '4px';
            err.innerText = message;
            input.parentNode.appendChild(err);
            isValid = false;
        }
    };
    
    const resetError = (inputId) => {
        const input = document.getElementById(inputId);
        if (input) input.style.borderColor = '';
    };

    const deliveryTimeInput = document.getElementById('delivery_time');
    const pulloutTimeInput = document.getElementById('pullout_time');
    const eventDurationInput = document.getElementById('event_duration');
    const deliveryDateInput = document.getElementById('delivery_date');
    
    const format12Hour = (timeStr) => {
        if (!timeStr) return '';
        let [h, m] = timeStr.split(':');
        let hours = parseInt(h);
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12 || 12;
        return `${hours}:${m} ${ampm}`;
    };

    if (deliveryTimeInput && deliveryTimeInput.value) {
        resetError('delivery_time');
        const dt = deliveryTimeInput.value;
        const bh = rules.business_hours || {};
        
        if (bh.open_time && dt < bh.open_time) showError('delivery_time', `Time is before operating hours (${format12Hour(bh.open_time)})`);
        if (bh.close_time && dt > bh.close_time) showError('delivery_time', `Time is after operating hours (${format12Hour(bh.close_time)})`);
        
        if (deliveryDateInput && deliveryDateInput.value) {
            // Validate operating days
            if (bh.operating_days) {
                const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
                const selectedDateObj = new Date(deliveryDateInput.value);
                const selectedDayName = dayNames[selectedDateObj.getDay()];
                if (!bh.operating_days.includes(selectedDayName)) {
                    resetError('delivery_date');
                    showError('delivery_date', `Caterer is closed on ${selectedDayName}s.`);
                }
            }

            // Lead time validation
            if (rules.food_rules && rules.food_rules.lead_time_hours) {
                const selectedDate = new Date(deliveryDateInput.value + 'T' + dt);
                const now = new Date();
                const diffHours = (selectedDate - now) / (1000 * 60 * 60);
                if (diffHours < rules.food_rules.lead_time_hours) {
                    resetError('delivery_date');
                    showError('delivery_date', `Requires ${rules.food_rules.lead_time_hours} hours lead time.`);
                }
            }
        }
    }
    
    if (pulloutTimeInput && pulloutTimeInput.value && rules.equipment_rules) {
        resetError('pullout_time');
        const er = rules.equipment_rules;
        if (deliveryTimeInput && deliveryTimeInput.value) {
            const d1 = new Date(`2000-01-01T${deliveryTimeInput.value}`);
            let d2 = new Date(`2000-01-01T${pulloutTimeInput.value}`);
            if (d2 < d1) d2.setDate(d2.getDate() + 1); // Over-night assumption
            
            const diffHours = (d2 - d1) / (1000 * 60 * 60);
            if (er.min_rental_hours && diffHours < er.min_rental_hours) showError('pullout_time', `Minimum rental is ${er.min_rental_hours} hours`);
            if (er.max_rental_hours && diffHours > er.max_rental_hours) showError('pullout_time', `Maximum rental is ${er.max_rental_hours} hours`);
        }
    }
    
    if (eventDurationInput && eventDurationInput.value && rules.service_rules) {
        resetError('event_duration');
        const sr = rules.service_rules;
        const duration = parseInt(eventDurationInput.value);
        if (sr.min_duration_hours && duration < sr.min_duration_hours) showError('event_duration', `Minimum service is ${sr.min_duration_hours} hours`);
        if (sr.max_duration_hours && duration > sr.max_duration_hours) showError('event_duration', `Maximum service is ${sr.max_duration_hours} hours`);
    }

    return isValid;
}

// Attach validation to inputs
document.addEventListener('DOMContentLoaded', () => {
    ['delivery_time', 'delivery_date', 'pullout_time', 'event_duration'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', validateSchedulingRules);
    });
});
