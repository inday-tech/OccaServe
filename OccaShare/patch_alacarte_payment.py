import os

js_file = r"c:\OccaServe\OccaShare\app\static\js\customer\alacarte_checkout.js"
html_file = r"c:\OccaServe\OccaShare\templates\customer\booking_wizard\alacarte_checkout.html"

# --- 1. PATCH ALACARTE_CHECKOUT.HTML ---
with open(html_file, "r", encoding="utf-8") as f:
    html_content = f.read()

# Remove the confusing "onlinePaymentNote"
target_note = """                            <!-- Payment Instruction Info -->
                            <div id="onlinePaymentNote" style="display: none; margin-top: 1.5rem; padding: 1rem; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 12px; color: #1e3a8a; font-size: 0.85rem; display: flex; align-items: flex-start; gap: 10px;">
                                <i class="fas fa-info-circle" style="font-size: 1.1rem; margin-top: 2px;"></i>
                                <div>
                                    <strong style="display: block; margin-bottom: 2px;">Payment Details Next</strong>
                                    You will be given the account details and asked to upload your proof of payment on the next page after you click Confirm & Checkout.
                                </div>
                            </div>
                            
                            <script>
                                function updatePaymentNote() {
                                    const method = document.getElementById('payment_method').value;
                                    const note = document.getElementById('onlinePaymentNote');
                                    if (note) {
                                        note.style.display = (method !== 'CASH') ? 'flex' : 'none';
                                    }
                                }
                                
                                // Call immediately
                                document.addEventListener('DOMContentLoaded', updatePaymentNote);
                                
                                // Hook into existing selectPayment if possible or just run a periodic check since we can't easily modify the script inside the same file dynamically right now without making it brittle.
                                // Actually, we modified selectPayment in alacarte_checkout.js. Let's just hook the click events.
                                document.addEventListener('click', function(e) {
                                    if(e.target.closest('.payment-opt')) {
                                        setTimeout(updatePaymentNote, 50);
                                    }
                                });
                            </script>"""

if target_note in html_content:
    html_content = html_content.replace(target_note, "<!-- Payment method note removed. Will use modal. -->")

# Inject Modal HTML
modal_html = """
{% block modals %}
    <!-- Dynamic Payment Modal -->
    <div id="paymentModalOverlay" style="display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.6); z-index: 99999; align-items: center; justify-content: center; backdrop-filter: blur(4px);">
        <div id="paymentModalCard" style="background: white; width: 95%; max-width: 450px; border-radius: 20px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25); display: flex; flex-direction: column; max-height: 90vh;">
            
            <div style="background: #f8fafc; padding: 1.5rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0;">
                <h3 id="modalTitle" style="margin: 0; font-size: 1.25rem; color: var(--up-slate-900); display: flex; align-items: center; gap: 8px; font-weight: 800;">
                    <i class="fas fa-wallet"></i> Payment Details
                </h3>
                <button type="button" onclick="closePaymentModal()" style="background: none; border: none; font-size: 1.25rem; color: var(--up-slate-400); cursor: pointer;"><i class="fas fa-times"></i></button>
            </div>
            
            <div style="padding: 2rem; overflow-y: auto;">
                <div id="modalContentGCASH" style="display: none; text-align: center;">
                    <img src="{{ caterer.gcash_qr_url }}" alt="GCash QR" style="width: 220px; height: 220px; object-fit: cover; border-radius: 16px; border: 2px solid #bfdbfe; margin-bottom: 1rem;">
                    
                    <div style="background: #eff6ff; padding: 1.25rem; border-radius: 12px; margin-bottom: 1.5rem; text-align: left;">
                        <h4 style="font-size: 0.9rem; font-weight: 800; color: #1e3a8a; margin-top: 0; margin-bottom: 1rem;"><i class="fas fa-info-circle"></i> GCash Payment Steps</h4>
                        <div style="font-size:0.85rem; margin-bottom:5px;">1. Open GCash App.</div>
                        <div style="font-size:0.85rem; margin-bottom:5px;">2. Scan QR or send to <strong>{{ caterer.gcash_number }}</strong>.</div>
                        <div style="font-size:0.85rem;">3. Upload the screenshot below.</div>
                    </div>
                </div>
                
                <div id="modalContentMAYA" style="display: none; text-align: center;">
                    <img src="{{ caterer.maya_qr_url }}" alt="Maya QR" style="width: 220px; height: 220px; object-fit: cover; border-radius: 16px; border: 2px solid #bbf7d0; margin-bottom: 1rem;">
                    
                    <div style="background: #f0fdf4; padding: 1.25rem; border-radius: 12px; margin-bottom: 1.5rem; text-align: left;">
                        <h4 style="font-size: 0.9rem; font-weight: 800; color: #14532d; margin-top: 0; margin-bottom: 1rem;"><i class="fas fa-info-circle"></i> Maya Payment Steps</h4>
                        <div style="font-size:0.85rem; margin-bottom:5px;">1. Open Maya App.</div>
                        <div style="font-size:0.85rem; margin-bottom:5px;">2. Scan QR or send to <strong>{{ caterer.maya_number }}</strong>.</div>
                        <div style="font-size:0.85rem;">3. Upload the screenshot below.</div>
                    </div>
                </div>
                
                <div id="modalContentBANK" style="display: none;">
                    <div style="background: #fefce8; padding: 1.5rem; border-radius: 12px; margin-bottom: 1rem; border: 1px solid #fef08a;">
                        <div style="margin-bottom: 1rem;">
                            <div style="font-size: 0.85rem; color: #ca8a04; font-weight: 600;">Bank Name</div>
                            <div style="font-size: 1.1rem; font-weight: 700; color: #713f12;">{{ caterer.bank_name }}</div>
                        </div>
                        <div style="margin-bottom: 1rem;">
                            <div style="font-size: 0.85rem; color: #ca8a04; font-weight: 600;">Account Name</div>
                            <div style="font-size: 1.1rem; font-weight: 700; color: #713f12;">{{ caterer.bank_account_name }}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.85rem; color: #ca8a04; font-weight: 600;">Account Number</div>
                            <div style="font-size: 1.25rem; font-weight: 800; color: #713f12; letter-spacing: 1px;">{{ caterer.bank_account_number }}</div>
                        </div>
                    </div>
                </div>
                
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 2rem 0;">
                
                <div>
                    <h4 style="font-size: 1rem; color: var(--up-slate-900); margin-bottom: 1rem; font-weight: 800;"><i class="fas fa-cloud-upload-alt" style="color: var(--up-emerald-500);"></i> Submit Proof of Payment</h4>
                    <div style="margin-bottom: 1.25rem;">
                        <label style="display: block; font-size: 0.85rem; font-weight: 700; margin-bottom: 6px;">Receipt Image</label>
                        <input type="file" id="proofImageInput" accept="image/*" style="width: 100%; padding: 0.75rem; border: 2px dashed #cbd5e1; border-radius: 8px; background: #f8fafc;">
                    </div>
                    <div id="uploadErrorMsg" style="display: none; background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; padding: 1rem; border-radius: 12px; font-size: 0.85rem; margin-bottom: 1.25rem; font-weight: 500;"></div>
                </div>

                <button type="button" id="submit-payment-btn" onclick="finalSubmitOrder()" style="width: 100%; background: var(--up-emerald-500); color: white; border: none; padding: 1rem; border-radius: 8px; font-weight: 800; font-size: 1rem; cursor: pointer; transition: 0.2s;">
                    Upload Proof & Finish Booking
                </button>
            </div>
        </div>
    </div>
{% endblock %}"""

html_content = html_content.replace("{% block modals %}{% endblock %}", modal_html)

with open(html_file, "w", encoding="utf-8") as f:
    f.write(html_content)

# --- 2. PATCH ALACARTE_CHECKOUT.JS ---
with open(js_file, "r", encoding="utf-8") as f:
    js_content = f.read()

# Find window.submitAtaCarteOrder = async function() {
target_js_func = """    window.submitAtaCarteOrder = async function() {
        // Terms & Conditions Validation
        const termsCheckbox = document.getElementById('alacarteTermsAgreement');
        if (termsCheckbox && !termsCheckbox.checked) {
            Swal.fire({
                title: 'Action Required',
                text: 'You must agree to the caterer\\'s Terms & Conditions before placing your order.',
                icon: 'warning',
                confirmButtonColor: 'var(--hub-emerald-500)'
            });
            return;
        }

        const paymentMethod = document.getElementById('payment_method').value;
        const proofInput = document.getElementById('payment_proof');
        if (paymentMethod !== 'CASH' && proofInput && proofInput.files.length === 0) {
            Swal.fire({
                title: 'Missing Receipt',
                text: 'Please upload a screenshot of your payment receipt to proceed.',
                icon: 'warning',
                confirmButtonColor: 'var(--hub-emerald-500)'
            });
            return;
        }"""

replacement_js_func = """    window.submitAtaCarteOrder = async function() {
        // Terms & Conditions Validation
        const termsCheckbox = document.getElementById('alacarteTermsAgreement');
        if (termsCheckbox && !termsCheckbox.checked) {
            Swal.fire({
                title: 'Action Required',
                text: 'You must agree to the caterer\\'s Terms & Conditions before placing your order.',
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
        
        const contentEl = document.getElementById('modalContent' + method);
        if(contentEl) contentEl.style.display = 'block';
    };
    
    window.closePaymentModal = function() {
        document.getElementById('paymentModalOverlay').style.display = 'none';
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
        }"""

js_content = js_content.replace(target_js_func, replacement_js_func)

# Fix formData appending and redirect
target_redirect = """        // Add payment proof manually since it is outside the form
        if (proofInput && proofInput.files.length > 0) {
            formData.append('payment_proof', proofInput.files[0]);
        }
        
        try {
            const res = await fetch('/bookings/alacarte/checkout/submit', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.success) {
                sessionStorage.removeItem(sessionKey); // Clear session on success
                
                // Redirect immediately to payment page if not CASH
                if (paymentMethod !== 'CASH') {
                    window.location.href = `/bookings/step/payment/${data.booking_id}`;
                } else {
                    // For CASH, show the local success screen
                    nextScreen(3, true);
                }
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
    };"""

replacement_redirect = """        // Add payment proof from the Modal
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
    };"""

js_content = js_content.replace(target_redirect, replacement_redirect)

with open(js_file, "w", encoding="utf-8") as f:
    f.write(js_content)
print("Patched alacarte payment flow.")
