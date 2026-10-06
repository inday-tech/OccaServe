/**
 * OccaServe Caterer Payments & Earnings — Clean, Responsive Controller
 */
document.addEventListener('DOMContentLoaded', function() {
    // Pagination Configuration
    const ROWS_PER_PAGE = 8;
    let currentPage = 1;
    let allRows = Array.from(document.querySelectorAll('#paymentsTableBody .transaction-row'));
    let filteredRows = allRows;

    // Initialize pagination
    showPage(1);

    function showPage(page) {
        const totalPages = Math.ceil(filteredRows.length / ROWS_PER_PAGE) || 1;
        if (page < 1) page = 1;
        if (page > totalPages) page = totalPages;
        currentPage = page;

        const startIdx = (page - 1) * ROWS_PER_PAGE;
        const endIdx = startIdx + ROWS_PER_PAGE;

        // Hide all rows
        allRows.forEach(row => row.style.display = 'none');

        // Show only current page rows
        filteredRows.slice(startIdx, endIdx).forEach(row => {
            row.style.display = '';
        });

        const noResults = document.getElementById('noPaymentResults');
        if (noResults) {
            noResults.style.display = filteredRows.length === 0 ? 'block' : 'none';
        }

        renderPaginationControls(totalPages);
        updatePaginationInfo(startIdx, endIdx);
    }

    function renderPaginationControls(totalPages) {
        const container = document.getElementById('pageNumbers');
        const prevBtn = document.getElementById('prevPage');
        const nextBtn = document.getElementById('nextPage');
        
        if (!container || !prevBtn || !nextBtn) return;
        container.innerHTML = '';

        prevBtn.disabled = currentPage === 1;
        nextBtn.disabled = currentPage === totalPages || filteredRows.length === 0;

        prevBtn.onclick = () => showPage(currentPage - 1);
        nextBtn.onclick = () => showPage(currentPage + 1);

        if (filteredRows.length === 0) return;

        for (let i = 1; i <= totalPages; i++) {
            const btn = document.createElement('button');
            const isActive = (i === currentPage);
            btn.className = `page-num-btn ${isActive ? 'active' : ''}`;
            btn.innerText = i;
            btn.setAttribute('type', 'button');
            btn.onclick = () => showPage(i);
            container.appendChild(btn);
        }
    }

    function updatePaginationInfo(startIdx, endIdx) {
        const start = document.getElementById('startRange');
        const end = document.getElementById('endRange');
        const total = document.getElementById('totalEntries');
        
        if (start && end && total) {
            start.innerText = filteredRows.length === 0 ? 0 : startIdx + 1;
            end.innerText = Math.min(endIdx, filteredRows.length);
            total.innerText = filteredRows.length;
        }
    }

    // Toggle Action Menu
    window.toggleActionMenu = function(id, event) {
        if (event) event.stopPropagation();
        
        document.querySelectorAll('.pay-dropdown-menu').forEach(menu => {
            if (menu.id !== 'actionMenu-' + id && menu.id !== 'exportMenu') {
                menu.style.display = 'none';
                menu.classList.remove('active');
            }
        });
        
        const element = document.getElementById('actionMenu-' + id);
        if (element) {
            if (element.style.display === "none" || element.style.display === "") {
                element.style.display = "block";
                setTimeout(() => element.classList.add('active'), 10);
            } else {
                element.classList.remove('active');
                setTimeout(() => element.style.display = "none", 150);
            }
        }
    };

    // Toggle Export Menu
    window.toggleExportMenu = function(event) {
        if (event) event.stopPropagation();
        const menu = document.getElementById('exportMenu');
        if (!menu) return;
        
        if (menu.style.display === "none" || menu.style.display === "") {
            menu.style.display = "block";
            setTimeout(() => menu.classList.add('active'), 10);
        } else {
            menu.classList.remove('active');
            setTimeout(() => menu.style.display = "none", 150);
        }
    };

    // Close on outside click
    document.addEventListener('click', function(event) {
        const isClickOutside = !event.target.closest('.pay-action-wrapper') && 
                               !event.target.closest('.export-dropdown-container');
        if (isClickOutside) {
            document.querySelectorAll('.pay-dropdown-menu').forEach(menu => {
                menu.classList.remove('active');
                menu.style.display = 'none';
            });
        }
    });

    function getRowStatusText(row) {
        const badges = row.querySelectorAll('.badge-pstatus, .badge-ptype');
        if (badges && badges.length > 0) {
            return Array.from(badges).map(b => b.textContent.trim()).filter(Boolean).join(' | ');
        }
        return row.getAttribute('data-status') || '';
    }

    // Filter Payments
    window.filterPayments = function() {
        const queryEl = document.getElementById('paymentSearch');
        const query = (queryEl ? queryEl.value : '').toLowerCase().trim();
        const statusEl = document.getElementById('statusFilter');
        const status = (statusEl ? statusEl.value : 'all').toLowerCase().trim();
        const typeEl = document.getElementById('typeFilter');
        const pType = (typeEl ? typeEl.value : 'all').toLowerCase().trim();
        
        allRows = Array.from(document.querySelectorAll('#paymentsTableBody .transaction-row'));
        
        filteredRows = allRows.filter(row => {
            const textContent = row.textContent.toLowerCase();
            const dataStatus = (row.getAttribute('data-status') || '').toLowerCase();
            const dataType = (row.getAttribute('data-type') || '').toLowerCase();
            const badges = Array.from(row.querySelectorAll('.badge-pstatus, .badge-ptype'))
                .map(b => b.textContent.toLowerCase().trim()).join(' ');
            const combinedStatus = `${dataStatus} ${badges}`;
            
            const matchesSearch = !query || textContent.includes(query);

            let matchesType = (pType === 'all');
            if (!matchesType) {
                matchesType = dataType.includes(pType) || badges.includes(pType);
            }

            let matchesStatus = (status === 'all');
            if (!matchesStatus) {
                if (status === 'paid') {
                    matchesStatus = combinedStatus.includes('fully paid') || (combinedStatus.includes('paid') && !combinedStatus.includes('partially'));
                } else if (status === 'partial') {
                    matchesStatus = combinedStatus.includes('partially paid') || combinedStatus.includes('partial');
                } else if (status === 'verify') {
                    matchesStatus = combinedStatus.includes('pending verification') || combinedStatus.includes('pending verify') || combinedStatus.includes('review');
                } else if (status === 'unpaid') {
                    matchesStatus = combinedStatus.includes('unpaid') || combinedStatus.includes('pending');
                } else if (status === 'refunded') {
                    matchesStatus = combinedStatus.includes('refund');
                } else {
                    matchesStatus = combinedStatus.includes(status);
                }
            }
            
            return matchesSearch && matchesType && matchesStatus;
        });
        
        currentPage = 1;
        showPage(1);
    };

    // Export PDF
    window.exportToPDF = function() {
        const jsPDFLib = window.jspdf ? window.jspdf.jsPDF : window.jsPDF;
        if (!jsPDFLib) {
            alert("PDF library is still loading. Please try again in a moment.");
            return;
        }

        try {
            const doc = new jsPDFLib({ orientation: 'landscape' });
            const primaryColor = '#ff7b54';

            doc.setFontSize(20);
            doc.setTextColor(primaryColor);
            doc.text('Payments & Earnings Report', 14, 20);
            
            doc.setFontSize(10);
            doc.setTextColor(100);
            doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 28);

            let totalPrice = 0;
            const tableData = filteredRows.map(row => {
                const amtEl = row.querySelector('.amount-pro');
                const amtText = amtEl ? amtEl.textContent.replace('₱', '').replace(/,/g, '').trim() : '0';
                const amt = parseFloat(amtText) || 0;
                totalPrice += amt;
                
                const custName = (row.querySelector('.pay-customer-name') ? row.querySelector('.pay-customer-name').textContent.trim() : '') || row.getAttribute('data-customer') || 'Customer';
                const payId = (row.querySelector('.pay-id') ? row.querySelector('.pay-id').textContent.trim() : '') || row.getAttribute('data-payment-id') || '';
                const bkId = (row.querySelector('.pay-booking-ref') ? row.querySelector('.pay-booking-ref').textContent.trim() : '') || ('BK-' + row.getAttribute('data-booking-id'));
                const ptype = row.getAttribute('data-type') || 'Payment';
                const method = row.getAttribute('data-method') || 'Direct';
                const dateStr = row.getAttribute('data-date') || '';
                
                return [
                    payId,
                    bkId,
                    custName,
                    ptype.toUpperCase(),
                    `₱${amt.toLocaleString(undefined, {minimumFractionDigits: 2})}`, 
                    method,
                    dateStr,
                    getRowStatusText(row).toUpperCase()
                ];
            });

            doc.autoTable({
                startY: 36,
                head: [['PAYMENT ID', 'BOOKING', 'CUSTOMER', 'TYPE', 'AMOUNT', 'METHOD', 'DATE', 'STATUS']],
                body: tableData,
                theme: 'grid',
                headStyles: { 
                    fillColor: [15, 23, 42], 
                    textColor: 255, 
                    fontSize: 9, 
                    fontStyle: 'bold'
                },
                styles: { 
                    fontSize: 8.5, 
                    cellPadding: 4, 
                    lineColor: [226, 232, 240], 
                    lineWidth: 0.1 
                },
                alternateRowStyles: { fillColor: [248, 250, 252] },
                margin: { left: 14, right: 14 }
            });

            const finalY = doc.lastAutoTable.finalY + 10;
            doc.setFontSize(11);
            doc.setTextColor(15, 23, 42);
            doc.setFont('helvetica', 'bold');
            doc.text(`TOTAL COLLECTED: ₱${totalPrice.toLocaleString(undefined, {minimumFractionDigits: 2})}`, doc.internal.pageSize.width - 14, finalY, { align: 'right' });

            doc.save(`Payments_Report_${Date.now()}.pdf`);
        } catch (e) {
            console.error("PDF Export error:", e);
            alert("Could not generate PDF at this time.");
        }
    };

    // Export Excel
    window.exportToExcel = function() {
        if (!window.XLSX) {
            alert("Excel library is still loading. Please try again in a moment.");
            return;
        }
        try {
            let totalAmt = 0;
            const dataRows = filteredRows.map(row => {
                const amtEl = row.querySelector('.amount-pro');
                const amtText = amtEl ? amtEl.textContent.replace('₱', '').replace(/,/g, '').trim() : '0';
                const amt = parseFloat(amtText) || 0;
                totalAmt += amt;

                const custName = (row.querySelector('.pay-customer-name') ? row.querySelector('.pay-customer-name').textContent.trim() : '') || row.getAttribute('data-customer') || 'Customer';
                const payId = (row.querySelector('.pay-id') ? row.querySelector('.pay-id').textContent.trim() : '') || row.getAttribute('data-payment-id') || '';
                const bkId = (row.querySelector('.pay-booking-ref') ? row.querySelector('.pay-booking-ref').textContent.trim() : '') || ('BK-' + row.getAttribute('data-booking-id'));
                const ptype = row.getAttribute('data-type') || 'Payment';
                const method = row.getAttribute('data-method') || 'Direct';
                const dateStr = row.getAttribute('data-date') || '';

                return [
                    payId,
                    bkId,
                    custName,
                    ptype,
                    amt,
                    method,
                    dateStr,
                    getRowStatusText(row)
                ];
            });

            const data = [
                ['Payment ID', 'Booking Ref', 'Customer', 'Payment Type', 'Amount (PHP)', 'Method', 'Date', 'Status'],
                ...dataRows,
                ['', '', '', 'TOTAL COLLECTED', totalAmt, '', '', '']
            ];

            const wb = XLSX.utils.book_new();
            const ws = XLSX.utils.aoa_to_sheet(data);
            ws['!cols'] = [
                {wch: 15}, {wch: 15}, {wch: 25}, {wch: 18}, {wch: 16}, {wch: 15}, {wch: 18}, {wch: 20}
            ];

            XLSX.utils.book_append_sheet(wb, ws, 'Payments');
            XLSX.writeFile(wb, `Payments_Report_${Date.now()}.xlsx`);
        } catch (e) {
            console.error("Excel Export error:", e);
            alert("Could not generate Excel file.");
        }
    };

    // Export CSV
    window.exportToCSV = function() {
        try {
            let csv = 'Payment ID,Booking Ref,Customer,Payment Type,Amount,Method,Date,Status\n';
            filteredRows.forEach(row => {
                const amtEl = row.querySelector('.amount-pro');
                const amtText = amtEl ? amtEl.textContent.replace('₱', '').replace(/,/g, '').trim() : '0';
                const custName = (row.querySelector('.pay-customer-name') ? row.querySelector('.pay-customer-name').textContent.trim() : '') || row.getAttribute('data-customer') || 'Customer';
                const payId = (row.querySelector('.pay-id') ? row.querySelector('.pay-id').textContent.trim() : '') || row.getAttribute('data-payment-id') || '';
                const bkId = (row.querySelector('.pay-booking-ref') ? row.querySelector('.pay-booking-ref').textContent.trim() : '') || ('BK-' + row.getAttribute('data-booking-id'));
                const ptype = row.getAttribute('data-type') || 'Payment';
                const method = row.getAttribute('data-method') || 'Direct';
                const dateStr = row.getAttribute('data-date') || '';

                const data = [
                    payId,
                    bkId,
                    custName,
                    ptype,
                    amtText,
                    method,
                    dateStr,
                    getRowStatusText(row)
                ];
                csv += data.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',') + '\n';
            });

            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Payments_Report_${Date.now()}.csv`;
            a.click();
        } catch (e) {
            console.error("CSV Export error:", e);
            alert("Could not export CSV file.");
        }
    };

    // Details Modal Hydration (Instant from Data Row Attributes)
    window.showTransactionModal = function(paymentId) {
        const row = document.querySelector(`tr[data-payment-id="${paymentId}"]`);
        if (!row) {
            window.viewPaymentDetails(paymentId);
            return;
        }

        const bookingId = row.getAttribute('data-booking-id');
        const bookingRef = row.getAttribute('data-booking-ref') || (row.querySelector('.pay-booking-ref') ? row.querySelector('.pay-booking-ref').textContent.replace('#', '').trim() : '') || ('BK-' + bookingId);
        const custName = row.getAttribute('data-customer') || 'Customer';
        const custRef = row.getAttribute('data-customer-ref') || '';
        const total = parseFloat(row.getAttribute('data-total')) || 0;
        const paid = parseFloat(row.getAttribute('data-paid')) || 0;
        const balance = parseFloat(row.getAttribute('data-balance')) || 0;
        const method = row.getAttribute('data-method') || 'Direct';
        const dateStr = row.getAttribute('data-date') || '—';
        const proofUrl = row.getAttribute('data-proof') || '';
        const contractUrl = row.getAttribute('data-contract') || '';
        const status = row.getAttribute('data-status') || 'Pending';
        const ptype = row.getAttribute('data-type') || 'Payment';
        
        // Commission estimate
        const commissionAttr = row.getAttribute('data-commission');
        const commission = commissionAttr ? parseFloat(commissionAttr) : (total * 0.10);
        const estEarnings = Math.max(0, paid - commission);

        const content = document.getElementById('detailsContent');
        if (!content) return;

        let statusBadgeClass = 'badge-pstatus-unpaid';
        if (status.includes('fully') || status.includes('paid')) statusBadgeClass = 'badge-pstatus-paid';
        else if (status.includes('partial')) statusBadgeClass = 'badge-pstatus-partial';
        else if (status.includes('verify')) statusBadgeClass = 'badge-pstatus-review';
        else if (status.includes('refund')) statusBadgeClass = 'badge-pstatus-refunded';

        content.innerHTML = `
            <div class="modal-detail-sections">
                <!-- 1. Payment Information -->
                <div class="modal-detail-section">
                    <h4 class="modal-section-title"><i class="fas fa-info-circle" style="color: var(--primary-color);"></i> Payment Information</h4>
                    <div class="modal-info-grid">
                        <div class="modal-info-item">
                            <span class="modal-info-label">Customer Reference</span>
                            <span class="modal-info-val" style="font-weight: 700; color: #0f172a;">${custRef || custName}</span>
                        </div>
                        <div class="modal-info-item">
                            <span class="modal-info-label">Booking ID</span>
                            <span class="modal-info-val"><a href="/caterer/bookings?booking_id=${bookingId}" class="pay-booking-ref">#${bookingRef}</a></span>
                        </div>
                        <div class="modal-info-item">
                            <span class="modal-info-label">Payment Method</span>
                            <span class="modal-info-val">${method}</span>
                        </div>
                        <div class="modal-info-item">
                            <span class="modal-info-label">Payment Status</span>
                            <span class="modal-info-val"><span class="badge-pstatus ${statusBadgeClass}">${status}</span></span>
                        </div>
                        <div class="modal-info-item">
                            <span class="modal-info-label">Payment Date</span>
                            <span class="modal-info-val">${dateStr}</span>
                        </div>
                        <div class="modal-info-item">
                            <span class="modal-info-label">Payment Type</span>
                            <span class="modal-info-val"><span class="badge-ptype badge-ptype-dp">${ptype}</span></span>
                        </div>
                    </div>
                </div>

                <!-- 2. Financial Breakdown -->
                <div class="modal-detail-section">
                    <h4 class="modal-section-title"><i class="fas fa-calculator" style="color: #6366f1;"></i> Financial Breakdown</h4>
                    <div class="modal-breakdown-list">
                        <div class="modal-breakdown-row">
                            <span class="row-label">Booking Total Contract Value:</span>
                            <span class="row-val">₱${total.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                        </div>
                        <div class="modal-breakdown-row">
                            <span class="row-label">Amount Paid to Date:</span>
                            <span class="row-val" style="color: #059669;">₱${paid.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                        </div>
                        <div class="modal-breakdown-row highlight-warn">
                            <span class="row-label" style="color: #c2410c;">Remaining Customer Balance:</span>
                            <span class="row-val" style="color: #c2410c;">₱${balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                        </div>
                        <div class="modal-breakdown-row">
                            <span class="row-label">Platform Commission:</span>
                            <span class="row-val" style="color: #dc2626;">− ₱${commission.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                        </div>
                        <div class="modal-breakdown-row highlight-net">
                            <span class="row-label" style="font-weight: 800; color: #0f172a;">Estimated Earnings After Platform Commission:</span>
                            <span class="row-val" style="color: var(--primary-color); font-size: 1.05rem;">₱${estEarnings.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                        </div>
                    </div>
                </div>

                <!-- 3. Documents -->
                <div class="modal-detail-section">
                    <h4 class="modal-section-title"><i class="fas fa-folder-open" style="color: #d97706;"></i> Documents</h4>
                    <div class="modal-docs-actions">
                        ${proofUrl ? `
                            <button type="button" class="btn-sm-outline" onclick="window.showProof('${proofUrl}', 'Receipt - ${paymentId}')">
                                <i class="fas fa-receipt"></i> Payment Proof
                            </button>
                        ` : '<span class="no-doc">No payment proof uploaded</span>'}
                        ${contractUrl ? `
                            <a href="${contractUrl}" target="_blank" class="btn-sm-outline">
                                <i class="fas fa-file-contract"></i> Digital Contract
                            </a>
                        ` : ''}
                        <button type="button" class="btn-sm-outline" onclick="window.viewInvoice('${bookingId}')">
                            <i class="fas fa-file-invoice"></i> View Invoice
                        </button>
                        <a href="/caterer/bookings?booking_id=${bookingId}" class="btn-sm-outline">
                            <i class="fas fa-external-link-alt"></i> View Booking
                        </a>
                    </div>
                </div>
            </div>
        `;

        if (typeof window.openModal === 'function') {
            window.openModal('detailsModal');
        } else {
            const el = document.getElementById('detailsModal');
            if (el) {
                el.style.display = 'flex';
                el.classList.add('active');
                document.body.style.overflow = 'hidden';
            }
        }
    };

    // Full Details Modal Hydration via API (for Outstanding Customer Balances & Direct links)
    window.viewPaymentDetails = async function(bookingId) {
        const content = document.getElementById('detailsContent');
        if (!content) return;
        
        content.innerHTML = '<div style="text-align: center; padding: 3rem;"><i class="fas fa-spinner fa-spin fa-2x" style="color: var(--primary-color);"></i><p style="margin-top: 0.75rem; color: #64748b; font-size: 0.85rem;">Loading financial details...</p></div>';
        if (typeof window.openModal === 'function') {
            window.openModal('detailsModal');
        } else {
            const el = document.getElementById('detailsModal');
            if (el) {
                el.style.display = 'flex';
                el.classList.add('active');
                document.body.style.overflow = 'hidden';
            }
        }

        try {
            const response = await fetch(`/caterer/api/bookings/${bookingId}/details`);
            const booking = await response.json();
            
            if (!response.ok) throw new Error(booking.detail || "Failed to load booking details");

            const total = parseFloat(booking.total_amount || booking.total_price || 0);
            const paid = parseFloat(booking.paid_amount || booking._pay_verified || 0);
            const balance = parseFloat(booking.balance_amount || booking._pay_balance || (total - paid));
            const commission = parseFloat(booking.commission || (total * 0.10));
            const estEarnings = parseFloat(booking.net_earnings || (paid - commission));
            const custRef = booking.customer_ref || 'Client';
            const status = booking.payment_status || booking.status || 'Pending';
            const method = booking.payment_method || 'Direct';
            const dateStr = booking.event_date ? new Date(booking.event_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—';
            const proofUrl = booking.payment_proof_url || booking.balance_proof_url || '';

            let statusBadgeClass = 'badge-pstatus-unpaid';
            if (status.includes('paid')) statusBadgeClass = 'badge-pstatus-paid';
            else if (status.includes('partial')) statusBadgeClass = 'badge-pstatus-partial';
            else if (status.includes('review') || status.includes('proof')) statusBadgeClass = 'badge-pstatus-review';

            content.innerHTML = `
                <div class="modal-detail-sections">
                    <!-- 1. Payment Information -->
                    <div class="modal-detail-section">
                        <h4 class="modal-section-title"><i class="fas fa-info-circle" style="color: var(--primary-color);"></i> Payment Information</h4>
                        <div class="modal-info-grid">
                            <div class="modal-info-item">
                                <span class="modal-info-label">Customer Reference</span>
                                <span class="modal-info-val" style="font-weight: 700;">${custRef}</span>
                            </div>
                            <div class="modal-info-item">
                                <span class="modal-info-label">Booking ID</span>
                                <span class="modal-info-val"><a href="/caterer/bookings?booking_id=${bookingId}" class="pay-booking-ref">#${booking.booking_ref || booking.booking_reference || ('BK-' + bookingId)}</a></span>
                            </div>
                            <div class="modal-info-item">
                                <span class="modal-info-label">Payment Method</span>
                                <span class="modal-info-val">${method}</span>
                            </div>
                            <div class="modal-info-item">
                                <span class="modal-info-label">Payment Status</span>
                                <span class="modal-info-val"><span class="badge-pstatus ${statusBadgeClass}">${status}</span></span>
                            </div>
                            <div class="modal-info-item">
                                <span class="modal-info-label">Event Date</span>
                                <span class="modal-info-val">${dateStr}</span>
                            </div>
                            <div class="modal-info-item">
                                <span class="modal-info-label">Payment Plan</span>
                                <span class="modal-info-val">${booking.payment_plan ? booking.payment_plan.toUpperCase() : 'STANDARD'}</span>
                            </div>
                        </div>
                    </div>

                    <!-- 2. Financial Breakdown -->
                    <div class="modal-detail-section">
                        <h4 class="modal-section-title"><i class="fas fa-calculator" style="color: #6366f1;"></i> Financial Breakdown</h4>
                        <div class="modal-breakdown-list">
                            <div class="modal-breakdown-row">
                                <span class="row-label">Booking Total Contract Value:</span>
                                <span class="row-val">₱${total.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                            </div>
                            <div class="modal-breakdown-row">
                                <span class="row-label">Amount Paid to Date:</span>
                                <span class="row-val" style="color: #059669;">₱${paid.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                            </div>
                            <div class="modal-breakdown-row highlight-warn">
                                <span class="row-label" style="color: #c2410c;">Remaining Customer Balance:</span>
                                <span class="row-val" style="color: #c2410c;">₱${balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                            </div>
                            <div class="modal-breakdown-row">
                                <span class="row-label">Platform Commission:</span>
                                <span class="row-val" style="color: #dc2626;">− ₱${commission.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                            </div>
                            <div class="modal-breakdown-row highlight-net">
                                <span class="row-label" style="font-weight: 800; color: #0f172a;">Estimated Earnings After Platform Commission:</span>
                                <span class="row-val" style="color: var(--primary-color); font-size: 1.05rem;">₱${estEarnings.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                            </div>
                        </div>
                    </div>

                    <!-- 3. Documents -->
                    <div class="modal-detail-section">
                        <h4 class="modal-section-title"><i class="fas fa-folder-open" style="color: #d97706;"></i> Documents</h4>
                        <div class="modal-docs-actions">
                            ${proofUrl ? `
                                <button type="button" class="btn-sm-outline" onclick="window.showProof('${proofUrl}', 'Receipt - BK-${bookingId}')">
                                    <i class="fas fa-receipt"></i> Payment Proof
                                </button>
                            ` : '<span class="no-doc">No payment proof uploaded</span>'}
                            ${booking.contract_url ? `
                                <a href="${booking.contract_url}" target="_blank" class="btn-sm-outline">
                                    <i class="fas fa-file-contract"></i> Digital Contract
                                </a>
                            ` : ''}
                            <button type="button" class="btn-sm-outline" onclick="window.viewInvoice('${bookingId}')">
                                <i class="fas fa-file-invoice"></i> View Invoice
                            </button>
                            <a href="/caterer/bookings?booking_id=${bookingId}" class="btn-sm-outline">
                                <i class="fas fa-external-link-alt"></i> View Booking
                            </a>
                        </div>
                    </div>
                </div>
            `;
        } catch (err) {
            console.error("View payment details error:", err);
            content.innerHTML = `<div style="text-align: center; color: #dc2626; padding: 2rem;"><i class="fas fa-exclamation-triangle fa-2x"></i><p style="margin-top: 0.5rem; font-weight: 600;">${err.message}</p></div>`;
        }
    };

    window.closeDetailsModal = function() {
        if (typeof window.closeModal === 'function') {
            window.closeModal('detailsModal');
        } else {
            const el = document.getElementById('detailsModal');
            if (el) {
                el.classList.remove('active');
                el.style.display = 'none';
                document.body.style.overflow = '';
            }
        }
    };

    // Verify Payment
    window.verifyPayment = function(bookingId) {
        const doVerify = () => {
            if (window.apiAction) {
                window.apiAction(`/caterer/payments/${bookingId}/confirm`, { 
                    method: "POST",
                    headers: { 'Content-Type': 'application/json' }
                })
                .then(res => {
                    if (res && res.status === 'success') {
                        window.location.reload();
                    } else {
                        window.location.reload();
                    }
                })
                .catch(err => {
                    console.error("Payment Verification Error:", err);
                    window.location.reload();
                });
            } else {
                const f = document.createElement('form'); 
                f.method = 'POST'; 
                f.action = `/caterer/payments/${bookingId}/confirm`; 
                document.body.appendChild(f); 
                f.submit();
            }
        };

        const row = document.querySelector(`tr[data-booking-id="${bookingId}"]`);
        const bRef = row ? (row.getAttribute('data-booking-ref') || (row.querySelector('.pay-booking-ref') ? row.querySelector('.pay-booking-ref').textContent.replace('#', '').trim() : '')) : '';
        const bLabel = bRef ? `#${bRef}` : `#BK-${bookingId}`;

        if (typeof window.showConfirm === 'function') {
            window.showConfirm(
                `Verify payment for booking ${bLabel}? This will mark the transaction as verified and update the booking.`,
                doVerify,
                'Verify Payment',
                'Yes, Verify Payment',
                'success'
            );
        } else {
            if (confirm(`Verify payment for booking ${bLabel}? This will confirm the received payment.`)) {
                doVerify();
            }
        }
    };

    // Confirm Cash Payment
    window.confirmCashPayment = function(bookingId, customerName, amount, paymentStatus) {
        const amountVal = parseFloat(amount) || 0;
        const today = new Date().toISOString().slice(0, 10);
        const amtLabel = amountVal ? `₱${amountVal.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : 'the cash payment';

        const doConfirm = () => {
            if (window.apiAction) {
                window.apiAction(`/caterer/payments/${bookingId}/confirm-cash`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        amount_received: amountVal,
                        payment_date: today,
                        notes: ''
                    })
                }).then(res => {
                    if (res && res.status === 'success') {
                        window.location.reload();
                    }
                }).catch(err => console.error('Cash confirm error:', err));
            } else {
                const f = document.createElement('form'); 
                f.method = 'POST'; 
                f.action = `/caterer/payments/${bookingId}/confirm-cash`; 
                document.body.appendChild(f); 
                f.submit();
            }
        };

        if (typeof window.showConfirm === 'function') {
            window.showConfirm(
                `Confirm that you have physically received ${amtLabel} in cash?`,
                doConfirm,
                'Confirm Cash Payment',
                'Yes, Cash Received',
                'success'
            );
        } else {
            if (confirm(`Confirm that you have physically received ${amtLabel} in cash?`)) {
                doConfirm();
            }
        }
    };

    // Real-time Event Listener (from layout.js)
    window.addEventListener('payoutUpdate', function(e) {
        console.log("Real-time payout update triggered refresh");
        refreshPaymentSummary();
        // If it was a completion, reload to update the history table
        if (e.detail.type === 'payout_completed' || e.detail.type === 'payout_update') {
            setTimeout(() => window.location.reload(), 1500);
        }
    });

    // Settle Dues Modal Logic
    window.openSettleModal = function(billingPeriod, amountDue) {
        const periodInput = document.getElementById('settlePeriod');
        if (periodInput && billingPeriod) {
            periodInput.value = billingPeriod;
        } else if (periodInput && !periodInput.value) {
            const now = new Date();
            const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
            periodInput.value = `${monthNames[now.getMonth()]} ${now.getFullYear()}`;
        }
        const amountEl = document.getElementById('settleAmountDue');
        const selectedAmount = Number(amountDue);
        if (amountEl && Number.isFinite(selectedAmount) && selectedAmount >= 0) {
            amountEl.innerText = `₱${selectedAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        }
        if (typeof window.openModal === 'function') {
            window.openModal('settleModal');
        } else {
            const el = document.getElementById('settleModal');
            if (el) {
                el.style.display = 'flex';
                el.classList.add('active');
                document.body.style.overflow = 'hidden';
            }
        }
    };

    window.closeSettleModal = function() {
        if (typeof window.closeModal === 'function') {
            window.closeModal('settleModal');
        } else {
            const el = document.getElementById('settleModal');
            if (el) {
                el.classList.remove('active');
                el.style.display = 'none';
                document.body.style.overflow = '';
            }
        }
    };

    window.submitSettleDues = async function() {
        const btn = document.getElementById('btnSubmitSettle');
        const originalHtml = btn ? btn.innerHTML : '';
        const period = document.getElementById('settlePeriod') ? document.getElementById('settlePeriod').value : '';
        const fileInput = document.getElementById('settleProofFile');
        const proofFile = fileInput && fileInput.files ? fileInput.files[0] : null;

        if (!period || !proofFile) {
            alert("Please specify the billing period and upload a payment screenshot.");
            return;
        }
        
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
        }
        
        try {
            const formData = new FormData();
            formData.append("billing_period", period);
            formData.append("proof_file", proofFile);

            const response = await fetch('/caterer/api/payments/settle-dues', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            
            if (response.ok && data.status === 'success') {
                alert("Proof of payment submitted successfully! OccaServe admin will verify it shortly.");
                window.closeSettleModal();
                setTimeout(() => window.location.reload(), 1000);
            } else {
                throw new Error(data.detail || "Unable to submit settlement at this time.");
            }
        } catch (err) {
            console.error("Submit settlement error:", err);
            alert(err.message || "An error occurred while submitting settlement.");
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalHtml;
            }
        }
    };

    // Proof Modal
    window.showProof = function(url, title) {
        const img = document.getElementById('proofModalImg');
        const h3 = document.getElementById('proofModalTitle');
        if (img) img.src = url;
        if (h3 && title) h3.innerText = title;
        if (typeof window.openModal === 'function') {
            window.openModal('proofModal');
        } else {
            const el = document.getElementById('proofModal');
            if (el) {
                el.style.display = 'flex';
                el.classList.add('active');
                document.body.style.overflow = 'hidden';
            }
        }
    };

    window.closeProof = function() {
        if (typeof window.closeModal === 'function') {
            window.closeModal('proofModal');
        } else {
            const el = document.getElementById('proofModal');
            if (el) {
                el.classList.remove('active');
                el.style.display = 'none';
                document.body.style.overflow = '';
            }
        }
    };

    // Invoice Modal
    window.viewInvoice = async function(bookingId) {
        const content = document.getElementById('invoiceContent');
        if (!content) return;
        
        content.innerHTML = '<div style="text-align: center; padding: 3rem;"><i class="fas fa-spinner fa-spin fa-2x" style="color: var(--primary-color);"></i><p style="margin-top: 0.75rem; color: #64748b; font-size: 0.85rem;">Generating invoice...</p></div>';
        if (typeof window.openModal === 'function') {
            window.openModal('invoiceModal');
        } else {
            const el = document.getElementById('invoiceModal');
            if (el) {
                el.style.display = 'flex';
                el.classList.add('active');
                document.body.style.overflow = 'hidden';
            }
        }

        try {
            const response = await fetch(`/caterer/api/bookings/${bookingId}/details`);
            if (!response.ok) throw new Error("Could not fetch invoice details");
            const data = await response.json();
            
            const customerRef = data.customer_ref || ('Client #' + bookingId);
            const totalAmount = Number(data.total_amount ?? data.total_price ?? 0);
            const formattedAmount = totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2 });
            const dateStr = new Date(data.created_at || Date.now()).toLocaleDateString('en-PH', { 
                year: 'numeric', month: 'long', day: 'numeric' 
            });

            content.innerHTML = `
                <div style="background: white; padding: 2rem; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 12px rgba(0,0,0,0.02);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; border-bottom: 2px solid #f1f5f9; padding-bottom: 1.25rem;">
                        <div>
                            <h2 style="margin: 0; color: var(--primary-color, #ff7b54); font-weight: 800; font-size: 1.4rem;">OccaServe</h2>
                            <p style="margin: 4px 0 0; font-size: 0.72rem; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;">Official Invoice</p>
                        </div>
                        <div style="text-align: right;">
                            <h3 style="margin: 0; font-size: 1.15rem; font-weight: 800; color: #0f172a;">#${data.invoice_ref || data.booking_ref || data.booking_reference || ('BK-' + bookingId)}</h3>
                            <p style="margin: 4px 0 0; font-size: 0.8rem; color: #64748b; font-weight: 600;">Date: ${dateStr}</p>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem;">
                        <div>
                            <h4 style="font-size: 0.72rem; text-transform: uppercase; color: #64748b; margin: 0 0 0.4rem 0; font-weight: 800; letter-spacing: 0.04em;">Customer Reference</h4>
                            <p style="margin: 0; font-weight: 700; font-size: 0.88rem; color: #0f172a;">${customerRef}</p>
                            <p style="margin: 2px 0 0; font-size: 0.8rem; color: #64748b;">Verified Booking Client</p>
                        </div>
                        <div style="text-align: right;">
                            <h4 style="font-size: 0.72rem; text-transform: uppercase; color: #64748b; margin: 0 0 0.4rem 0; font-weight: 800; letter-spacing: 0.04em;">Service Provider</h4>
                            <p style="margin: 0; font-weight: 700; font-size: 0.88rem; color: #0f172a;">Verified OccaServe Partner</p>
                            <p style="margin: 2px 0 0; font-size: 0.8rem; color: #64748b;">Platform Certified Caterer</p>
                        </div>
                    </div>

                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 1.5rem;">
                        <thead>
                            <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                                <th style="text-align: left; padding: 10px; font-size: 0.72rem; font-weight: 800; color: #64748b; text-transform: uppercase;">Description</th>
                                <th style="text-align: right; padding: 10px; font-size: 0.72rem; font-weight: 800; color: #64748b; text-transform: uppercase;">Amount</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td style="padding: 1rem 10px; border-bottom: 1px solid #f1f5f9;">
                                    <div style="font-weight: 700; font-size: 0.88rem; color: #0f172a;">${data.event_name || data.event_type || 'Catering Package Service'}</div>
                                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 2px;">Confirmed event booking services.</div>
                                </td>
                                <td style="text-align: right; padding: 1rem 10px; font-weight: 800; font-size: 0.9rem; color: #0f172a; border-bottom: 1px solid #f1f5f9;">₱${formattedAmount}</td>
                            </tr>
                        </tbody>
                    </table>

                    <div style="margin-left: auto; width: 100%; max-width: 260px;">
                        <div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 0.82rem; color: #64748b; font-weight: 600;">
                            <span>Subtotal:</span>
                            <span>₱${formattedAmount}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0; font-weight: 800; font-size: 1.1rem; color: var(--primary-color, #ff7b54); border-top: 2px solid #e2e8f0; margin-top: 6px;">
                            <span>TOTAL:</span>
                            <span>₱${formattedAmount}</span>
                        </div>
                    </div>

                    <div style="margin-top: 2rem; padding-top: 1rem; border-top: 1px dashed #cbd5e1; text-align: center;">
                        <p style="margin: 0; font-size: 0.72rem; color: #94a3b8; font-weight: 600;">Generated electronically via OccaServe. Audit and tax compliant.</p>
                    </div>
                </div>
            `;
        } catch (err) {
            console.error("View invoice error:", err);
            content.innerHTML = `<p style="text-align: center; color: #dc2626; padding: 2rem; font-weight: 700;">${err.message || 'Failed to generate invoice.'}</p>`;
        }
    };

    window.printInvoice = function() {
        const content = document.getElementById('invoiceContent');
        if (!content) return;
        const win = window.open('', '', 'height=700,width=850');
        win.document.write('<html><head><title>Invoice</title>');
        win.document.write('<style>body{font-family: sans-serif; padding: 30px; color: #0f172a;} table{width:100%; border-collapse:collapse;} th,td{padding:10px; border-bottom:1px solid #f1f5f9;} th{background:#f8fafc; text-transform:uppercase; font-size:10px; color:#64748b;}</style>');
        win.document.write('</head><body>');
        win.document.write(content.innerHTML);
        win.document.write('</body></html>');
        win.document.close();
        win.print();
    };

    window.closeInvoiceModal = function() {
        if (typeof window.closeModal === 'function') {
            window.closeModal('invoiceModal');
        } else {
            const el = document.getElementById('invoiceModal');
            if (el) {
                el.classList.remove('active');
                el.style.display = 'none';
                document.body.style.overflow = '';
            }
        }
    };

    // Real-time Summary Polling
    async function refreshPaymentSummary() {
        try {
            const response = await fetch('/caterer/api/payments/summary');
            if (!response.ok) return;
            const data = await response.json();
            
            if (data) {
                const formatter = new Intl.NumberFormat('en-PH', {
                    style: 'currency',
                    currency: 'PHP',
                    minimumFractionDigits: 2
                });

                if (data.collected_total !== undefined) {
                    const colEl = document.getElementById('kpiCollected');
                    if (colEl) colEl.innerText = formatter.format(data.collected_total);
                }
            }
        } catch (err) {
            console.warn("Summary poll note:", err);
        }
    }

    // Refresh every 35 seconds
    setInterval(refreshPaymentSummary, 35000);

    // Real-time Payout & Global Search listeners
    window.addEventListener('payoutUpdate', function(e) {
        refreshPaymentSummary();
        if (e.detail && (e.detail.type === 'payout_completed' || e.detail.type === 'payout_update')) {
            setTimeout(() => window.location.reload(), 1500);
        }
    });

    window.addEventListener('globalSearch', function(e) {
        const searchInput = document.getElementById('paymentSearch');
        if (searchInput && typeof window.filterPayments === 'function') {
            searchInput.value = e.detail.value;
            window.filterPayments();
        }
    });
});
