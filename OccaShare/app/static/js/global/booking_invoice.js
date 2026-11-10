(function () {
    const money = value => `₱${Number(value || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    const safeDate = value => {
        if (!value) return '—';
        const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/);
        if (match) {
            return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
                .toLocaleDateString('en-PH', { year: 'numeric', month: 'short', day: 'numeric' });
        }
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('en-PH', { year: 'numeric', month: 'short', day: 'numeric' });
    };
    const displayTime = value => {
        const text = String(value || '').trim();
        if (!text) return '';
        const match = text.match(/^(\d{1,2}):(\d{2})(?::\d{2})?$/);
        if (!match) return text;
        const hour = Number(match[1]);
        const minute = Number(match[2]);
        if (hour > 23 || minute > 59) return text;
        return `${hour % 12 || 12}:${match[2]} ${hour >= 12 ? 'PM' : 'AM'}`;
    };

    function element(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function buildTable(headers, rows, className) {
        const table = element('table', className);
        const head = table.createTHead().insertRow();
        headers.forEach(label => head.appendChild(element('th', '', label)));
        const body = table.createTBody();
        rows.forEach(values => {
            const row = body.insertRow();
            values.forEach((value, index) => {
                const cell = row.insertCell();
                cell.textContent = value;
                if (index === values.length - 1) cell.className = 'invoice-number-cell';
            });
        });
        return table;
    }

    function renderInvoice(host, data) {
        host.replaceChildren();
        const events = Array.isArray(data.events) ? data.events : [];
        const section = element('section', 'booking-invoice-sheet');
        section.id = 'bookingInvoicePreview';
        const heading = element('div', 'booking-invoice-heading');
        const brand = element('div', 'booking-invoice-brand');
        brand.append(element('span', 'booking-invoice-mark', 'O'), element('span', '', 'OccaServe'));
        heading.append(brand, element('span', 'booking-invoice-label', 'BOOKING INVOICE'));
        section.appendChild(heading);

        const identity = element('div', 'booking-invoice-identity');
        identity.append(element('h3', '', data.caterer_name || 'Caterer'), element('p', '', `Invoice for booking ${data.booking_ref || data.booking_id}`));
        const generatedAt = safeDate(data.generated_at);
        identity.append(element('span', 'booking-invoice-date', `Generated ${generatedAt}`));
        section.appendChild(identity);

        const facts = element('div', 'booking-invoice-facts');
        const eventSummary = events.length
            ? events.map((event, index) => {
                const parts = [event.type || 'Event'];
                if (event.package_name) parts.push(event.package_name);
                if (event.guest_count) parts.push(`${Number(event.guest_count).toLocaleString()} guests`);
                return `${index + 1}. ${event.name || event.type || 'Event'} — ${parts.join(' · ')}`;
            }).join('\n')
            : `${data.event_name || data.event_type || 'Event'}${data.guest_count ? ` · ${Number(data.guest_count).toLocaleString()} guests` : ''}`;
        [
            ['Bill to', data.customer_name || 'Customer'],
            ['Booking reference', data.booking_ref || `BK-${data.booking_id}`],
            ['Events', eventSummary],
            ['Event date', events.length
                ? events.map((event, index) => `${index + 1}. ${event.name || event.type || 'Event'}: ${safeDate(event.date)}${displayTime(event.time) ? ` · Ingress ${displayTime(event.time)}` : ''}${displayTime(event.end_time) ? ` · Egress ${displayTime(event.end_time)}` : ''}`).join('\n')
                : `${safeDate(data.event_date)}${displayTime(data.event_time) ? ` · Ingress ${displayTime(data.event_time)}` : ''}${displayTime(data.event_end_time) ? ` · Egress ${displayTime(data.event_end_time)}` : ''}`],
        ].forEach(([label, value]) => {
            const fact = element('div', 'booking-invoice-fact');
            fact.append(element('span', '', label), element('strong', '', value));
            facts.appendChild(fact);
        });
        section.appendChild(facts);

        section.append(element('h4', 'booking-invoice-section-title', 'Price breakdown'));
        const lines = Array.isArray(data.line_items) ? data.line_items : [];
        if (lines.length) {
            section.appendChild(buildTable(
                ['Event / charge', 'Amount'],
                lines.map(line => [line.description || 'Booking charge', money(line.amount)]),
                'booking-invoice-table'
            ));
        } else {
            section.appendChild(element('p', 'booking-invoice-empty', 'No itemized charges have been saved for this booking yet.'));
        }

        const totals = element('div', 'booking-invoice-totals');
        [
            ['Total amount', money(data.total_amount), 'invoice-total'],
            ['Verified payments', money(data.verified_paid), ''],
            ['Remaining balance', money(data.remaining_balance), 'invoice-balance'],
            ['Payment status', data.payment_status || 'Unpaid', ''],
        ].forEach(([label, value, className]) => {
            const row = element('div', `booking-invoice-total-row ${className}`.trim());
            row.append(element('span', '', label), element('strong', '', value));
            totals.appendChild(row);
        });
        section.appendChild(totals);

        section.append(element('h4', 'booking-invoice-section-title', 'Verified payment history'));
        const payments = Array.isArray(data.payments) ? data.payments : [];
        if (payments.length) {
            section.appendChild(buildTable(
                ['Date', 'Payment', 'Method / reference', 'Amount'],
                payments.map(payment => [safeDate(payment.date), payment.type || 'Payment', [payment.method, payment.reference].filter(Boolean).join(' · ') || '—', money(payment.amount)]),
                'booking-invoice-table booking-invoice-payment-table'
            ));
        } else {
            section.appendChild(element('p', 'booking-invoice-empty', 'No verified payments recorded yet.'));
        }
        section.append(element('p', 'booking-invoice-note', 'This invoice reflects the current booking total and verified payment records. Unverified submissions are not counted as paid.'));
        host.appendChild(section);

        const actions = element('div', 'booking-invoice-actions');
        const preview = element('button', 'booking-invoice-button booking-invoice-button-light', 'Preview');
        preview.type = 'button';
        preview.addEventListener('click', () => section.scrollIntoView({ behavior: 'smooth', block: 'start' }));
        const download = element('button', 'booking-invoice-button', 'Download PDF');
        download.type = 'button';
        download.addEventListener('click', () => downloadPdf(data));
        const print = element('button', 'booking-invoice-button booking-invoice-button-light', 'Print');
        print.type = 'button';
        print.addEventListener('click', () => printInvoice(section));
        actions.append(preview, download, print);
        host.appendChild(actions);
    }

    function loadScript(src, test) {
        if (test()) return Promise.resolve();
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = () => test() ? resolve() : reject(new Error('PDF library did not initialize.'));
            script.onerror = () => reject(new Error('Could not load the PDF library.'));
            document.head.appendChild(script);
        });
    }

    async function downloadPdf(data) {
        try {
            await loadScript('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js', () => Boolean(window.jspdf?.jsPDF));
            await loadScript('https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.28/jspdf.plugin.autotable.min.js', () => Boolean(window.jspdf?.jsPDF?.API?.autoTable));
            const Pdf = window.jspdf.jsPDF;
            const pdf = new Pdf({ unit: 'pt', format: 'a4' });
            pdf.setTextColor(15, 23, 42);
            pdf.setFontSize(20); pdf.setFont(undefined, 'bold'); pdf.text('OccaServe', 42, 48);
            pdf.setFontSize(10); pdf.setFont(undefined, 'normal'); pdf.setTextColor(100, 116, 139); pdf.text('BOOKING INVOICE', 42, 66);
            pdf.setDrawColor(234, 88, 12); pdf.line(42, 78, 553, 78);
            pdf.setTextColor(15, 23, 42); pdf.setFontSize(11); pdf.setFont(undefined, 'bold');
            pdf.text(data.caterer_name || 'Caterer', 42, 102);
            pdf.setFont(undefined, 'normal'); pdf.setFontSize(9);
            pdf.text(`Invoice for booking ${data.booking_ref || data.booking_id}`, 42, 119);
            pdf.text(`Generated ${safeDate(data.generated_at)}`, 42, 134);
            const invoiceEvents = Array.isArray(data.events) ? data.events : [];
            const invoiceEventLabel = invoiceEvents.length
                ? invoiceEvents.map(event => `${event.name || event.type || 'Event'} — ${event.package_name || 'Package'} (${Number(event.guest_count || 0).toLocaleString()} guests)`).join('\n')
                : data.event_name || data.event_type || 'Event';
            const invoiceDateLabel = invoiceEvents.length
                ? invoiceEvents.map(event => `${event.name || 'Event'}: ${safeDate(event.date)}${displayTime(event.time) ? ` · Ingress ${displayTime(event.time)}` : ''}${displayTime(event.end_time) ? ` · Egress ${displayTime(event.end_time)}` : ''}`).join('\n')
                : safeDate(data.event_date);
            pdf.autoTable({ startY: 149, theme: 'grid', head: [['Bill to', 'Booking', 'Event', 'Event date']], body: [[data.customer_name || 'Customer', data.booking_ref || `BK-${data.booking_id}`, invoiceEventLabel, invoiceDateLabel]], styles: { fontSize: 8, cellPadding: 6, overflow: 'linebreak' }, headStyles: { fillColor: [255, 247, 237], textColor: [154, 52, 18] } });
            const pdfMoney = value => `PHP ${Number(value || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            const lines = (data.line_items || []).map(item => [item.description || 'Booking charge', pdfMoney(item.amount)]);
            if (lines.length) {
                pdf.autoTable({ startY: pdf.lastAutoTable.finalY + 14, theme: 'grid', head: [['Price breakdown', 'Amount']], body: lines, styles: { fontSize: 9, cellPadding: 6 }, headStyles: { fillColor: [234, 88, 12] }, columnStyles: { 1: { halign: 'right' } } });
            } else {
                pdf.setFontSize(9); pdf.setTextColor(100, 116, 139); pdf.text('No itemized charges have been saved for this booking yet.', 42, pdf.lastAutoTable.finalY + 28);
                pdf.lastAutoTable = { finalY: pdf.lastAutoTable.finalY + 34 };
            }
            pdf.autoTable({ startY: pdf.lastAutoTable.finalY + 12, theme: 'plain', body: [['Total amount', pdfMoney(data.total_amount)], ['Verified payments', pdfMoney(data.verified_paid)], ['Remaining balance', pdfMoney(data.remaining_balance)], ['Payment status', data.payment_status || 'Unpaid']], styles: { fontSize: 9, cellPadding: 4 }, columnStyles: { 1: { halign: 'right', fontStyle: 'bold' } }, tableWidth: 240, margin: { left: 313 } });
            if ((data.payments || []).length) {
                pdf.autoTable({ startY: pdf.lastAutoTable.finalY + 10, theme: 'grid', head: [['Verified payment history', 'Payment', 'Method / reference', 'Amount']], body: data.payments.map(payment => [safeDate(payment.date), payment.type || 'Payment', [payment.method, payment.reference].filter(Boolean).join(' · ') || '—', pdfMoney(payment.amount)]), styles: { fontSize: 8, cellPadding: 5 }, headStyles: { fillColor: [241, 245, 249], textColor: [51, 65, 85] } });
            } else {
                pdf.setFontSize(8); pdf.setTextColor(100, 116, 139); pdf.text('No verified payments recorded yet.', 42, pdf.lastAutoTable.finalY + 18);
                pdf.lastAutoTable = { finalY: pdf.lastAutoTable.finalY + 24 };
            }
            pdf.setFontSize(8); pdf.setTextColor(100, 116, 139); pdf.text('Unverified payment submissions are not counted as paid.', 42, Math.min(pdf.lastAutoTable.finalY + 18, 805));
            pdf.save(`OccaServe-Invoice-${String(data.booking_ref || data.booking_id).replace(/[^a-z0-9-]/gi, '-')}.pdf`);
        } catch (error) {
            if (window.showToast) window.showToast(error.message || 'PDF download is unavailable.', 'error');
            else window.alert(error.message || 'PDF download is unavailable.');
        }
    }

    function printInvoice(section) {
        const printWindow = window.open('', '_blank');
        if (!printWindow) {
            window.alert('Allow pop-ups to print the invoice.');
            return;
        }
        printWindow.document.open();
        printWindow.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>OccaServe Booking Invoice</title><link rel="stylesheet" href="${window.location.origin}/static/css/global/booking_invoice.css"><style>@page{size:A4;margin:16mm}body{background:#fff!important;padding:0!important}.booking-invoice-actions{display:none!important}.booking-invoice-sheet{box-shadow:none!important;border:0!important}</style></head><body>${section.outerHTML}<script>window.onload=()=>{window.print();window.onafterprint=()=>window.close()}<\/script></body></html>`);
        printWindow.document.close();
    }

    async function load(host, bookingId, silent = false) {
        if (!host || !bookingId) return;
        if (host.dataset.invoiceLoading === 'true') return;
        host.dataset.invoiceLoading = 'true';
        if (!silent) host.replaceChildren(element('p', 'booking-invoice-loading', 'Loading the latest invoice and verified payments…'));
        try {
            const response = await fetch(`/bookings/${encodeURIComponent(bookingId)}/invoice-data`, { headers: { Accept: 'application/json' }, cache: 'no-store' });
            const result = await response.json();
            if (!response.ok || !result.success || !result.invoice) throw new Error(result.detail || 'Invoice details could not be loaded.');
            renderInvoice(host, result.invoice);
        } catch (error) {
            host.replaceChildren(element('p', 'booking-invoice-error', error instanceof Error ? error.message : 'Invoice details could not be loaded.'));
        } finally {
            host.dataset.invoiceLoading = 'false';
        }
    }

    window.setInterval(() => {
        const host = document.getElementById('bookingInvoiceHost');
        if (!host) return;
        const customerPane = host.closest('#bkPaneInvoice');
        const catererPane = host.closest('#btab-invoice');
        const adminPane = host.closest('#adminInvoicePane');
        const active = customerPane?.classList.contains('is-active')
            || catererPane?.classList.contains('active')
            || (adminPane && adminPane.style.display !== 'none');
        const bookingId = customerPane?.dataset.bookingId || catererPane?.dataset.bookingId || adminPane?.dataset.bookingId;
        if (active && bookingId) load(host, bookingId, true);
    }, 30000);

    window.OccaBookingInvoice = { load };
})();
