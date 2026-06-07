import os

js_files = {
    'app/static/js/caterer/layout.js': {
        'start': '// ─── Inactivity Auto-Logout',
        'end': '// ─── Sidebar Scroll Persistence',
        'replacement': """    // ─── Inactivity Auto-Logout ──────────────────────────────────────────────
    const LIMIT = 15 * 60 * 1000; // 15 mins total
    const WARN = 60 * 1000;       // 1 min countdown
    let idle, countdown;
    
    function initInactivityTimer() {
        const reset = () => {
            clearTimeout(idle); clearInterval(countdown);
            const m = document.getElementById('inactivityModal');
            if (m) {
                m.classList.remove('active');
                setTimeout(() => { if (!m.classList.contains('active')) m.style.display = 'none'; }, 400);
            }
            idle = setTimeout(warn, LIMIT - WARN);
        };

        const warn = () => {
            const m = document.getElementById('inactivityModal');
            if (m) {
                m.style.display = 'flex';
                // Trigger reflow to animate
                requestAnimationFrame(() => requestAnimationFrame(() => m.classList.add('active')));
            }
            let s = 60;
            const cdEl = document.getElementById('inactivityCountdown');
            if(cdEl) cdEl.innerText = s;
            
            countdown = setInterval(() => { 
                s--;
                if(cdEl) cdEl.innerText = s;
                if (s <= 0) { 
                    clearInterval(countdown); 
                    window.location.href = '/auth/logout?reason=inactivity'; 
                } 
            }, 1000);
        };

        const activityEvents = ['mousedown','mousemove','keypress','scroll','touchstart','click'];
        activityEvents.forEach(ev => document.addEventListener(ev, reset, { passive: true }));
        const stayBtn = document.getElementById('stayLoggedInBtn');
        if(stayBtn) stayBtn.addEventListener('click', reset);
        reset();
    }
    initInactivityTimer();

    """
    },
    'app/static/js/admin/layout.js': {
        'start': '// ─── Inactivity Auto-Logout',
        'end': '// Close on outside click',
        'replacement': """    // ─── Inactivity Auto-Logout ───────────────────────────────────────────────
    const LIMIT = 15 * 60 * 1000;
    const WARN = 60 * 1000;
    let idle, countdown;
    
    function initInactivityTimer() {
        const reset = () => {
            clearTimeout(idle); clearInterval(countdown);
            const m = document.getElementById('inactivityModal');
            if (m) {
                m.classList.remove('active');
                setTimeout(() => { if (!m.classList.contains('active')) m.style.display = 'none'; }, 400);
            }
            idle = setTimeout(warn, LIMIT - WARN);
        };

        const warn = () => {
            const m = document.getElementById('inactivityModal');
            if (m) {
                m.style.display = 'flex';
                requestAnimationFrame(() => requestAnimationFrame(() => m.classList.add('active')));
            }
            let s = 60;
            const cdEl = document.getElementById('inactivityCountdown');
            if(cdEl) cdEl.innerText = s;
            
            countdown = setInterval(() => { 
                s--;
                if(cdEl) cdEl.innerText = s;
                if (s <= 0) { 
                    clearInterval(countdown); 
                    window.location.href = '/auth/logout?reason=inactivity'; 
                } 
            }, 1000);
        };

        ['mousedown','mousemove','keypress','scroll','touchstart','click'].forEach(ev => document.addEventListener(ev, reset, { passive: true }));
        const stayBtn = document.getElementById('stayLoggedInBtn');
        if(stayBtn) stayBtn.addEventListener('click', reset);
        reset();
    }
    initInactivityTimer();

    """
    },
    'app/static/js/customer/layout.js': {
        'start': '// ─── Inactivity Auto-Logout',
        'end': '/* ============================================================',
        'replacement': """// ─── Inactivity Auto-Logout ──────────────────────────────────────────────
function initInactivityTimer() {
    const LIMIT = 15 * 60 * 1000;
    const WARN = 60 * 1000;
    let idle, countdown;

    const reset = () => {
        clearTimeout(idle); clearInterval(countdown);
        const m = document.getElementById('inactivityModal');
        if (m) {
            m.classList.remove('active');
            setTimeout(() => { if (!m.classList.contains('active')) m.style.display = 'none'; }, 400);
        }
        idle = setTimeout(warn, LIMIT - WARN);
    };

    const warn = () => {
        const m = document.getElementById('inactivityModal');
        if (m) {
            m.style.display = 'flex';
            requestAnimationFrame(() => requestAnimationFrame(() => m.classList.add('active')));
        }
        let s = 60;
        const cdEl = document.getElementById('inactivityCountdown');
        if(cdEl) cdEl.innerText = s;
        
        countdown = setInterval(() => { 
            s--;
            if(cdEl) cdEl.innerText = s;
            if (s <= 0) { 
                clearInterval(countdown); 
                window.location.href = '/auth/logout?reason=inactivity'; 
            } 
        }, 1000);
    };

    ['mousedown','mousemove','keypress','scroll','touchstart','click'].forEach(ev => document.addEventListener(ev, reset, { passive: true }));
    const stayBtn = document.getElementById('stayLoggedInBtn');
    if(stayBtn) stayBtn.addEventListener('click', reset);
    reset();
}

"""
    }
}

for path, info in js_files.items():
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        start_idx = content.find(info['start'])
        end_idx = content.find(info['end'])
        
        if start_idx != -1 and end_idx != -1:
            new_content = content[:start_idx] + info['replacement'] + content[end_idx:]
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Patched {path}")
        else:
            print(f"Could not find markers in {path}")
