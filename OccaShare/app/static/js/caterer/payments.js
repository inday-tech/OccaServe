/**
 * Caterer Payments Pro Interactions - Advanced Features & Theme Sync
 */
document.addEventListener('DOMContentLoaded', function() {
    // Global Pagination State
    const ROWS_PER_PAGE = 5;
    let currentPage = 1;
    let filteredRows = [];

    // Initialize
    const allRows = Array.from(document.querySelectorAll('.payment-row'));
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
        
        document.querySelectorAll('.action-dropdown-menu').forEach(menu => {
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

    // Close on outside click
    document.addEventListener('click', function(event) {
        if (!event.target.closest('.action-dropdown-container') && !event.target.closest('.export-dropdown-container')) {
            document.querySelectorAll('.action-dropdown-menu, #exportMenu').forEach(menu => {
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
            const rowId = row.querySelector('.payment-id').textContent.toLowerCase();
            const custName = row.querySelector('.cust-name').textContent.toLowerCase();
            const eventName = row.cells[2].textContent.toLowerCase();
            const rowStatus = row.querySelector('.badge-status-pro').textContent.toLowerCase();
            
            const matchesSearch = rowId.includes(query) || custName.includes(query) || eventName.includes(query);
            const matchesStatus = (status === 'all' || rowStatus === status);
            
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
                    row.querySelector('.badge-status-pro').textContent.trim().toUpperCase()
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
                    row.querySelector('.badge-status-pro').textContent.trim().toUpperCase()
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
                    row.querySelector('.badge-status-pro').textContent
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

            let verificationHtml = '';
            if (booking.payment_proof_url) {
                const verif = booking.payment_verification_data;
                const confidence = verif ? verif.confidence : 0;
                const statusColor = confidence > 70 ? '#10b981' : (confidence > 30 ? '#f59e0b' : '#ef4444');
                const statusIcon = confidence > 70 ? 'fa-shield-check' : (confidence > 30 ? 'fa-shield-exclamation' : 'fa-shield-slash');
                
                verificationHtml = `
                    <div class="verification-report-pro" style="margin-top: 1.5rem; padding: 1.5rem; background: #f8fafc; border: 2px solid ${statusColor}15; border-radius: 1.25rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                            <h4 style="margin: 0; color: #1e293b; display: flex; align-items: center; gap: 0.5rem;">
                                <i class="fas ${statusIcon}" style="color: ${statusColor};"></i> Legitimacy Report
                            </h4>
                            <span style="font-size: 0.8rem; font-weight: 700; color: ${statusColor}; background: ${statusColor}15; padding: 0.2rem 0.6rem; border-radius: 2rem;">
                                ${confidence}% Confidence
                            </span>
                        </div>
                        
                        ${verif ? `
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; font-size: 0.85rem;">
                                <div style="color: #64748b;">Amount Match:</div>
                                <div style="font-weight: 600; text-align: right; color: ${verif.amount_match ? '#10b981' : '#ef4444'}">
                                    ${verif.amount_match ? 'Matched ✓' : 'Mismatch ✗'}
                                </div>
                                <div style="color: #64748b;">Unique Receipt:</div>
                                <div style="font-weight: 600; text-align: right; color: ${!verif.is_duplicate_ref ? '#10b981' : '#ef4444'}">
                                    ${!verif.is_duplicate_ref ? 'Verified ✓' : 'Duplicate Found ✗'}
                                </div>
                                <div style="color: #64748b;">Extracted Ref:</div>
                                <div style="font-weight: 600; text-align: right; color: #1e293b;">
                                    ${verif.extracted_data.reference_no || 'Not found'}
                                </div>
                            </div>
                            
                            ${verif.flags && verif.flags.length > 0 ? `
                                <div style="margin-top: 1rem; padding: 0.75rem; background: #fff5f5; border: 1px solid #feb2b2; border-radius: 0.75rem;">
                                    <div style="font-weight: 700; color: #c53030; font-size: 0.75rem; margin-bottom: 0.25rem; text-transform: uppercase;">System Alerts</div>
                                    <ul style="margin: 0; padding-left: 1.25rem; font-size: 0.8rem; color: #9b2c2c;">
                                        ${verif.flags.map(f => `<li>${f}</li>`).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                        ` : `
                            <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 1rem;">Verification report not yet generated for this proof.</p>
                            <button class="btn-primary-pro" onclick="runManualVerification(${bookingId})" style="width: 100%; border: none; padding: 0.6rem; border-radius: 0.75rem; font-weight: 600; font-size: 0.85rem; cursor: pointer;">
                                <i class="fas fa-microchip"></i> Run AI Scan
                            </button>
                        `}
                        
                        <button onclick="showProof('${booking.payment_proof_url}', 'Proof - BK-${bookingId}')" style="width: 100%; margin-top: 0.75rem; background: white; border: 1px solid #e2e8f0; padding: 0.6rem; border-radius: 0.75rem; font-weight: 600; font-size: 0.85rem; cursor: pointer; color: #475569;">
                            <i class="fas fa-search-plus"></i> Enlarged Proof
                        </button>
                    </div>
                `;
            }

            content.innerHTML = `
                <div style="display: flex; flex-direction: column; gap: 1.25rem;">
                    <div style="text-align: center; margin-bottom: 0.5rem; padding: 1.25rem; background: #f8fafc; border-radius: 1.25rem; border: 1px solid #f1f5f9;">
                        <div style="font-size: 0.85rem; text-transform: uppercase; color: #64748b; font-weight: 700; margin-bottom: 0.35rem; letter-spacing: 0.05em;">Transaction Amount</div>
                        <div style="font-size: 2.25rem; font-weight: 800; color: var(--primary-color);">₱${parseFloat(booking.total_amount).toLocaleString()}</div>
                    </div>
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.75rem;"><span style="color: #64748b; font-weight: 600;">Customer</span><span style="font-weight: 700; color: #0f172a;">${booking.user.first_name} ${booking.user.last_name}</span></div>
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.75rem;"><span style="color: #64748b; font-weight: 600;">Booking Ref</span><span style="font-weight: 700; color: #0f172a;">BK-${bookingId}</span></div>
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.75rem;"><span style="color: #64748b; font-weight: 600;">Event Name</span><span style="font-weight: 700; color: #0f172a;">${booking.event_name || booking.event_type}</span></div>
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.75rem;"><span style="color: #64748b; font-weight: 600;">Payment Method</span><span style="font-weight: 700; color: #1e293b;">${booking.payment_method || 'Manual'}</span></div>
                    <div style="display: flex; justify-content: space-between;"><span style="color: #64748b; font-weight: 600;">Payment Status</span><span class="badge-status-pro ${booking.payment_status.toLowerCase()}">${booking.payment_status}</span></div>
                    
                    ${verificationHtml}
                </div>
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
        }, "Are you sure?", "Yes, Verify Payment");
    };
    
    window.archivePayment = function(bookingId) {
        const row = allRows.find(r => r.querySelector('.bk-id').textContent.trim() === `BK-${bookingId}`);
        const displayId = row ? row.querySelector('.payment-id').textContent.trim() : `PAY-${bookingId}`;
        
        window.showConfirm(`Archive payment <strong>${displayId}</strong>?<br><br>This will move the payment record to archives. You can still view it in the Archives section.`, function() {
            if (window.apiAction) {
                window.apiAction(`/caterer/bookings/${bookingId}/archive`, { method: "POST" })
                .then(res => {
                    if (res.status === 'success' && row) {
                        row.classList.add('fade-out-archive');
                        setTimeout(() => {
                            row.remove();
                            const total = document.getElementById('totalEntries');
                            if (total) total.innerText = parseInt(total.innerText) - 1;
                        }, 500);
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
        }, "Archive Payment", "Yes, Archive");
    };

    window.showProof = function(url, title) {
        const img = document.getElementById('proofModalImg');
        const h3 = document.getElementById('proofModalTitle');
        if (img) { 
            img.src = url; 
            if (h3) h3.innerText = title; 
            window.openModal('proofModal');
        }
    };
    window.closeProof = function() { 
        window.closeModal('proofModal');
    };
});
