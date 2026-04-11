/* 
   OccaServe - Dashboard Interactivity
*/

document.addEventListener('DOMContentLoaded', function() {
    console.log('Customer Dashboard Loaded');

    // Add subtle entrance animations to cards
    const cards = document.querySelectorAll('.stat-card, .next-event-card, .quick-actions-card, .activity-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
        
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 100 * index);
    });

    // Stats Click Interactions (Filtering Table)
    const statCards = document.querySelectorAll('.stat-card');
    const tableRows = document.querySelectorAll('.activity-row');

    statCards.forEach(card => {
        card.addEventListener('click', () => {
            const label = card.querySelector('.stat-label').textContent.toLowerCase();
            
            // Simple filter logic example
            if (label.includes('upcoming')) {
                filterTable('pending'); // Just an example, mapping labels to status
            } else {
                showAllRows();
            }
        });
    });

    function filterTable(status) {
        tableRows.forEach(row => {
            const rowStatus = row.querySelector('.status-badge').textContent.toLowerCase();
            if (rowStatus.includes(status)) {
                row.style.display = 'table-row';
            } else {
                row.style.display = 'none';
            }
        });
    }

    function showAllRows() {
        tableRows.forEach(row => {
            row.style.display = 'table-row';
        });
    }
});
