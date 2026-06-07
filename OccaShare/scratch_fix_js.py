with open(r'c:\OccaServe\OccaShare\app\static\js\caterer\profile_edit.js', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines()
new_lines = lines[:477]  # Everything up to line 477 (index 477 is line 478)

new_content = '\n'.join(new_lines) + '''
// Gallery Archive Function
async function archiveGalleryItem(itemId) {
    if (!confirm('Archive this photo?')) return;
    try {
        const response = await fetch(`/caterer/gallery/${itemId}/archive`, { method: 'POST' });
        if (response.ok) {
            const btn = document.querySelector(`button[onclick="archiveGalleryItem(${itemId})"]`);
            const item = btn?.closest('.gallery-item-wrapper');
            if (item) {
                item.style.opacity = '0';
                item.style.transform = 'scale(0.8)';
                setTimeout(() => item.remove(), 300);
            }
            if (window.showSuccess) window.showSuccess('Photo archived successfully.');
        }
    } catch (err) { console.error(err); }
}

// Notification Preferences
async function saveNotificationPrefs() {
    const btn = document.getElementById('saveNotifsBtn');
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    btn.disabled = true;

    const prefs = {};
    document.querySelectorAll('#notifPrefsList input[data-pref]').forEach(input => {
        prefs[input.dataset.pref] = input.checked;
    });

    try {
        const response = await fetch('/caterer/settings/notifications', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(prefs)
        });
        const result = await response.json();
        if (result.status === 'success') {
            if (window.showSuccess) window.showSuccess('Notification preferences saved!');
        } else {
            if (window.showError) window.showError(result.message || 'Failed to save.');
        }
    } catch (err) {
        console.error(err);
        if (window.showError) window.showError('An error occurred. Please try again.');
    } finally {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    }
}

// Account Deactivation
async function handleDeactivate() {
    if (typeof Swal !== "undefined") {
        const result = await Swal.fire({
            title: "Deactivate Account?",
            text: "Your profile will be hidden from customers. Are you sure?",
            icon: "warning",
            showCancelButton: true,
            confirmButtonColor: "#f39c12",
            cancelButtonColor: "#3085d6",
            confirmButtonText: "Yes, deactivate it!"
        });
        if (!result.isConfirmed) return;
    } else {
        if (!confirm("Are you sure you want to deactivate your account? Your profile will be hidden from customers.")) return;
    }
    try {
        const res = await window.apiAction("/caterer/settings/deactivate", { method: "POST" });
        if (res) setTimeout(() => window.location.href = "/login", 1500);
    } catch (e) {}
}

async function handleReactivate() {
    if (typeof Swal !== "undefined") {
        const result = await Swal.fire({
            title: "Reactivate Account?",
            text: "Your profile will be visible to customers again.",
            icon: "info",
            showCancelButton: true,
            confirmButtonColor: "#2ecc71",
            cancelButtonColor: "#3085d6",
            confirmButtonText: "Yes, reactivate it!"
        });
        if (!result.isConfirmed) return;
    } else {
        if (!confirm("Are you sure you want to reactivate your account? Your profile will be visible again.")) return;
    }
    try {
        const res = await window.apiAction("/caterer/settings/reactivate", { method: "POST" });
        if (res) setTimeout(() => window.location.reload(), 1500);
    } catch (e) {}
}

async function handleDeleteRequest() {
    if (typeof Swal !== "undefined") {
        const result = await Swal.fire({
            title: "PERMANENTLY DELETE ACCOUNT?",
            text: "WARNING: All data, dishes, and history will be lost. This cannot be undone!",
            icon: "error",
            showCancelButton: true,
            confirmButtonColor: "#d33",
            cancelButtonColor: "#3085d6",
            confirmButtonText: "Yes, delete my account forever!"
        });
        if (!result.isConfirmed) return;
    } else {
        if (!confirm("WARNING: Are you absolutely sure you want to PERMANENTLY delete your account? All data, dishes, and history will be lost. This cannot be undone.")) return;
    }
    try {
        const res = await window.apiAction("/caterer/settings/delete", { method: "POST" });
        if (res) setTimeout(() => window.location.href = "/login", 2000);
    } catch (e) {}
}

// Reset Brand to Defaults
async function resetBrandDefaults() {
    if (!window.showStandardConfirm) return;

    const { isConfirmed } = await window.showStandardConfirm({
        title: 'Reset Brand Settings?',
        message: 'This will clear all your custom colors, fonts, textures, and decorations, reverting to OccaServe defaults.',
        icon: 'warning',
        confirmButtonText: 'Yes, reset to defaults'
    });

    if (!isConfirmed) return;

    try {
        const response = await fetch('/caterer/settings/reset-brand', { method: 'POST' });
        const resJson = await response.json();
        if (resJson.status === 'success') {
            if (window.showSuccess) window.showSuccess('Brand settings reset! Reloading page...');
            setTimeout(() => window.location.reload(), 1500);
        } else {
            if (window.showError) window.showError(resJson.message || 'Failed to reset.');
        }
    } catch (err) {
        console.error(err);
        if (window.showError) window.showError('An error occurred.');
    }
}
'''

with open(r'c:\OccaServe\OccaShare\app\static\js\caterer\profile_edit.js', 'w', encoding='utf-8') as f:
    f.write(new_content)
