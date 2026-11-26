document.addEventListener('DOMContentLoaded', function () {
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function (e) {
            const pass = document.getElementById('password')?.value;
            const confirm = document.getElementById('confirm_password')?.value;
            if (pass !== confirm) {
                e.preventDefault();
                if (window.Swal) {
                    Swal.fire({
                        icon: 'error',
                        title: 'Passwords Do Not Match',
                        text: 'Please make sure both password fields match.',
                        confirmButtonColor: '#FF7B54'
                    });
                } else {
                    alert("Passwords do not match!");
                }
            }
        });
    }
});
