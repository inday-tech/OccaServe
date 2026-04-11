document.addEventListener('DOMContentLoaded', function () {
    const idLine = document.getElementById('idLine');
    const idScanner = document.getElementById('idScanner');
    const idStatus = document.getElementById('idStatus');

    const faceLine = document.getElementById('faceLine');
    const faceScanner = document.getElementById('faceScanner');
    const faceStatus = document.getElementById('faceStatus');

    window.handleIDUpload = function (input) {
        if (input.files && input.files[0] && idLine && idScanner && idStatus) {
            idLine.style.display = 'block';
            idScanner.classList.add('active');
            idStatus.innerHTML = '<i class="fas fa-check-circle" style="font-size: 3rem; color: #10b981; margin-bottom: 1rem;"></i><h4 style="color: #166534">ID Uploaded</h4>';
            setTimeout(() => {
                idLine.style.display = 'none';
                idScanner.classList.add('completed');
            }, 2000);
        }
    };

    window.handleFaceUpload = function (input) {
        if (input.files && input.files[0] && faceLine && faceScanner && faceStatus) {
            faceLine.style.display = 'block';
            faceScanner.classList.add('active');
            faceStatus.innerHTML = '<i class="fas fa-check-circle" style="font-size: 3rem; color: #10b981; margin-bottom: 1rem;"></i><h4 style="font-size: 0.9rem; color: #166534">Face Captured</h4>';
            setTimeout(() => {
                faceLine.style.display = 'none';
                faceScanner.classList.add('completed');
            }, 2000);
        }
    };

    const verifyForm = document.getElementById('verifyForm');
    const btnText = document.getElementById('btnText');
    const verifyBtn = document.getElementById('verifyBtn');

    if (verifyForm && btnText && verifyBtn) {
        verifyForm.onsubmit = function () {
            btnText.innerText = 'Processing Data...';
            verifyBtn.disabled = true;
            verifyBtn.style.opacity = '0.7';
            return true;
        };
    }
});
