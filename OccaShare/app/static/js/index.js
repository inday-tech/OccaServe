(function () {
    const categoryCards = document.querySelectorAll('.category-card');
    const catererCards = document.querySelectorAll('.caterer-card');
    const othersInput = document.getElementById('othersInput');
    const othersBtn = document.getElementById('othersFilterBtn');

    function filterCaterers(filterValue, isSearch = false) {
        catererCards.forEach(card => {
            if (isSearch) {
                const name = (card.dataset.name || '').toLowerCase();
                const desc = (card.dataset.description || '').toLowerCase();
                if (name.includes(filterValue) || desc.includes(filterValue)) {
                    card.classList.remove('hidden');
                } else {
                    card.classList.add('hidden');
                }
            } else {
                if (filterValue === 'all') {
                    card.classList.remove('hidden');
                } else {
                    const categories = (card.dataset.category || '').toLowerCase().split(',').map(s => s.trim());
                    if (categories.includes(filterValue.toLowerCase())) {
                        card.classList.remove('hidden');
                    } else {
                        card.classList.add('hidden');
                    }
                }
            }
        });
    }

    function setActiveCategory(activeCard) {
        categoryCards.forEach(card => card.classList.remove('active-category'));
        if (activeCard) activeCard.classList.add('active-category');
    }

    categoryCards.forEach(card => {
        card.addEventListener('click', function () {
            const filter = this.dataset.filter;
            setActiveCategory(this);
            filterCaterers(filter, false);
            if (othersInput) othersInput.value = '';
        });
    });

    if (othersBtn && othersInput) {
        othersBtn.addEventListener('click', function () {
            const searchTerm = othersInput.value.trim().toLowerCase();
            if (searchTerm === '') {
                const allCard = document.querySelector('.category-card[data-filter="all"]');
                if (allCard) {
                    setActiveCategory(allCard);
                    filterCaterers('all', false);
                }
            } else {
                setActiveCategory(null);
                filterCaterers(searchTerm, true);
            }
        });

        othersInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                othersBtn.click();
            }
        });
    }

    const allCard = document.querySelector('.category-card[data-filter="all"]');
    if (allCard && !allCard.classList.contains('active-category')) {
        allCard.classList.add('active-category');
    }
})();
