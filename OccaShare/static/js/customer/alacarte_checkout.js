/**
 * alacarte_checkout.js
 * Handles all interactivity for the A La Carte / Equipment / Service checkout wizard.
 * Depends on window.backendMenuItems and other globals injected by the template.
 */

(function () {
    'use strict';

    /* ------------------------------------------------------------------ */
    /*  STATE                                                               */
    /* ------------------------------------------------------------------ */
    window.currentScreen = 1;
    let selectedFulfillment = 'delivery';
    let selectedPaymentMethod = '';
    let cartData = {};   // { itemId: { item, qty } }
    let deliveryFee = 0;

    /* ------------------------------------------------------------------ */
    /*  INIT                                                                */
    /* ------------------------------------------------------------------ */
    document.addEventListener('DOMContentLoaded', function () {
        initCart();
        updateSummarySidebar();
        updateBookingLabel();
        initAddressDropdowns();
        autoSelectPayment();
        setMinDate();
    });

    function initCart() {
        const items = window.backendMenuItems || [];
        items.forEach(function (item) {
            cartData[item.id] = { item: item, qty: item.min_quantity || 1 };
        });
    }

    function setMinDate() {
        const dateInput = document.getElementById('delivery_date');
        if (!dateInput) return;
        const lead = window.bookingLeadTime || 1;
        const today = new Date();
        today.setDate(today.getDate() + lead);
        dateInput.min = today.toISOString().split('T')[0];
    }

    /* ------------------------------------------------------------------ */
    /*  BOOKING LABEL — show specific item names instead of generic type    */
    /* ------------------------------------------------------------------ */
    function updateBookingLabel() {
        const labelEl = document.querySelector('.calc-title div:last-child');
        if (!labelEl) return;
        const items = window.backendMenuItems || [];
        if (items.length === 0) return;

        if (items.length === 1) {
            labelEl.innerHTML = '<i class="fas fa-receipt" style="color: var(--checkout-primary);"></i> ' + escHtml(items[0].name);
        } else {
            const extra = items.length - 1;
            labelEl.innerHTML = '<i class="fas fa-receipt" style="color: var(--checkout-primary);"></i> '
                + escHtml(items[0].name)
                + ' <span style="font-size:0.8rem;color:var(--text-muted);">+' + extra + ' more</span>';
        }
    }

    /* ------------------------------------------------------------------ */
    /*  SUMMARY SIDEBAR                                                     */
    /* ------------------------------------------------------------------ */
    function updateSummarySidebar() {
        const container = document.getElementById('dynamic-bill-items');
        if (!container) return;

        let html = '';
        let baseTotal = 0;
        let depositTotal = 0;

        Object.values(cartData).forEach(function (entry) {
            const item = entry.item;
            const qty = entry.qty || 1;
            const linePrice = (parseFloat(item.price) || 0) * qty;
            baseTotal += linePrice;

            if (item.type === 'Equipment' && item.security_deposit_pct) {
                depositTotal += linePrice * (item.security_deposit_pct / 100);
            }

            const pricingLabel = formatPricingUnit(item.pricing_unit);
            const qtyControls = item.type !== 'Service' ? `
                <div style="display:flex;align-items:center;gap:4px;margin-top:4px;justify-content:flex-end;">
                    <button type="button" onclick="changeQty('${item.id}', -1)"
                        style="width:22px;height:22px;border-radius:50%;border:1px solid #e2e8f0;background:white;font-size:0.8rem;cursor:pointer;line-height:1;">-</button>
                    <span id="qty-${item.id}" style="font-size:0.8rem;font-weight:700;min-width:18px;text-align:center;">${qty}</span>
                    <button type="button" onclick="changeQty('${item.id}', 1)"
                        style="width:22px;height:22px;border-radius:50%;border:1px solid #e2e8f0;background:white;font-size:0.8rem;cursor:pointer;line-height:1;">+</button>
                </div>` : '';

            html += `
            <div style="display:flex;align-items:flex-start;gap:0.75rem;margin-bottom:0.85rem;">
                <img src="${item.image_url || '/static/images/placeholder_dish.jpg'}"
                     style="width:42px;height:42px;border-radius:8px;object-fit:cover;flex-shrink:0;"
                     onerror="this.src='/static/images/placeholder_dish.jpg'">
                <div style="flex:1;min-width:0;">
                    <div style="font-size:0.85rem;font-weight:700;color:var(--text-slate);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                         title="${escHtml(item.name)}">${escHtml(item.name)}</div>
                    <div style="font-size:0.75rem;color:var(--text-muted);">${pricingLabel}</div>
                </div>
                <div style="text-align:right;flex-shrink:0;">
                    <div style="font-size:0.9rem;font-weight:800;color:var(--text-slate);">${formatPeso(linePrice)}</div>
                    ${qtyControls}
                </div>
            </div>`;
        });

        container.innerHTML = html || '<p style="font-size:0.85rem;color:var(--text-muted);text-align:center;">No items selected.</p>';

        const baseTotalEl = document.getElementById('sum-base-total');
        const grandTotalEl = document.getElementById('sum-grand-total');
        const depositRow = document.getElementById('deposit-row');
        const depositFeeEl = document.getElementById('sum-deposit-fee');
        const deliveryFeeEl = document.getElementById('sum-delivery-fee');

        if (baseTotalEl) baseTotalEl.textContent = formatPeso(baseTotal);

        const isPickup = selectedFulfillment === 'pickup';
        if (deliveryFeeEl) {
            if (isPickup) {
                deliveryFee = 0;
                deliveryFeeEl.textContent = 'Free';
            } else {
                deliveryFeeEl.textContent = deliveryFee > 0 ? formatPeso(deliveryFee) : 'TBD';
            }
        }

        if (depositRow && depositFeeEl) {
            if (depositTotal > 0) {
                depositRow.style.display = 'flex';
                depositFeeEl.textContent = formatPeso(depositTotal);
            } else {
                depositRow.style.display = 'none';
            }
        }

        const grandTotal = baseTotal + (isPickup ? 0 : deliveryFee) + depositTotal;
        if (grandTotalEl) grandTotalEl.textContent = formatPeso(grandTotal);

        const aiAmountEl = document.getElementById('ai-modal-amount');
        if (aiAmountEl) aiAmountEl.textContent = grandTotal.toFixed(2);
    }

    /* ------------------------------------------------------------------ */
    /*  QUANTITY CONTROLS                                                   */
    /* ------------------------------------------------------------------ */
    window.changeQty = function (itemId, delta) {
        if (!cartData[itemId]) return;
        const item = cartData[itemId].item;
        const min = item.min_quantity || 1;
        let newQty = (cartData[itemId].qty || 1) + delta;
        if (newQty < min) newQty = min;
        cartData[itemId].qty = newQty;
        const qtyEl = document.getElementById('qty-' + itemId);
        if (qtyEl) qtyEl.textContent = newQty;
        updateSummarySidebar();
    };

    /* ------------------------------------------------------------------ */
    /*  FULFILLMENT                                                         */
    /* ------------------------------------------------------------------ */
    window.updateFulfillment = function (radio) {
        selectedFulfillment = radio.value;

        document.querySelectorAll('.fulfillment-opt').forEach(function (opt) {
            opt.classList.remove('active');
        });
        const parent = radio.closest ? radio.closest('.fulfillment-opt') : null;
        if (parent) parent.classList.add('active');

        const addressSection = document.getElementById('address-section');
        const pickupInfo = document.getElementById('pickup-address-info');

        if (selectedFulfillment === 'pickup') {
            if (addressSection) addressSection.style.display = 'none';
            if (pickupInfo) pickupInfo.style.display = 'block';
            deliveryFee = 0;
        } else {
            if (addressSection) addressSection.style.display = 'block';
            if (pickupInfo) pickupInfo.style.display = 'none';
            deliveryFee = window.catererBaseDeliveryFee || 0;
        }

        updateSummarySidebar();
    };

    /* ------------------------------------------------------------------ */
    /*  MULTI-SCREEN NAVIGATION                                             */
    /* ------------------------------------------------------------------ */
    window.nextScreen = function (targetScreen) {
        if (targetScreen > window.currentScreen) {
            if (!validateScreen(window.currentScreen)) return;
        }

        if (targetScreen === window.paymentStep) {
            populateReviewPanel();
        }

        const currentEl = document.getElementById('screen-' + window.currentScreen);
        const nextEl = document.getElementById('screen-' + targetScreen);
        if (currentEl) currentEl.classList.remove('active');
        if (nextEl) nextEl.classList.add('active');
        window.currentScreen = targetScreen;
        updateStepper(targetScreen);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    function validateScreen(screen) {
        let valid = true;

        if (screen === 1) {
            const fullName = document.getElementById('full_name');
            if (fullName && !fullName.value.trim()) {
                showFieldError('err-full_name', true); valid = false;
            } else { showFieldError('err-full_name', false); }

            const contact = document.getElementById('contact_number');
            if (contact) {
                const val = contact.value.trim();
                if (!val || val.length !== 11 || !val.startsWith('09')) {
                    showFieldError('err-contact_number', true); valid = false;
                } else { showFieldError('err-contact_number', false); }
            }

            const date = document.getElementById('delivery_date');
            if (date && !date.value) {
                showFieldError('err-delivery_date', true); valid = false;
            } else { showFieldError('err-delivery_date', false); }

            const time = document.getElementById('delivery_time');
            if (time && !time.value) {
                showFieldError('err-delivery_time', true); valid = false;
            } else { showFieldError('err-delivery_time', false); }

            if (selectedFulfillment === 'delivery') {
                const addrInput = document.getElementById('address');
                if (addrInput && !addrInput.value.trim()) {
                    showFieldError('err-address', true); valid = false;
                } else { showFieldError('err-address', false); }
            }
        }

        return valid;
    }

    function showFieldError(id, show) {
        const el = document.getElementById(id);
        if (el) el.style.display = show ? 'block' : 'none';
    }

    function updateStepper(screen) {
        for (let i = 1; i <= 4; i++) {
            const step = document.getElementById('m-step-' + i);
            if (!step) continue;
            step.classList.remove('active', 'completed');
            if (i < screen) step.classList.add('completed');
            else if (i === screen) step.classList.add('active');
        }
    }

    function populateReviewPanel() {
        const name = document.getElementById('full_name');
        const phone = document.getElementById('contact_number');
        const date = document.getElementById('delivery_date');
        const time = document.getElementById('delivery_time');
        const address = document.getElementById('address');

        const set = function (id, val) {
            const el = document.getElementById(id);
            if (el) el.textContent = val || '-';
        };

        set('rev-name', name ? name.value : '');
        set('rev-phone', phone ? phone.value : '');
        if (date && date.value && time && time.value) {
            const dt = new Date(date.value + 'T' + time.value);
            set('rev-datetime', dt.toLocaleString('en-PH', { dateStyle: 'medium', timeStyle: 'short' }));
        } else {
            set('rev-datetime', '-');
        }
        set('rev-location', selectedFulfillment === 'pickup' ? 'Store Pickup / Self-Collect' : (address ? address.value : '-'));
    }

    /* ------------------------------------------------------------------ */
    /*  PAYMENT METHOD                                                      */
    /* ------------------------------------------------------------------ */
    function autoSelectPayment() {
        const hidden = document.getElementById('payment_method');
        if (hidden && hidden.value) selectedPaymentMethod = hidden.value;
    }

    window.selectPayment = function (method, card) {
        selectedPaymentMethod = method;
        document.querySelectorAll('.payment-opt').forEach(function (opt) {
            opt.classList.remove('active');
        });
        if (card) card.classList.add('active');
        const hidden = document.getElementById('payment_method');
        if (hidden) hidden.value = method;
    };

    /* ------------------------------------------------------------------ */
    /*  SUBMIT ORDER                                                        */
    /* ------------------------------------------------------------------ */
    window.submitAtaCarteOrder = function () {
        const terms = document.getElementById('alacarteTermsAgreement');
        if (terms && !terms.checked) {
            alert('Please agree to the terms before proceeding.');
            return;
        }

        const loading = document.getElementById('place-order-loading');
        const btn = document.getElementById('final-submit-btn');

        if (selectedPaymentMethod && selectedPaymentMethod !== 'CASH') {
            openPaymentModal();
            return;
        }

        if (loading) loading.style.display = 'block';
        if (btn) btn.disabled = true;
        submitFormData(null);
    };

    /* ------------------------------------------------------------------ */
    /*  PAYMENT MODAL                                                       */
    /* ------------------------------------------------------------------ */
    window.openPaymentModal = function () {
        const overlay = document.getElementById('paymentModalOverlay');
        if (overlay) overlay.style.display = 'flex';

        ['GCASH', 'MAYA', 'BANK'].forEach(function (m) {
            const el = document.getElementById('modalContent' + m);
            if (el) el.style.display = (selectedPaymentMethod === m) ? 'block' : 'none';
        });

        const grandTotalEl = document.getElementById('sum-grand-total');
        const aiEl = document.getElementById('ai-modal-amount');
        if (grandTotalEl && aiEl) {
            aiEl.textContent = grandTotalEl.textContent.replace('₱', '').replace(/,/g, '');
        }
    };

    window.closePaymentModal = function () {
        const overlay = document.getElementById('paymentModalOverlay');
        if (overlay) overlay.style.display = 'none';
    };

    window.finalSubmitOrder = function () {
        const proofInput = document.getElementById('proofImageInput');
        const errorEl = document.getElementById('uploadErrorMsg');
        const submitBtn = document.getElementById('submit-payment-btn');

        if (!proofInput || !proofInput.files || proofInput.files.length === 0) {
            if (errorEl) { errorEl.textContent = 'Please upload your proof of payment.'; errorEl.style.display = 'block'; }
            return;
        }

        if (errorEl) errorEl.style.display = 'none';
        if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Submitting...'; }

        const reader = new FileReader();
        reader.onload = function (e) { submitFormData(e.target.result); };
        reader.readAsDataURL(proofInput.files[0]);
    };

    function submitFormData(proofBase64) {
        const form = document.getElementById('checkoutForm');
        if (!form) return;

        const quantities = {};
        Object.values(cartData).forEach(function (entry) {
            quantities[entry.item.id] = entry.qty;
        });

        const formData = new FormData(form);
        formData.set('caterer_id', window.catererId || '');
        formData.set('items', window.menuId || '');
        formData.set('cart_data', JSON.stringify(quantities));
        formData.set('fulfillment', selectedFulfillment);
        formData.set('payment_method', selectedPaymentMethod);
        if (proofBase64) formData.set('payment_proof_base64', proofBase64);

        let baseTotal = 0;
        Object.values(cartData).forEach(function (entry) {
            baseTotal += (parseFloat(entry.item.price) || 0) * (entry.qty || 1);
        });
        const grandTotalEl = document.getElementById('sum-grand-total');
        const grandTotalVal = grandTotalEl ? grandTotalEl.textContent.replace(/[^0-9.]/g, '') : String(baseTotal);
        formData.set('total_amount', grandTotalVal);
        formData.set('base_amount', String(baseTotal.toFixed(2)));

        fetch('/bookings/alacarte/checkout/submit', {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        })
        .then(function (resp) {
            if (!resp.ok) return resp.json().then(function (d) { throw new Error(d.detail || 'Submission failed'); });
            return resp.json();
        })
        .then(function (data) {
            closePaymentModal();
            const successScreen = (window.paymentStep || 2) + 1;
            const currentEl = document.getElementById('screen-' + window.currentScreen);
            const successEl = document.getElementById('screen-' + successScreen);
            if (currentEl) currentEl.classList.remove('active');
            if (successEl) successEl.classList.add('active');
            window.currentScreen = successScreen;

            if (data && data.booking_id) {
                const invoiceBtn = document.getElementById('download-invoice-btn');
                if (invoiceBtn) invoiceBtn.href = '/customer/bookings/' + data.booking_id + '/invoice';
            }
        })
        .catch(function (err) {
            console.error('Order submission error:', err);
            alert('Failed to submit: ' + err.message);
            const loading = document.getElementById('place-order-loading');
            const btn = document.getElementById('final-submit-btn');
            const submitBtn = document.getElementById('submit-payment-btn');
            if (loading) loading.style.display = 'none';
            if (btn) btn.disabled = false;
            if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Upload Proof & Finish Order'; }
        });
    }

    /* ------------------------------------------------------------------ */
    /*  COMBO SELECTION                                                     */
    /* ------------------------------------------------------------------ */
    window.handleComboSelection = function (checkbox) {
        const grid = checkbox.closest('[data-limit]');
        if (!grid) return;
        const limit = parseInt(grid.getAttribute('data-limit')) || 99;
        const id = grid.getAttribute('data-id');
        const checked = grid.querySelectorAll('input[type="checkbox"]:checked');
        if (checkbox.checked && checked.length > limit) {
            checkbox.checked = false;
            alert('You can only select up to ' + limit + ' options.');
            return;
        }
        const counter = document.getElementById('counter-combo-' + id);
        const finalCount = grid.querySelectorAll('input[type="checkbox"]:checked').length;
        if (counter) counter.textContent = finalCount + ' / ' + limit + ' Selected';
    };

    /* ------------------------------------------------------------------ */
    /*  ADDRESS DROPDOWNS (PSGC)                                           */
    /* ------------------------------------------------------------------ */
    let phProvinces = null;

    function initAddressDropdowns() {
        const editSection = document.getElementById('address-edit-section');
        if (!editSection || editSection.style.display === 'none') return;
        loadProvinces();
    }

    function loadProvinces() {
        if (phProvinces) { populateProvinces(phProvinces); return; }
        fetch('https://psgc.gitlab.io/api/provinces.json')
            .then(function (r) { return r.json(); })
            .then(function (data) { phProvinces = data; populateProvinces(data); })
            .catch(function () { console.warn('Could not load provinces'); });
    }

    function populateProvinces(data) {
        const provSelect = document.getElementById('prov_select');
        if (!provSelect) return;
        provSelect.innerHTML = '<option value="" disabled selected hidden>-- Select Province --</option>';
        data.sort(function (a, b) { return (a.name || '').localeCompare(b.name || ''); })
            .forEach(function (prov) {
                const opt = document.createElement('option');
                opt.value = prov.name;
                opt.dataset.code = prov.code;
                opt.textContent = prov.name;
                provSelect.appendChild(opt);
            });

        const saved = window.userSavedAddress;
        if (saved && saved.province) {
            Array.from(provSelect.options).forEach(function (opt) {
                if (opt.value === saved.province) { provSelect.value = opt.value; handleProvinceChange(); }
            });
        }
    }

    window.handleProvinceChange = function () {
        const provSelect = document.getElementById('prov_select');
        const citySelect = document.getElementById('city_select');
        const brgySelect = document.getElementById('brgy_select');
        if (!provSelect || !citySelect) return;

        citySelect.innerHTML = '<option value="" disabled selected hidden>-- Select Municipality --</option>';
        citySelect.disabled = true;
        if (brgySelect) { brgySelect.innerHTML = '<option value="" disabled selected hidden>-- Select Barangay --</option>'; brgySelect.disabled = true; }

        const selOpt = provSelect.options[provSelect.selectedIndex];
        const code = selOpt ? selOpt.dataset.code : null;
        if (!code) return;

        fetch('https://psgc.gitlab.io/api/provinces/' + code + '/cities-municipalities.json')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                data.sort(function (a, b) { return (a.name || '').localeCompare(b.name || ''); })
                    .forEach(function (city) {
                        const opt = document.createElement('option');
                        opt.value = city.name;
                        opt.dataset.code = city.code;
                        opt.textContent = city.name;
                        citySelect.appendChild(opt);
                    });
                citySelect.disabled = false;

                const saved = window.userSavedAddress;
                if (saved && saved.city) {
                    Array.from(citySelect.options).forEach(function (opt) {
                        if (opt.value === saved.city) { citySelect.value = opt.value; handleCityChange(); }
                    });
                }
            }).catch(function () { citySelect.disabled = false; });
    };

    window.handleCityChange = function () {
        const citySelect = document.getElementById('city_select');
        const brgySelect = document.getElementById('brgy_select');
        if (!citySelect || !brgySelect) return;

        brgySelect.innerHTML = '<option value="" disabled selected hidden>-- Select Barangay --</option>';
        brgySelect.disabled = true;

        const selOpt = citySelect.options[citySelect.selectedIndex];
        const code = selOpt ? selOpt.dataset.code : null;
        if (!code) return;

        fetch('https://psgc.gitlab.io/api/cities-municipalities/' + code + '/barangays.json')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                data.sort(function (a, b) { return (a.name || '').localeCompare(b.name || ''); })
                    .forEach(function (brgy) {
                        const opt = document.createElement('option');
                        opt.value = brgy.name;
                        opt.textContent = brgy.name;
                        brgySelect.appendChild(opt);
                    });
                brgySelect.disabled = false;

                const saved = window.userSavedAddress;
                if (saved && saved.brgy) {
                    Array.from(brgySelect.options).forEach(function (opt) {
                        if (opt.value === saved.brgy) { brgySelect.value = opt.value; syncAddress(); }
                    });
                }
            }).catch(function () { brgySelect.disabled = false; });
    };

    window.syncAddress = function () {
        const parts = [];
        const street = document.getElementById('street_input');
        const brgy = document.getElementById('brgy_select');
        const city = document.getElementById('city_select');
        const prov = document.getElementById('prov_select');

        if (street && street.value.trim()) parts.push(street.value.trim());
        if (brgy && brgy.value) parts.push('Brgy. ' + brgy.value);
        if (city && city.value) parts.push(city.value);
        if (prov && prov.value) parts.push(prov.value);
        parts.push('Philippines');

        const full = parts.join(', ');
        const hiddenAddr = document.getElementById('address');
        const hiddenProv = document.getElementById('hidden_province');
        const hiddenCity = document.getElementById('hidden_municipality');
        const hiddenBrgy = document.getElementById('hidden_barangay');

        if (hiddenAddr) hiddenAddr.value = full;
        if (hiddenProv && prov) hiddenProv.value = prov.value || '';
        if (hiddenCity && city) hiddenCity.value = city.value || '';
        if (hiddenBrgy && brgy) hiddenBrgy.value = brgy.value || '';
    };

    window.showEditAddress = function () {
        document.getElementById('address-display-section').style.display = 'none';
        document.getElementById('address-edit-section').style.display = 'block';
        loadProvinces();
    };

    window.cancelEditAddress = function () {
        const disp = document.getElementById('address-display-section');
        const edit = document.getElementById('address-edit-section');
        if (disp) disp.style.display = 'flex';
        if (edit) edit.style.display = 'none';
    };

    window.saveEditAddress = function () {
        syncAddress();
        const hiddenAddr = document.getElementById('address');
        const savedText = document.getElementById('saved-address-text');
        if (savedText && hiddenAddr) savedText.textContent = hiddenAddr.value;
        cancelEditAddress();
        showFieldError('err-address', false);
    };

    /* ------------------------------------------------------------------ */
    /*  HELPERS                                                             */
    /* ------------------------------------------------------------------ */
    function formatPeso(amount) {
        return '\u20b1' + (parseFloat(amount) || 0).toLocaleString('en-PH', {
            minimumFractionDigits: 2, maximumFractionDigits: 2
        });
    }

    function formatPricingUnit(unit) {
        const map = {
            per_tray: 'per tray', per_pax: 'per pax', per_unit: 'per unit',
            per_hour: 'per hour', per_day: 'per day', per_event: 'per event', per_set: 'per set'
        };
        return map[unit] || (unit ? unit.replace(/_/g, ' ') : 'per unit');
    }

    function escHtml(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    }

})();
