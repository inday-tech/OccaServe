/**
 * Premium Alert System (Using SweetAlert2)
 * Globally accessible via window.showAlert(), window.showSuccess(), window.showError()
 */

window.showAlert = (options) => {
    if (!window.Swal) {
        console.error("SweetAlert2 is not loaded!");
        alert(options.message);
        return;
    }

window.showStandardConfirm = function(options) {
    return new Promise((resolve) => {
        const modal = document.getElementById('globalConfirmModal');
        if (!modal) {
            console.error('globalConfirmModal not found, falling back to Swal');
            if (window.Swal) return Swal.fire(options).then(resolve);
            resolve({ isConfirmed: confirm(options.text || options.message) });
            return;
        }

        // Configure Modal UI
        document.getElementById('gcmTitle').innerText = options.title || 'Confirm Action';
        document.getElementById('gcmSubtitle').innerText = options.subtitle || 'Confirming request.';
        
        const messageEl = document.getElementById('gcmMessage');
        if (options.html) messageEl.innerHTML = options.html;
        else messageEl.innerText = options.text || options.message || 'Are you sure?';

        // Input Box
        const inputContainer = document.getElementById('gcmInputContainer');
        const inputEl = document.getElementById('gcmInput');
        if (options.input === 'text') {
            inputContainer.style.display = 'block';
            document.getElementById('gcmInputLabel').innerText = options.text || options.message || 'Enter value:';
            inputEl.placeholder = options.inputPlaceholder || '';
            inputEl.value = '';
            setTimeout(() => inputEl.focus(), 100);
        } else {
            inputContainer.style.display = 'none';
        }

        const hintEl = document.getElementById('gcmHint');
        if (options.hint) {
            hintEl.innerText = options.hint;
            hintEl.style.display = 'block';
        } else {
            hintEl.style.display = 'none';
        }

        // Styling based on icon/type
        const header = document.getElementById('gcmHeader');
        const icon = document.getElementById('gcmIcon');
        const confirmBtn = document.getElementById('gcmConfirmBtn');
        const alertBox = document.getElementById('gcmAlertBox');
        
        const type = options.icon || 'warning';
        if (type === 'error' || type === 'danger') {
            header.style.background = '#ef4444';
            icon.style.color = '#ef4444';
            icon.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
            confirmBtn.style.background = '#0f172a';
            confirmBtn.style.borderColor = '#0f172a';
            alertBox.style.background = '#fef2f2';
            alertBox.style.borderColor = '#fecaca';
        } else if (type === 'warning') {
            header.style.background = '#f59e0b';
            icon.style.color = '#f59e0b';
            icon.innerHTML = '<i class="fas fa-exclamation-circle"></i>';
            confirmBtn.style.background = '#0f172a';
            confirmBtn.style.borderColor = '#0f172a';
            alertBox.style.background = '#fffbeb';
            alertBox.style.borderColor = '#fde68a';
        } else {
            header.style.background = 'var(--primary-color)';
            icon.style.color = 'var(--primary-color)';
            icon.innerHTML = '<i class="fas fa-info-circle"></i>';
            confirmBtn.style.background = 'var(--primary-color)';
            confirmBtn.style.borderColor = 'var(--primary-color)';
            alertBox.style.background = '#f8fafc';
            alertBox.style.borderColor = '#e2e8f0';
        }

        confirmBtn.innerText = options.confirmButtonText || 'Confirm';
        document.getElementById('gcmCancelBtn').innerText = options.cancelButtonText || 'Cancel';

        // Bind events
        const handleConfirm = () => {
            cleanup();
            resolve({ isConfirmed: true, value: options.input === 'text' ? inputEl.value : null });
        };
        const handleCancel = () => {
            cleanup();
            resolve({ isConfirmed: false });
        };

        const cleanup = () => {
            modal.style.display = 'none';
            confirmBtn.removeEventListener('click', handleConfirm);
            document.getElementById('gcmCancelBtn').removeEventListener('click', handleCancel);
            const closeBtn = modal.querySelector('.occ-modal-close');
            if (closeBtn) closeBtn.removeEventListener('click', handleCancel);
        };

        confirmBtn.addEventListener('click', handleConfirm);
        document.getElementById('gcmCancelBtn').addEventListener('click', handleCancel);
        const closeBtn = modal.querySelector('.occ-modal-close');
        if (closeBtn) closeBtn.addEventListener('click', handleCancel);

        modal.style.display = 'flex';
    });
};

window.showAlert = (options) => {
    if (options.type === 'confirm') {
        window.showStandardConfirm({
            title: options.title,
            html: options.message,
            icon: 'warning',
            confirmButtonText: options.confirmText,
            cancelButtonText: options.cancelText
        }).then(res => {
            if (res.isConfirmed && options.onConfirm) options.onConfirm();
            else if (!res.isConfirmed && options.onCancel) options.onCancel();
        });
        return;
    }

    if (!window.Swal) return;

    const Toast = Swal.mixin({
        toast: true,
        position: 'bottom-end',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true,
        didOpen: (toast) => {
            toast.onmouseenter = Swal.stopTimer;
            toast.onmouseleave = Swal.resumeTimer;
        }
    });

    Toast.fire({
        icon: options.type || 'success',
        title: options.message || options.title
    });
};

window.showSuccess = (message, title = "Success!") => {
    if (!window.Swal) return alert(message);
    const Toast = Swal.mixin({
        toast: true,
        position: 'bottom-end',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true,
        didOpen: (toast) => {
            toast.onmouseenter = Swal.stopTimer;
            toast.onmouseleave = Swal.resumeTimer;
        }
    });
    Toast.fire({
        icon: 'success',
        title: message
    });
};

window.showError = (message, title = "Oops!") => {
    if (!window.Swal) return alert(message);
    const Toast = Swal.mixin({
        toast: true,
        position: 'bottom-end',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true,
        didOpen: (toast) => {
            toast.onmouseenter = Swal.stopTimer;
            toast.onmouseleave = Swal.resumeTimer;
        }
    });
    Toast.fire({
        icon: 'error',
        title: message
    });
};

window.showPrompt = (message, onConfirm, title = "Input Required", placeholder = "Enter details...") => {
    window.showStandardConfirm({
        title: title,
        html: message,
        input: 'text',
        inputPlaceholder: placeholder,
        icon: 'warning',
        confirmButtonText: 'Submit'
    }).then(res => {
        if (res.isConfirmed && res.value) {
            if (onConfirm) onConfirm(res.value);
        }
    });
};
