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

    if (options.type === 'confirm') {
        Swal.fire({
            title: options.title || 'Are you sure?',
            html: options.message || '',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: 'var(--primary-color, #800000)',
            cancelButtonColor: '#64748b',
            confirmButtonText: options.confirmText || 'Confirm',
            cancelButtonText: options.cancelText || 'Cancel'
        }).then((result) => {
            if (result.isConfirmed) {
                if (options.onConfirm) options.onConfirm();
            } else {
                if (options.onCancel) options.onCancel();
            }
        });
        return;
    }

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
    if (!window.Swal) return;
    Swal.fire({
        title: title,
        text: message,
        input: 'text',
        inputPlaceholder: placeholder,
        showCancelButton: true,
        confirmButtonColor: 'var(--primary-color, #800000)',
        cancelButtonColor: '#64748b',
        confirmButtonText: 'Submit'
    }).then((result) => {
        if (result.isConfirmed && result.value) {
            if (onConfirm) onConfirm(result.value);
        }
    });
};
