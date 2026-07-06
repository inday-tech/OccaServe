import codecs

func = """
window.toggleLibItemSelectCard = function(card, id) {
    const cb = card.querySelector('input[type="checkbox"]');
    if (!cb) return;
    cb.checked = !cb.checked;

    if (cb.checked) {
        card.classList.add('selected');
        card.style.background = '#f0fdf4';
        card.style.borderColor = 'var(--primary-color)';
        const i = card.querySelector('div[style*="absolute"] i');
        if (i) {
            i.className = 'fas fa-check-circle';
            i.parentElement.style.color = 'var(--primary-color)';
        }
    } else {
        card.classList.remove('selected');
        card.style.background = 'white';
        card.style.borderColor = '#e2e8f0';
        const i = card.querySelector('div[style*="absolute"] i');
        if (i) {
            i.className = 'far fa-circle';
            i.parentElement.style.color = '#cbd5e1';
        }
    }

    // Only update rules if in menu tab
    if (card.closest('#tab-menu')) {
        if (typeof updateSelectionRulesBuilder === 'function') {
            updateSelectionRulesBuilder();
        }
    }
};
"""

with codecs.open('c:\\OccaServe\\OccaShare\\app\\static\\js\\caterer\\packages.js', 'a', 'utf-8') as f:
    f.write(func)

print("Appended!")
