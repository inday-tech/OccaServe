// Universal Pagination Script for Admin Panel
// Automatically paginates elements with class .auto-paginate
document.addEventListener('DOMContentLoaded', function() {
    const paginatedElements = document.querySelectorAll('.auto-paginate');
    
    paginatedElements.forEach((el, index) => {
        const rowsPerPage = 5;
        let currentPage = 1;
        
        let items = [];
        if (el.tagName === 'TBODY') {
            items = Array.from(el.querySelectorAll('tr'));
        } else {
            items = Array.from(el.children);
        }
        
        if (items.length <= rowsPerPage) return; // No pagination needed
        
        const paginationBox = document.createElement('div');
        paginationBox.className = 'pagination-box';
        paginationBox.style.marginTop = '1.5rem';
        
        const infoDiv = document.createElement('div');
        infoDiv.className = 'pagination-info';
        
        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'pagination-controls';
        
        paginationBox.appendChild(infoDiv);
        paginationBox.appendChild(controlsDiv);
        
        // Insert after the element's container (account for responsiveness divs)
        let wrapper = el.closest('table');
        if (wrapper && wrapper.parentElement.style.overflowX) {
            wrapper = wrapper.parentElement;
        } else if (!wrapper) {
            wrapper = el;
        }
        
        wrapper.parentNode.insertBefore(paginationBox, wrapper.nextSibling);
        
        function render() {
            const start = (currentPage - 1) * rowsPerPage;
            const end = start + rowsPerPage;
            
            items.forEach((item, i) => {
                item.style.display = (i >= start && i < end) ? '' : 'none';
            });
            
            const totalPages = Math.ceil(items.length / rowsPerPage);
            controlsDiv.innerHTML = '';
            
            const prevBtn = document.createElement('button');
            prevBtn.className = 'page-btn';
            prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
            prevBtn.disabled = currentPage === 1;
            prevBtn.onclick = () => { currentPage--; render(); };
            controlsDiv.appendChild(prevBtn);
            
            for (let i = 1; i <= totalPages; i++) {
                if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
                    const btn = document.createElement('button');
                    btn.className = `page-btn ${i === currentPage ? 'active' : ''}`;
                    btn.innerText = i;
                    btn.onclick = () => { currentPage = i; render(); };
                    controlsDiv.appendChild(btn);
                } else if (i === currentPage - 2 || i === currentPage + 2) {
                    const dots = document.createElement('span');
                    dots.innerText = '...';
                    dots.style.padding = '0 0.25rem';
                    dots.style.color = '#64748b';
                    controlsDiv.appendChild(dots);
                }
            }
            
            const nextBtn = document.createElement('button');
            nextBtn.className = 'page-btn';
            nextBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
            nextBtn.disabled = currentPage === totalPages;
            nextBtn.onclick = () => { currentPage++; render(); };
            controlsDiv.appendChild(nextBtn);
            
            const actualStart = items.length === 0 ? 0 : start + 1;
            const actualEnd = Math.min(currentPage * rowsPerPage, items.length);
            infoDiv.innerText = `Showing ${actualStart} to ${actualEnd} of ${items.length} entries`;
        }
        
        render();
    });
});
