/**
 * Premium Alert Modal System (Customer - Diamond Standard)
 * Globally accessible via window.showAlert()
 */

const PremiumAlert = {
    overlay: null,
    container: null,
    titleEL: null,
    messageEL: null,
    iconEL: null,
    actionsEL: null,

    init() {
        if (this.overlay) return;

        // HTML Structure
        const html = `
            <div id="premiumAlertOverlay" class="premium-modal-overlay">
                <div class="premium-modal-container" id="premiumAlertContainer">
                    <div class="modal-icon-wrapper">
                        <i id="premiumModalIcon" class="fas fa-check"></i>
                    </div>
                    <h2 class="modal-title" id="premiumModalTitle">Success!</h2>
                    <p class="modal-message" id="premiumModalMessage">Your action has been completed.</p>
                    <div id="modalInputWrapper" style="display: none; margin-bottom: 2rem;">
                        <input type="text" id="modalPromptInput" class="form-control" style="width: 100%; padding: 0.8rem; border-radius: 0.85rem; border: 1px solid #e2e8f0; font-family: inherit;">
                    </div>
                    <div class="modal-actions" id="premiumModalActions">
                        <button class="modal-btn btn-confirm-main" id="premiumModalConfirmBtn">Got it</button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', html);
        this.overlay = document.getElementById('premiumAlertOverlay');
        this.container = document.getElementById('premiumAlertContainer');
        this.titleEL = document.getElementById('premiumModalTitle');
        this.messageEL = document.getElementById('premiumModalMessage');
        this.iconEL = document.getElementById('premiumModalIcon');
        this.actionsEL = document.getElementById('premiumModalActions');

        // Close on overlay click (if not mandatory)
        this.overlay.onclick = (e) => {
            if (e.target === this.overlay && !this.overlay.dataset.mandatory) {
                this.hide();
            }
        };
    },

    show({
        title = "Alert",
        message = "",
        type = "success", // success, error, warning, confirm
        confirmText = "Got it",
        cancelText = "Cancel",
        onConfirm = null,
        onCancel = null,
        mandatory = false
    }) {
        this.init();

        // Setup Content
        this.titleEL.innerText = title;
        this.messageEL.innerHTML = message;
        this.container.className = `premium-modal-container modal-type-${type}`;
        this.overlay.dataset.mandatory = mandatory ? "true" : "";

        // Icon Setup
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-times-circle',
            warning: 'fa-exclamation-triangle',
            confirm: 'fa-question-circle'
        };
        this.iconEL.className = `fas ${icons[type] || icons.success}`;

        // Actions Setup
        this.actionsEL.innerHTML = '';
        
        if (type === 'confirm' || onCancel) {
            const cancelBtn = document.createElement('button');
            cancelBtn.className = 'modal-btn btn-cancel-secondary';
            cancelBtn.innerText = cancelText || "Cancel";
            cancelBtn.onclick = () => {
                this.hide();
                if (onCancel) onCancel();
            };
            this.actionsEL.appendChild(cancelBtn);
        }

        const confirmBtn = document.createElement('button');
        confirmBtn.className = 'modal-btn btn-confirm-main';
        confirmBtn.innerText = confirmText || (type === 'confirm' ? "Confirm" : "Got it");
        confirmBtn.onclick = () => {
            this.hide();
            if (onConfirm) onConfirm();
        };
        this.actionsEL.appendChild(confirmBtn);

        // Show
        this.overlay.style.display = 'flex';
        setTimeout(() => this.overlay.classList.add('active'), 10);
    },

    hide() {
        if (!this.overlay) return;
        this.overlay.classList.remove('active');
        setTimeout(() => {
            if (!this.overlay.classList.contains('active')) {
                this.overlay.style.display = 'none';
            }
        }, 300);
    }
};

// Global shorthand
window.PremiumAlert = PremiumAlert;
window.showAlert = (options) => PremiumAlert.show(options);
window.showSuccess = (message, title = "Success!") => window.showAlert({ type: 'success', title, message });
window.showError = (message, title = "Oops!") => window.showAlert({ type: 'error', title, message });
