import os

path = 'app/static/js/customer/layout.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('/* ============================================================')
# we need the index of 'INACTIVITY TIMER'
start_idx = content.find('INACTIVITY TIMER')
if start_idx != -1 and start != -1:
    # go back to the start of the comment
    start_idx = content.rfind('/*', 0, start_idx)
    
    replacement = """/* ============================================================
   INACTIVITY TIMER
   ============================================================ */
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
    new_content = content[:start_idx] + replacement + content[start:]
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Patched customer/layout.js")
