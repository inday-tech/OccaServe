import re

file_path = r"c:\OccaServe\OccaShare\templates\customer\food_order_manage.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add the payment upload UI if it's pending_payment or reupload_requested
payment_ui_html = """
            {% if booking.status in ['pending_payment', 'awaiting_payment', 'draft'] or booking.payment_status in ['reupload_requested', 'pending'] %}
            {% if booking.status != 'draft' and booking.payment_status != 'paid' and booking.payment_method != 'CASH' %}
            <div class="section-card" style="margin-top: 1.5rem; border: 2px solid var(--primary);">
                <h3 style="font-size: 1.25rem; color: var(--text-primary); margin-bottom: 1rem;"><i class="fas fa-wallet text-primary"></i> Complete Your Payment</h3>
                
                {% if booking.payment_status == 'reupload_requested' %}
                <div class="alert alert-danger" style="margin-bottom: 1rem; border-radius: 8px;">
                    <i class="fas fa-exclamation-circle"></i> <strong>Payment Rejected:</strong> The caterer requested a clearer image or valid receipt. Please re-upload.
                </div>
                {% endif %}

                <p style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 1.5rem;">
                    Please select your preferred payment method and upload the proof of payment. 
                    <br><strong style="color: var(--primary);">AI Verification:</strong> Our system will scan your receipt to verify the amount (<strong>₱{{ "{:,.2f}".format(booking.total_amount or 0) }}</strong>), date, and caterer details. Ensure the screenshot is clear and unedited.
                </p>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                    {% if booking.caterer.gcash_number %}
                    <div class="method-card" onclick="selectManagePayment('GCash')" id="mc-GCash" style="border: 2px solid #e2e8f0; border-radius: 12px; padding: 1rem; text-align: center; cursor: pointer; transition: 0.2s;">
                        <i class="fas fa-mobile-alt text-blue-500" style="font-size: 1.5rem; margin-bottom: 0.5rem;"></i><br>GCash
                    </div>
                    {% endif %}
                    {% if booking.caterer.maya_number %}
                    <div class="method-card" onclick="selectManagePayment('Maya')" id="mc-Maya" style="border: 2px solid #e2e8f0; border-radius: 12px; padding: 1rem; text-align: center; cursor: pointer; transition: 0.2s;">
                        <i class="fas fa-wallet text-gray-800" style="font-size: 1.5rem; margin-bottom: 0.5rem;"></i><br>Maya
                    </div>
                    {% endif %}
                    {% if booking.caterer.bank_account_number %}
                    <div class="method-card" onclick="selectManagePayment('Bank')" id="mc-Bank" style="border: 2px solid #e2e8f0; border-radius: 12px; padding: 1rem; text-align: center; cursor: pointer; transition: 0.2s;">
                        <i class="fas fa-university text-blue-700" style="font-size: 1.5rem; margin-bottom: 0.5rem;"></i><br>Bank
                    </div>
                    {% endif %}
                </div>

                <div id="manageUploadSection" style="display: none;">
                    <div id="manage-instr-GCash" style="display: none; background: #eff6ff; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                        <strong>GCash:</strong> Send to {{ booking.caterer.gcash_number }}
                    </div>
                    <div id="manage-instr-Maya" style="display: none; background: #f0fdf4; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                        <strong>Maya:</strong> Send to {{ booking.caterer.maya_number }}
                    </div>
                    <div id="manage-instr-Bank" style="display: none; background: #fefce8; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                        <strong>Bank:</strong> {{ booking.caterer.bank_name }} - {{ booking.caterer.bank_account_name }} ({{ booking.caterer.bank_account_number }})
                    </div>

                    <div style="border: 2px dashed #cbd5e1; border-radius: 12px; padding: 2rem; text-align: center; cursor: pointer; background: #f8fafc;" onclick="document.getElementById('manageProofInput').click()">
                        <i class="fas fa-cloud-upload-alt text-3xl text-gray-400 mb-2"></i>
                        <div style="font-weight: 600;">Click to upload receipt</div>
                        <input type="file" id="manageProofInput" accept="image/*" style="display: none;" onchange="previewManageFile(this)">
                        <img id="managePreview" style="max-width: 100%; max-height: 200px; margin-top: 1rem; display: none; border-radius: 8px; margin-left: auto; margin-right: auto;">
                    </div>
                    
                    <div id="manageUploadError" style="display: none; color: #ef4444; font-size: 0.9rem; margin-top: 1rem; background: #fef2f2; padding: 1rem; border-radius: 8px; border: 1px solid #fca5a5;"></div>

                    <button type="button" class="btn-action btn-primary" id="manageSubmitBtn" onclick="submitManagePayment()" style="margin-top: 1.5rem; width: 100%;" disabled>
                        Upload & Verify Receipt
                    </button>
                </div>
            </div>
            {% endif %}
            {% endif %}
"""

if "Complete Your Payment" not in content:
    content = content.replace("<!-- Actions -->", payment_ui_html + "\n            <!-- Actions -->")

js_script = """
<script>
    let selectedManageMethod = '';
    
    function selectManagePayment(method) {
        selectedManageMethod = method;
        document.querySelectorAll('.method-card').forEach(c => {
            c.style.borderColor = '#e2e8f0';
            c.style.background = 'white';
        });
        document.getElementById('mc-' + method).style.borderColor = 'var(--primary)';
        document.getElementById('mc-' + method).style.background = '#fff2ee';
        
        document.getElementById('manageUploadSection').style.display = 'block';
        document.getElementById('manage-instr-GCash').style.display = 'none';
        document.getElementById('manage-instr-Maya').style.display = 'none';
        document.getElementById('manage-instr-Bank').style.display = 'none';
        document.getElementById('manage-instr-' + method).style.display = 'block';
    }

    function previewManageFile(input) {
        const preview = document.getElementById('managePreview');
        const file = input.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = e => {
                preview.src = e.target.result;
                preview.style.display = 'block';
                document.getElementById('manageSubmitBtn').disabled = false;
            }
            reader.readAsDataURL(file);
        }
    }

    async function submitManagePayment() {
        const fileInput = document.getElementById('manageProofInput');
        if (!fileInput.files.length) return;
        
        const btn = document.getElementById('manageSubmitBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Validating Receipt with AI...';
        
        const errBox = document.getElementById('manageUploadError');
        errBox.style.display = 'none';
        
        const formData = new FormData();
        formData.append('payment_method', selectedManageMethod);
        formData.append('proof_image', fileInput.files[0]);
        
        try {
            const res = await fetch('/bookings/alacarte/payment/{{ booking.id }}', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            
            if (data.success) {
                window.location.reload();
            } else {
                errBox.style.display = 'block';
                errBox.innerHTML = '<i class="fas fa-robot"></i> AI Detection Failed: ' + data.message;
                btn.disabled = false;
                btn.innerHTML = 'Upload & Verify Receipt';
            }
        } catch (e) {
            errBox.style.display = 'block';
            errBox.innerHTML = 'Network error occurred.';
            btn.disabled = false;
            btn.innerHTML = 'Upload & Verify Receipt';
        }
    }

    function deleteDraft(bookingId) {
"""

if "function selectManagePayment" not in content:
    content = content.replace("function deleteDraft(bookingId) {", js_script)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patched food_order_manage.html")
