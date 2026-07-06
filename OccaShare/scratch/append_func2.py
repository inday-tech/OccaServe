import codecs

func = """
window.toggleAllInContainer = function(checkbox, containerSelector) {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    
    const cards = container.querySelectorAll('.menu-select-card');
    cards.forEach(card => {
        const cb = card.querySelector('input[type="checkbox"]');
        if (!cb) return;
        
        // If the card's state doesn't match the master checkbox state, toggle it
        if (cb.checked !== checkbox.checked) {
            // Trigger the card click programmatically so it updates the UI too
            card.click();
        }
    });
};
"""

with codecs.open('c:\\OccaServe\\OccaShare\\app\\static\\js\\caterer\\packages.js', 'a', 'utf-8') as f:
    f.write(func)

print("Appended toggleAllInContainer!")
