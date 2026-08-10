/**
 * Caterer Payments Pro Interactions - Advanced Features & Theme Sync
 */
document.addEventListener('DOMContentLoaded', function() {
    // Global Pagination State
    const ROWS_PER_PAGE = 5;
    let currentPage = 1;
    let filteredRows = [];

    // Initialize
    const allRows = Array.from(document.querySelectorAll('#paymentsTableBody .premium-row'));
    filteredRows = allRows;
    showPage(1);

    // Pagination Logic
    function showPage(page) {
        const totalPages = Math.ceil(filteredRows.length / ROWS_PER_PAGE) || 1;
        if (page < 1) page = 1;
        if (page > totalPages) page = totalPages;
        currentPage = page;

        const startIdx = (page - 1) * ROWS_PER_PAGE;
        const endIdx = startIdx + ROWS_PER_PAGE;

        // Hide all rows first
        allRows.forEach(row => row.style.display = 'none');

        // Show scoped rows from filtered list
        filteredRows.slice(startIdx, endIdx).forEach(row => {
            row.style.display = '';
        });

        const noResults = document.getElementById('noPaymentResults');
        if (noResults) {
            noResults.style.display = filteredRows.length === 0 ? 'flex' : 'none';
        }

        renderPaginationControls(totalPages);
        updatePaginationInfo(startIdx, endIdx);
    }

    function renderPaginationControls(totalPages) {
        const container = document.getElementById('pageNumbers');
        const prevBtn = document.getElementById('prevPage');
        const nextBtn = document.getElementById('nextPage');
        
        if (!container) return;
        container.innerHTML = '';

        prevBtn.disabled = currentPage === 1;
        nextBtn.disabled = currentPage === totalPages || filteredRows.length === 0;

        prevBtn.onclick = () => showPage(currentPage - 1);
        nextBtn.onclick = () => showPage(currentPage + 1);

        if (filteredRows.length === 0) return;

        // Branding Primary Color for Active Page
        const primaryColor = getComputedStyle(document.documentElement).getPropertyValue('--primary-color').trim() || '#3b82f6';

        for (let i = 1; i <= totalPages; i++) {
            const btn = document.createElement('button');
            const isActive = i === currentPage;
            
            btn.className = `page-num-btn ${isActive ? 'active' : ''}`;
            btn.style.cssText = `
                width: 34px; height: 34px; display: flex; align-items: center; justify-content: center;
                border-radius: 0.5rem; border: 1px solid ${isActive ? primaryColor : '#e2e8f0'};
                background: ${isActive ? primaryColor : 'white'};
                color: ${isActive ? 'white' : '#475569'};
                font-size: 0.85rem; font-weight: 700; cursor: pointer; transition: all 0.2s;
            `;
            btn.innerText = i;
            btn.onclick = () => showPage(i);
            container.appendChild(btn);
        }
    }

    function updatePaginationInfo(startIdx, endIdx) {
        const start = document.getElementById('startRange');
        const end = document.getElementById('endRange');
        const total = document.getElementById('totalEntries');
        
        if (start) {
            start.innerText = filteredRows.length === 0 ? 0 : startIdx + 1;
            end.innerText = Math.min(endIdx, filteredRows.length);
            total.innerText = filteredRows.length;
        }
    }

    // Toggle Action Menu (Exact Bookings Logic)
    window.toggleActionMenu = function(id, event) {
        if (event) event.stopPropagation();
        
        document.querySelectorAll('.action-dropdown-menu, .pay-dropdown-menu').forEach(menu => {
            if (menu.id !== 'actionMenu-' + id) {
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
                setTimeout(() => element.style.display = "none", 200);
            }
        }
    };

    window.toggleExportMenu = function(event) {
        if (event) event.stopPropagation();
        const menu = document.getElementById('exportMenu');
        if (menu.style.display === "none" || menu.style.display === "") {
            menu.style.display = "block";
            setTimeout(() => menu.classList.add('active'), 10);
        } else {
            menu.classList.remove('active');
            setTimeout(() => menu.style.display = "none", 200);
        }
    };

    // Close on outside click or when an item is clicked
    document.addEventListener('click', function(event) {
        const isClickOutside = !event.target.closest('.action-dropdown-container') && 
                               !event.target.closest('.export-dropdown-container') && 
                               !event.target.closest('.pay-action-wrapper');
        const isClickItem = event.target.closest('.pay-dropdown-item') || event.target.closest('.action-dropdown-item');
        
        if (isClickOutside || isClickItem) {
            document.querySelectorAll('.action-dropdown-menu, .pay-dropdown-menu, #exportMenu').forEach(menu => {
                menu.classList.remove('active');
                setTimeout(() => menu.style.display = 'none', 200);
            });
        }
    });

    // Filtering
    window.filterPayments = function() {
        const query = document.getElementById('paymentSearch').value.toLowerCase();
        const status = document.getElementById('statusFilter').value.toLowerCase();
        
        filteredRows = allRows.filter(row => {
            const textContent = row.textContent.toLowerCase();
            const badgeEl = row.querySelector('.pay-status-badge');
            const rowStatus = badgeEl ? badgeEl.textContent.toLowerCase().trim() : '';
            
            const matchesSearch = textContent.includes(query);
            const matchesStatus = (status === 'all' || rowStatus.includes(status));
            
            return matchesSearch && matchesStatus;
        });
        
        currentPage = 1;
        showPage(1);
    };

    // Export PDF
    window.exportToPDF = function() {
        // More robust detection for jsPDF in different bundle formats
        const jsPDFLib = window.jspdf ? window.jspdf.jsPDF : window.jsPDF;
        
        if (!jsPDFLib) {
            window.showError("PDF Library not loaded yet. Please wait a moment and try again.", "Integration Error");
            return;
        }

        // For plugins like autoTable to work, window.jsPDF might be needed
        if (!window.jsPDF) window.jsPDF = jsPDFLib;

        try {
            const doc = new jsPDFLib({ orientation: 'landscape' });
            const primaryColor = getComputedStyle(document.documentElement).getPropertyValue('--primary-color').trim() || '#1e293b';

            doc.setFontSize(22);
            doc.setTextColor(primaryColor);
            doc.text('Payments & Earnings Report', 14, 20);
            
            doc.setFontSize(11);
            doc.setTextColor(100);
            doc.text(`Caterer: ${window.catererConfig?.businessName || 'Business Owner'} | Generated: ${new Date().toLocaleString()}`, 14, 28);

            let totalPrice = 0;
            const tableData = filteredRows.map(row => {
                const amtText = row.querySelector('.amount-pro').textContent.replace('₱', '').replace(/,/g, '').trim();
                const amt = parseFloat(amtText) || 0;
                totalPrice += amt;
                
                const custName = row.querySelector('.cust-name').textContent.trim();
                const eventName = row.cells[2].textContent.trim();
                
                return [
                    row.querySelector('.payment-id').textContent.trim(),
                    custName || 'Walk-in Customer', // Fallback for empty names
                    row.querySelector('.bk-id').textContent.trim(),
                    eventName || 'N/A',
                    `P${amt.toLocaleString()}`, 
                    row.cells[4].textContent.trim(),
                    row.cells[5].textContent.trim(),
                    row.querySelector('.premium-status-badge').textContent.trim().toUpperCase()
                ];
            });

            doc.autoTable({
                startY: 40,
                head: [['PAY ID', 'Customer', 'Booking ID', 'Event Name', 'Amount', 'Method', 'Date', 'Status']],
                body: tableData,
                theme: 'grid',
                headStyles: { 
                    fillColor: primaryColor, 
                    textColor: 255, 
                    fontSize: 10, 
                    fontStyle: 'bold',
                    halign: 'center'
                },
                styles: { 
                    fontSize: 9, 
                    cellPadding: 4, 
                    font: 'helvetica',
                    valign: 'middle',
                    lineColor: [226, 232, 240], // Lighter borders
                    lineWidth: 0.1
                },
                columnStyles: {
                    0: { cellWidth: 25, halign: 'center' }, // PAY ID
                    1: { cellWidth: 45 }, // Customer
                    2: { cellWidth: 25, halign: 'center' }, // BK ID
                    3: { cellWidth: 'auto' }, // Event
                    4: { cellWidth: 35, fontStyle: 'bold', halign: 'right' }, // Amount
                    5: { cellWidth: 25, halign: 'center' }, // Method
                    6: { cellWidth: 35, halign: 'center' }, // Date
                    7: { cellWidth: 30, halign: 'center' }  // Status
                },
                alternateRowStyles: { fillColor: [250, 252, 255] },
                margin: { left: 14, right: 14 }
            });

            // Add Total Summary at the bottom
            const finalY = doc.lastAutoTable.finalY + 10;
            doc.setFontSize(13);
            doc.setTextColor(primaryColor);
            doc.setFont('helvetica', 'bold');
            doc.text(`TOTAL EARNINGS: P${totalPrice.toLocaleString()}`, doc.internal.pageSize.width - 14, finalY, { align: 'right' });

            doc.save(`Payments_Report_${Date.now()}.pdf`);
            window.showSuccess("PDF report generated successfully.");
        } catch (e) {
            console.error("PDF Export failed", e);
            window.showError("Failed to generate PDF. Internal script error.");
        }
    };

    // Export Excel
    window.exportToExcel = function() {
        if (!window.XLSX) {
            window.showError("Excel Library not loaded yet.", "Internal Error");
            return;
        }
        try {
            let totalAmt = 0;
            const dataRows = filteredRows.map(row => {
                const amt = parseFloat(row.querySelector('.amount-pro').textContent.replace('₱', '').replace(/,/g, '').trim()) || 0;
                totalAmt += amt;
                return [
                    row.querySelector('.payment-id').textContent.trim(),
                    row.querySelector('.cust-name').textContent.trim() || 'Walk-in',
                    row.querySelector('.bk-id').textContent.trim(),
                    row.cells[2].textContent.trim(),
                    amt,
                    row.cells[4].textContent.trim(),
                    row.cells[5].textContent.trim(),
                    row.querySelector('.premium-status-badge').textContent.trim().toUpperCase()
                ];
            });

            const data = [
                ['Payment ID', 'Customer Name', 'Booking ID', 'Event Title', 'Amount (PHP)', 'Method', 'Transaction Date', 'Current Status'],
                ...dataRows,
                ['', '', '', 'TOTAL EARNINGS', totalAmt, '', '', '']
            ];

            const wb = XLSX.utils.book_new();
            const ws = XLSX.utils.aoa_to_sheet(data);
            
            // Auto-format columns
            ws['!cols'] = [
                {wch: 15}, {wch: 25}, {wch: 15}, {wch: 30}, {wch: 15}, {wch: 15}, {wch: 20}, {wch: 15}
            ];

            XLSX.utils.book_append_sheet(wb, ws, 'Payments');
            XLSX.writeFile(wb, `Payments_Export_${Date.now()}.xlsx`);
            window.showSuccess("Excel export successful.");
        } catch (e) {
            console.error("Excel Export failed", e);
            window.showError("Failed to generate Excel file.");
        }
    };

    // Export CSV
    window.exportToCSV = function() {
        try {
            let csv = 'Payment ID,Customer,Event,Amount,Method,Date,Status\n';
            filteredRows.forEach(row => {
                const data = [
                    row.querySelector('.payment-id').textContent,
                    row.querySelector('.cust-name').textContent,
                    row.cells[2].textContent,
                    row.querySelector('.amount-pro').textContent.replace('₱', '').replace(/,/g, ''),
                    row.cells[4].textContent,
                    row.cells[5].textContent,
                    row.querySelector('.premium-status-badge').textContent
                ];
                csv += data.map(v => `"${v}"`).join(',') + '\n';
            });

            const blob = new Blob([csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Payments_Report_${Date.now()}.csv`;
            a.click();
            window.showSuccess("CSV export successful.");
        } catch (e) {
            window.showError("Failed to download CSV.");
        }
    };

    // Modal Details
    window.viewPaymentDetails = async function(bookingId) {
        const modal = document.getElementById('detailsModal');
        const content = document.getElementById('detailsContent');
        
        // Initial Loading State
        content.innerHTML = '<div style="text-align: center; padding: 3rem;"><i class="fas fa-spinner fa-spin fa-3x" style="color: var(--primary-color);"></i><p style="margin-top: 1rem; color: #64748b;">Fetching details...</p></div>';
        window.openModal('detailsModal');

        try {
            const response = await fetch(`/caterer/api/bookings/${bookingId}/details`);
            const booking = await response.json();
            
            if (!response.ok) throw new Error(booking.detail || "Failed to load details");

            let documentsHtml = '';
            if (booking.payment_proof_url || booking.balance_proof_url || booking.contract_url) {
                documentsHtml = `
                    <div class="pay-docs-group">
                        <div class="pay-docs-title">Verified Documents</div>
                        <div class="pay-docs-actions">
                            ${booking.payment_proof_url || booking.balance_proof_url ? `
                                <button class="pay-doc-btn" onclick="showProof('${booking.balance_proof_url || booking.payment_proof_url}', 'Proof - BK-${bookingId}')">
                                    <i class="fas fa-image"></i> Payment Proof
                                </button>
                            ` : ''}
                            ${booking.contract_url ? `
                                <a href="${booking.contract_url}" target="_blank" class="pay-doc-btn">
                                    <i class="fas fa-file-contract"></i> Digital Contract
                                </a>
                            ` : ''}
                            ${booking.quotation_id ? `
                                <button type="button" class="pay-doc-btn" onclick="window.viewInvoice(${bookingId})">
                                    <i class="fas fa-receipt"></i> Official Invoice
                                </button>
                            ` : ''}
                        </div>
                    </div>
                `;
            }

            let verificationHtml = '';
            if (booking.payment_proof_url || booking.balance_proof_url) {
                const verif = booking.payment_verification_data;
                const confidence = verif ? verif.confidence : 0;
                const statusColor = confidence > 70 ? 'var(--color-success-500)' : (confidence > 30 ? 'var(--color-warning-500)' : 'var(--color-danger-500)');
                const statusBg = confidence > 70 ? 'var(--color-success-50)' : (confidence > 30 ? 'var(--color-warning-50)' : 'var(--color-danger-50)');
                const statusIcon = confidence > 70 ? 'fa-shield-check' : (confidence > 30 ? 'fa-shield-exclamation' : 'fa-shield-slash');
                
                verificationHtml = `
                    <div class="pay-verification-report" style="margin-top: var(--space-md);">
                        <div class="pay-verification-header">
                            <h4 class="pay-verification-title">
                                <i class="fas ${statusIcon}" style="color: ${statusColor};"></i> AI Integrity Scan
                            </h4>
                            <span class="pay-verification-confidence" style="color: ${statusColor}; background: ${statusBg};">
                                ${confidence}% Confidence
                            </span>
                        </div>
                        
                        ${verif ? `
                            <div class="pay-verification-grid">
                                <div class="pay-verification-key">Amount Match:</div>
                                <div class="pay-verification-val" style="color: ${verif.amount_match ? 'var(--color-success-600)' : 'var(--color-danger-600)'}">
                                    ${verif.amount_match ? 'Match ✓' : 'Mismatch ✗'}
                                </div>
                                <div class="pay-verification-key">Receipt Status:</div>
                                <div class="pay-verification-val" style="color: ${!verif.is_duplicate_ref ? 'var(--color-success-600)' : 'var(--color-danger-600)'}">
                                    ${!verif.is_duplicate_ref ? 'Unique ✓' : 'Duplicate ✗'}
                                </div>
                                <div class="pay-verification-key">Reference No:</div>
                                <div class="pay-verification-val" style="color: var(--color-neutral-900);">
                                    ${verif.extracted_data?.reference_no || 'N/A'}
                                </div>
                            </div>
                        ` : `
                            <p style="font-size: var(--text-xs); color: var(--color-neutral-500); margin-bottom: var(--space-sm);">No security scan data found for this proof.</p>
                            <button class="btn-review-kyc" onclick="runManualVerification(${bookingId})" style="width: 100%; padding: 0.5rem;">
                                <i class="fas fa-microchip"></i> Re-scan Proof
                            </button>
                        `}
                    </div>
                `;
            }

            content.innerHTML = `
                <div class="pay-details-summary">
                    <div class="pay-details-label-sm">Gross Subtotal</div>
                    <div class="pay-details-amount-lg">₱${parseFloat(booking.total_amount).toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
                </div>

                <div class="pay-details-grid">
                    <div class="pay-details-item-box">
                        <span class="pay-details-key-label">Client Name</span>
                        <span class="pay-details-val-text">${booking.user.first_name} ${booking.user.last_name}</span>
                    </div>
                    <div class="pay-details-item-box">
                        <span class="pay-details-key-label">Booking ID</span>
                        <span class="pay-details-val-text">#BK-${bookingId}</span>
                    </div>
                    <div class="pay-details-item-box">
                        <span class="pay-details-key-label">Event Type</span>
                        <span class="pay-details-val-text">${booking.event_type}</span>
                    </div>
                    <div class="pay-details-item-box">
                        <span class="pay-details-key-label">Payment Method</span>
                        <span class="pay-details-val-text">${booking.payment_method || 'Direct'}</span>
                    </div>
                </div>

                <div class="pay-breakdown-card">
                    <div class="pay-breakdown-hdr">
                        <i class="fas fa-chart-pie"></i> Financial Breakdown
                    </div>
                    <div class="pay-breakdown-row">
                        <span class="pay-breakdown-label">Gross Revenue</span>
                        <span class="pay-breakdown-val">₱${parseFloat(booking.total_amount).toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                    </div>
                    <div class="pay-breakdown-row">
                        <span class="pay-breakdown-label">Platform Fee (${booking.commission_rate}%)</span>
                        <span class="pay-breakdown-val negative">- ₱${parseFloat(booking.commission).toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                    </div>
                    <div class="pay-earnings-summary-line">
                        <span class="pay-earnings-label-text">Net Earnings</span>
                        <span class="pay-earnings-amount-val">₱${parseFloat(booking.net_earnings || (booking.total_amount - booking.commission)).toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                    </div>
                </div>
              </div>

                ${documentsHtml}
                
                ${verificationHtml}
            `;

        } catch (err) {
            console.error(err);
            content.innerHTML = `<div style="text-align: center; color: #ef4444; padding: 2rem;"><i class="fas fa-exclamation-triangle fa-2x"></i><p>${err.message}</p></div>`;
        }
    };

    window.runManualVerification = async function(bookingId) {
        const btn = event.currentTarget;
        const originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scanning...';
        
        try {
            const res = await window.apiAction(`/caterer/api/bookings/${bookingId}/verify-proof`, { method: "POST" });
            if (res && res.status === 'success') {
                window.viewPaymentDetails(bookingId); // Refresh details
            }
        } catch (err) {
            console.error(err);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalHtml;
            }
        }
    };

    window.closeDetailsModal = function() {
        window.closeModal('detailsModal');
    };

    window.verifyPayment = function(bookingId) {
        const row = allRows.find(r => r.querySelector('.bk-id').textContent.trim() === `BK-${bookingId}`);
        const amount = row ? row.querySelector('.amount-pro').textContent.trim() : "Unknown Amount";
        const custName = row ? row.querySelector('.cust-name').textContent.trim() : "Unknown Customer";
        
        window.showConfirm(`Verify payment of <strong>${amount}</strong> from <strong>${custName}</strong>?<br><br>This will mark the transaction BK-${bookingId} as fully paid and confirm the booking.`, function() {
            if (window.apiAction) {
                window.apiAction(`/caterer/payments/${bookingId}/confirm`, { 
                    method: "POST",
                    headers: { 'Content-Type': 'application/json' }
                })
                .then(res => {
                    if (res.status === 'success' && row) {
                        refreshPaymentSummary(); // Immediate refresh
                        row.classList.add('fade-out-archive');
                        setTimeout(() => {
                            row.remove();
                            // Update total entries count if needed
                            const total = document.getElementById('totalEntries');
                            if (total) total.innerText = parseInt(total.innerText) - 1;
                        }, 500);
                    }
                })
                .catch(err => console.error("Payment Verification Error:", err));
            } else {
                // Fallback if layout.js not fully loaded or helpers missing
                const f = document.createElement('form'); 
                f.method = 'POST'; 
                f.action = `/caterer/payments/${bookingId}/confirm`; 
                document.body.appendChild(f); 
                f.submit();
            }
        }, "Are you sure?", "Yes, Verify Payment", "success");
    };
    
    window.archivePayment = function(bookingId) {
        const row = document.getElementById('payment-row-' + bookingId);
        const displayId = 'BK-' + bookingId;

        window.showConfirm('This will move the payment record to archives. You can still view it in the Archives section.', function() {
            if (window.apiAction) {
                window.apiAction(`/caterer/bookings/${bookingId}/archive`, { method: 'POST' })
                    .then(res => {
                        if (res.status === 'success' || res.success) {
                            if (row) {
                                if (typeof refreshPaymentSummary === 'function') refreshPaymentSummary();
                                row.classList.add('fade-out-archive');
                                setTimeout(() => { 
                                    row.remove(); 
                                    const total = document.getElementById('totalEntries');
                                    if (total) total.innerText = parseInt(total.innerText) - 1;
                                }, 400);
                            } else {
                                location.reload();
                            }
                        } else {
                            if (window.showError) window.showError(res.error || 'Failed to archive payment');
                        }
                    })
                    .catch(err => console.error("Payment Archival Error:", err));
            } else {
                const f = document.createElement('form');
                f.method = 'POST';
                f.action = `/caterer/bookings/${bookingId}/archive?next=/caterer/payments`; 
                document.body.appendChild(f);
                f.submit();
            }
        });
    };

    // Real-time Summary Polling
    async function refreshPaymentSummary() {
        try {
            const response = await fetch('/caterer/api/payments/summary');
            const data = await response.json();
            
            if (data) {
                const formatter = new Intl.NumberFormat('en-PH', {
                    style: 'currency',
                    currency: 'PHP',
                    minimumFractionDigits: 2
                });

                // Update Withdraw Panel (Available Funds)
                const withdrawValue = document.querySelector('.pay-withdrawable-amount .value');
                if (withdrawValue) withdrawValue.innerText = formatter.format(data.ready_total);

                // Update Stats Grid
                const releasedValue = document.querySelector('.pay-stat-released .pay-stat-value');
                if (releasedValue) releasedValue.innerText = formatter.format(data.released_total);

                const escrowValue = document.querySelector('.pay-stat-escrow .pay-stat-value');
                if (escrowValue) escrowValue.innerText = formatter.format(data.escrow_total);

                const activeValue = document.querySelector('.pay-stat-active .pay-stat-value');
                if (activeValue) activeValue.innerText = data.active_count;

                // Disable/Enable Withdraw button based on amount
                const btnWithdraw = document.getElementById('btnWithdraw');
                if (btnWithdraw) {
                    btnWithdraw.disabled = data.ready_total <= 0;
                }
            }
        } catch (err) {
            console.warn("Summary refresh failed:", err);
        }
    }

    // Initial refresh and setup interval (every 30 seconds)
    refreshPaymentSummary();
    setInterval(refreshPaymentSummary, 30000);

    window.showProof = function(url, title) {
        const img = document.getElementById('proofModalImg');
        const h3 = document.getElementById('proofModalTitle');
        if (img) { 
            img.src = url; 
            if (h3) h3.innerText = title; 
            window.openModal('proofModal');
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
    window.openSettleModal = function() {
        window.openModal('settleModal');
    };

    window.closeSettleModal = function() {
        window.closeModal('settleModal');
    };

    window.submitSettleDues = async function() {
        const btn = document.getElementById('btnSubmitSettle');
        const originalHtml = btn.innerHTML;
        const period = document.getElementById('settlePeriod').value;
        const proofFile = document.getElementById('settleProofFile').files[0];

        if (!period || !proofFile) {
            window.showError("Please provide a billing period and upload a payment proof.", "Missing Details");
            return;
        }
        
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
        
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
                window.showSuccess("Proof of payment submitted successfully! The admin will verify it shortly.", "Settlement Requested");
                closeSettleModal();
                setTimeout(() => window.location.reload(), 2000);
            } else {
                throw new Error(data.detail || "Unable to submit settlement at this time.");
            }
        } catch (err) {
            console.error(err);
            window.showError(err.message, "System Error");
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    };

    // Listen to global header search
    window.addEventListener('globalSearch', function(e) {
        const hiddenInput = document.getElementById('paymentSearch');
        if (hiddenInput && typeof window.filterPayments === 'function') {
            hiddenInput.value = e.detail.value;
            window.filterPayments();
        }
    });

    window.closeProof = function() { 
        window.closeModal('proofModal');
    };

    // Modal Invoice View
    window.viewInvoice = async function(bookingId) {
        const modal = document.getElementById('invoiceModal');
        const content = document.getElementById('invoiceContent');
        
        content.innerHTML = '<div style="text-align: center; padding: 3rem;"><i class="fas fa-spinner fa-spin fa-3x" style="color: var(--primary-color);"></i><p style="margin-top:1rem; font-weight:700; color:var(--color-neutral-400);">GENERTING INVOICE...</p></div>';
        window.openModal('invoiceModal');

        try {
            const response = await fetch(`/caterer/api/bookings/${bookingId}/details`);
            const data = await response.json();

            const dateStr = new Date(data.created_at || Date.now()).toLocaleDateString('en-PH', { 
                year: 'numeric', month: 'long', day: 'numeric' 
            });

            content.innerHTML = `
                <div style="background: white; padding: 2.5rem; border-radius: var(--radius-md); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; border-bottom: 2px solid var(--color-neutral-50); padding-bottom: 1.5rem;">
                        <div>
                            <h2 style="margin: 0; color: var(--primary-color); font-weight: 800;">OccaServe</h2>
                            <p style="margin: 4px 0 0; font-size: 0.7rem; color: var(--color-neutral-400); font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;">Official Invoice</p>
                        </div>
                        <div style="text-align: right;">
                            <h3 style="margin: 0; font-size: 1.25rem; font-weight: 800; color: var(--color-neutral-900);">#BK-${bookingId}</h3>
                            <p style="margin: 4px 0 0; font-size: 0.85rem; color: var(--color-neutral-500); font-weight: 600;">Date: ${dateStr}</p>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-bottom: 2rem;">
                        <div>
                            <h4 style="font-size: 10px; text-transform: uppercase; color: var(--color-neutral-400); margin-bottom: 0.5rem; font-weight: 800; letter-spacing: 0.05em;">Client Details</h4>
                            <p style="margin: 0; font-weight: 700; font-size: 0.9rem; color: var(--color-neutral-900);">${data.user.first_name} ${data.user.last_name}</p>
                            <p style="margin: 2px 0; font-size: 0.8rem; color: var(--color-neutral-500);">${data.user.email}</p>
                        </div>
                        <div style="text-align: right;">
                            <h4 style="font-size: 10px; text-transform: uppercase; color: var(--color-neutral-400); margin-bottom: 0.5rem; font-weight: 800; letter-spacing: 0.05em;">Service Provider</h4>
                            <p style="margin: 0; font-weight: 700; font-size: 0.9rem; color: var(--color-neutral-900);">Verified Caterer</p>
                            <p style="margin: 2px 0; font-size: 0.8rem; color: var(--color-neutral-500);">OccaServe Certified Partner</p>
                        </div>
                    </div>

                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 2rem;">
                        <thead>
                            <tr style="background: var(--color-neutral-50);">
                                <th style="text-align: left; padding: 12px; font-size: 10px; font-weight: 800; color: var(--color-neutral-500); text-transform: uppercase; letter-spacing: 0.05em;">Description</th>
                                <th style="text-align: right; padding: 12px; font-size: 10px; font-weight: 800; color: var(--color-neutral-500); text-transform: uppercase; letter-spacing: 0.05em;">Amount</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td style="padding: 1.25rem 12px; border-bottom: 1px solid var(--color-neutral-50);">
                                    <div style="font-weight: 700; font-size: 0.9rem; color: var(--color-neutral-900);">${data.event_name || data.event_type}</div>
                                    <div style="font-size: 0.75rem; color: var(--color-neutral-400); margin-top: 4px;">Standard event package and platform service fee.</div>
                                </td>
                                <td style="text-align: right; padding: 1.25rem 12px; font-weight: 800; font-size: 0.9rem; color: var(--color-neutral-900); border-bottom: 1px solid var(--color-neutral-50);">₱${parseFloat(data.total_amount).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                            </tr>
                        </tbody>
                    </table>

                    <div style="margin-left: auto; width: 100%; max-width: 250px;">
                        <div style="display: flex; justify-content: space-between; padding: 8px 0; font-size: 0.85rem; color: var(--color-neutral-500); font-weight: 600;">
                            <span>Subtotal</span>
                            <span>₱${parseFloat(data.total_amount).toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 12px 0; font-weight: 900; font-size: 1.15rem; color: var(--primary-color); border-top: 2px solid var(--color-neutral-100); margin-top: 8px;">
                            <span>TOTAL PAID</span>
                            <span>₱${parseFloat(data.total_amount).toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                        </div>
                    </div>

                    <div style="margin-top: 3rem; padding-top: 1.5rem; border-top: 1px dashed var(--color-neutral-200); text-align: center;">
                        <p style="margin: 0; font-size: 0.7rem; color: var(--color-neutral-400); font-weight: 600; letter-spacing: 0.025em;">Thank you for using OccaServe. This is a computer-generated digital record.</p>
                    </div>
                </div>
            `;
        } catch (err) {
            console.error(err);
            content.innerHTML = '<p style="text-align: center; color: var(--color-danger-500); padding: 2rem; font-weight:700;">Failed to generate invoice. Please try again.</p>';
        }
    };

    window.printInvoice = function() {
        const content = document.getElementById('invoiceContent').innerHTML;
        const win = window.open('', '', 'height=700,width=900');
        win.document.write('<html><head><title>Invoice</title>');
        win.document.write('<style>body{font-family: sans-serif; padding: 40px; color: #1e293b;} table{width:100%; border-collapse:collapse;} th,td{padding:12px; border-bottom:1px solid #f1f5f9;} th{background:#f8fafc; text-transform:uppercase; font-size:10px; color:#64748b;}</style>');
        win.document.write('</head><body>');
        win.document.write(content);
        win.document.write('</body></html>');
        win.document.close();
        win.print();
    };

    window.closeInvoiceModal = function() {
        window.closeModal('invoiceModal');
    };
});
