with open('app/static/js/global/dynamic_landing.js', 'a', encoding='utf-8') as f:
    f.write('''

window.triggerGeolocation = function() {
    const btn = document.getElementById('locateMeBtn');
    if ('geolocation' in navigator) {
        if (btn) btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        navigator.geolocation.getCurrentPosition(function(position) {
            sessionStorage.setItem('user_lat', position.coords.latitude);
            sessionStorage.setItem('user_lon', position.coords.longitude);
            if (btn) {
                btn.innerHTML = '<i class="fas fa-location-crosshairs"></i>';
                btn.style.color = '#f97316';
                btn.style.borderColor = '#f97316';
                btn.style.backgroundColor = '#fff7ed';
            }
            if (window.performUnifiedSearch) {
                window.performUnifiedSearch();
            }
        }, function(error) {
            if (btn) btn.innerHTML = '<i class="fas fa-location-crosshairs"></i>';
            if (typeof Swal !== 'undefined') Swal.fire('Location Access Denied', 'Please allow location permissions to find nearby caterers.', 'warning');
            else alert('Location Access Denied. Please allow location permissions to find nearby caterers.');
        }, { timeout: 10000 });
    } else {
        alert('Geolocation is not supported by your browser.');
    }
};
''')
