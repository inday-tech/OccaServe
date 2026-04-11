document.addEventListener('DOMContentLoaded', function () {
    const photoInput = document.getElementById('photoInput');
    const photoForm = document.getElementById('photoForm');

    if (photoInput && photoForm) {
        photoInput.addEventListener('change', function () {
            if (this.files && this.files[0]) {
                photoForm.submit();
            }
        });
    }
});
