(function () {
    'use strict';

    const libraries = {
        xlsx: 'https://cdn.jsdelivr.net/npm/exceljs@4.4.0/dist/exceljs.min.js',
        pdf: 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js',
        table: 'https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.28/jspdf.plugin.autotable.min.js',
        docx: [
            'https://cdn.jsdelivr.net/npm/docx@8.5.0/dist/index.umd.js',
            'https://unpkg.com/docx@8.5.0/dist/index.umd.js'
        ]
    };
    const loadPromises = new Map();

    function loadScript(src) {
        if (loadPromises.has(src)) return loadPromises.get(src);
        const existing = Array.from(document.scripts).find(script => script.src === src);
        const promise = existing ? Promise.resolve() : new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = () => {
                script.remove();
                loadPromises.delete(src);
                reject(new Error('Export library failed to load.'));
            };
            document.head.appendChild(script);
        });
        loadPromises.set(src, promise);
        return promise;
    }

    async function loadLibrary(sources) {
        let lastError;
        for (const source of sources) {
            try {
                await loadScript(source);
                return;
            } catch (error) {
                lastError = error;
            }
        }
        throw lastError || new Error('Export library failed to load.');
    }

    function normalizeSections(config) {
        const sections = config.sections || [{ title: '', columns: config.columns || [], rows: config.rows || [] }];
        return sections.map(section => ({
            title: section.title || '',
            columns: (section.columns || []).map((column, index) => typeof column === 'string'
                ? { label: column, key: index } : column),
            rows: Array.isArray(section.rows) ? section.rows : []
        }));
    }

    function valueFor(row, column, index) {
        if (Array.isArray(row)) return row[index] ?? '';
        return row && typeof row === 'object' ? (row[column.key] ?? '') : '';
    }

    function safeText(value) {
        return String(value == null ? '' : value);
    }

    function escapeHtml(value) {
        return safeText(value).replace(/[&<>"']/g, character => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        })[character]);
    }

    function formatCurrency(value) {
        if (typeof value === 'string' && value.includes('₱')) return value;
        const amount = typeof value === 'number' ? value : Number(String(value).replace(/[^0-9.-]+/g, ''));
        return Number.isFinite(amount)
            ? `₱${amount.toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            : safeText(value);
    }

    function parseNumericValue(value) {
        if (typeof value === 'number') return value;
        const cleaned = String(value || '').replace(/[^0-9.-]+/g, '');
        const num = parseFloat(cleaned);
        return Number.isFinite(num) ? num : null;
    }

    // Status Pill Badge Detection matching OccaServe template
    function getStatusBadgeHtml(value) {
        if (value == null) return null;
        const str = String(value).trim();
        const low = str.toLowerCase();

        // Fully Paid / Confirmed / Completed
        if (/^(fully[ -]?paid|confirmed|completed|paid|active|approved|verified)$/i.test(low)) {
            return `<span class="occa-status-pill status-fully-paid">${escapeHtml(str)}</span>`;
        }
        // Partially Paid / Pending / Review
        if (/^(partially[ -]?paid|partial|pending|in[ -]?progress|under[ -]?review|review|draft|resubmit)$/i.test(low)) {
            return `<span class="occa-status-pill status-partially-paid">${escapeHtml(str)}</span>`;
        }
        // Cancelled / Rejected / Failed / Unpaid
        if (/^(cancelled|rejected|failed|unpaid|disputed|declined|terminated)$/i.test(low)) {
            return `<span class="occa-status-pill status-cancelled">${escapeHtml(str)}</span>`;
        }
        return null;
    }

    // Centered Report Header Block matching image
    function appendReportHeader(sheet, config, totalRecords) {
        const header = document.createElement('div');
        header.className = 'occa-report-header';

        // 1. Centered Brand Logo
        const logoWrap = document.createElement('div');
        logoWrap.className = 'occa-report-logo-wrap';
        const logoImg = document.createElement('img');
        logoImg.src = '/static/images/occaserve_logo_clean.png';
        logoImg.alt = 'OccaServe';
        logoImg.className = 'occa-report-brand-logo';
        logoImg.onerror = function () {
            this.src = '/static/images/brand_icon.png';
        };
        logoWrap.appendChild(logoImg);
        header.appendChild(logoWrap);

        // 2. OFFICIAL REPORT Divider
        const badge = document.createElement('div');
        badge.className = 'occa-report-official-badge';
        badge.textContent = 'OFFICIAL REPORT';
        header.appendChild(badge);

        // 3. Report Title (e.g. Bookings Database Report)
        const titleEl = document.createElement('h1');
        titleEl.className = 'occa-report-title';
        titleEl.textContent = config.title || 'Bookings Database Report';
        header.appendChild(titleEl);

        // 4. Metadata Line (Calendar icon | Date | matching count)
        const metaLine = document.createElement('div');
        metaLine.className = 'occa-report-meta-line';
        const dateStr = config.generatedAt || new Date().toLocaleString('en-US', {
            month: 'short', day: '2-digit', year: 'numeric',
            hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true
        });
        const countText = `${totalRecords} bookings matching current search and filters`;
        metaLine.innerHTML = `<i class="fas fa-calendar-alt" aria-hidden="true"></i> Generated on ${dateStr} <span class="occa-report-meta-sep">|</span> ${countText}`;
        header.appendChild(metaLine);

        // 5. Orange Divider Bar above the table
        const orangeBar = document.createElement('div');
        orangeBar.className = 'occa-report-orange-divider';
        header.appendChild(orangeBar);

        sheet.appendChild(header);
    }

    function appendReportFooter(sheet) {
        const orangeBar = document.createElement('div');
        orangeBar.className = 'occa-report-footer-divider';
        sheet.appendChild(orangeBar);

        const footerRow = document.createElement('div');
        footerRow.className = 'occa-report-footer-row';
        footerRow.innerHTML = `
            <div class="occa-report-footer-left">
                <span class="occa-report-footer-brand">OccaServe</span>
                <span class="occa-report-footer-sep">|</span>
                <span>Confidential Platform Report</span>
            </div>
            <div class="occa-report-footer-right">
                Page 1 of 1
            </div>
        `;
        sheet.appendChild(footerRow);
    }

    function renderFormatPreview(config, sections, format) {
        const sheet = document.createElement('article');
        sheet.className = `occa-export-sheet occa-export-sheet-${format}`;
        const totalRecords = sections.reduce((sum, s) => sum + s.rows.length, 0);

        appendReportHeader(sheet, config, totalRecords);

        sections.forEach(section => {
            const sectionEl = document.createElement('section');
            sectionEl.className = 'occa-export-section';

            if (!section.columns.length || !section.rows.length) {
                const empty = document.createElement('div');
                empty.className = 'occa-export-empty';
                empty.innerHTML = `<i class="fas fa-inbox fa-2x" style="display:block;margin-bottom:8px;color:#94a3b8;"></i> ${section.rows.length ? 'No columns available.' : 'No matching records found for this report.'}`;
                sectionEl.appendChild(empty);
            } else {
                const wrap = document.createElement('div');
                wrap.className = 'occa-report-table-wrap';
                const table = document.createElement('table');
                table.className = 'occa-report-table';

                if (format === 'xlsx') {
                    table.style.minWidth = `${Math.max(760, section.columns.length * 125)}px`;
                } else {
                    table.style.width = '100%';
                }

                const head = document.createElement('thead');
                const headRow = document.createElement('tr');
                section.columns.forEach(column => {
                    const cell = document.createElement('th');
                    cell.textContent = column.label;
                    headRow.appendChild(cell);
                });
                head.appendChild(headRow);

                const body = document.createElement('tbody');
                section.rows.forEach(row => {
                    const tr = document.createElement('tr');
                    section.columns.forEach((column, index) => {
                        const td = document.createElement('td');
                        const value = valueFor(row, column, index);
                        const labelLow = String(column.label || '').toLowerCase();
                        const isCurrency = column.type === 'currency' ||
                            /amount|price|total|revenue|fee|dues/i.test(labelLow);
                        const isStatus = /status|payment/i.test(labelLow);
                        const isBookingId = /booking[ -]?id|reference|ref/i.test(labelLow);

                        if (isCurrency) {
                            td.textContent = formatCurrency(value);
                            td.classList.add('is-currency');
                        } else if (isStatus) {
                            td.classList.add('is-status');
                            const badgeHtml = getStatusBadgeHtml(value);
                            if (badgeHtml) {
                                td.innerHTML = badgeHtml;
                            } else {
                                td.textContent = safeText(value);
                            }
                        } else {
                            if (isBookingId) td.classList.add('is-booking-id');
                            // Format multi-line event text nicely
                            const textVal = safeText(value);
                            if (textVal.includes('\n')) {
                                td.innerHTML = textVal.split('\n').map(l => escapeHtml(l)).join('<br>');
                            } else {
                                td.textContent = textVal;
                            }
                        }
                        tr.appendChild(td);
                    });
                    body.appendChild(tr);
                });

                table.append(head, body);
                wrap.appendChild(table);
                sectionEl.appendChild(wrap);
            }
            sheet.appendChild(sectionEl);
        });

        appendReportFooter(sheet);
        return sheet;
    }

    function createPreview(config) {
        const sections = normalizeSections(config);
        const overlay = document.createElement('div');
        overlay.className = 'occa-export-overlay';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');
        overlay.setAttribute('aria-label', `${config.title || 'Report'} preview`);

        const dialog = document.createElement('div');
        dialog.className = 'occa-export-dialog';

        // Top Toolbar
        const toolbar = document.createElement('div');
        toolbar.className = 'occa-export-toolbar';
        toolbar.innerHTML = `
            <div class="occa-export-brand">
                <img src="/static/images/occaserve_logo_clean.png" alt="OccaServe" onerror="this.src='/static/images/brand_icon.png'">
                <div>
                    <span>OCCASERVE REPORT</span>
                    <strong>${escapeHtml(config.title || 'Bookings Database Report')}</strong>
                </div>
            </div>
        `;
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'occa-export-close';
        closeButton.setAttribute('aria-label', 'Close preview');
        closeButton.innerHTML = '<i class="fas fa-times" aria-hidden="true"></i>';
        toolbar.appendChild(closeButton);

        const content = document.createElement('main');
        content.className = 'occa-export-content';

        // Segmented Format Navigation (PDF, Excel, Word)
        const formatNav = document.createElement('nav');
        formatNav.className = 'occa-export-formats';
        formatNav.setAttribute('aria-label', 'Preview format');

        const formatOptions = [
            ['pdf', 'PDF Document', '.pdf', 'fa-file-pdf'],
            ['xlsx', 'Excel Sheet', '.xlsx', 'fa-file-excel'],
            ['word', 'Word Document', '.docx', 'fa-file-word']
        ];
        const previewHost = document.createElement('div');
        previewHost.className = 'occa-export-preview-host';
        const formatButtons = new Map();
        const formatLabels = new Map(formatOptions.map(([format, label, extension]) => [format, { label, extension }]));
        let selectedFormat = 'pdf';
        let currentZoom = 1.0;

        formatOptions.forEach(([format, label, extension, icon]) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'occa-export-format';
            button.setAttribute('aria-pressed', 'false');
            button.innerHTML = `<i class="fas ${icon}" aria-hidden="true"></i><span>${label}</span><small>${extension}</small>`;
            button.addEventListener('click', () => selectFormat(format));
            formatButtons.set(format, button);
            formatNav.appendChild(button);
        });

        // Interactive Canvas Bar with Meta & Zoom Controls
        const canvasBar = document.createElement('div');
        canvasBar.className = 'occa-export-canvas-bar';

        const totalRecords = sections.reduce((sum, s) => sum + s.rows.length, 0);
        const canvasMeta = document.createElement('div');
        canvasMeta.className = 'occa-export-canvas-meta';
        canvasMeta.innerHTML = `
            <span class="occa-meta-pill"><i class="fas fa-file-lines" aria-hidden="true"></i> A4 Landscape</span>
            <span class="occa-meta-pill"><i class="fas fa-database" aria-hidden="true"></i> ${totalRecords} Records</span>
        `;

        const zoomControls = document.createElement('div');
        zoomControls.className = 'occa-export-zoom-controls';
        zoomControls.innerHTML = `
            <button type="button" class="occa-zoom-btn" id="occaZoomOut" title="Zoom Out" aria-label="Zoom Out"><i class="fas fa-minus" aria-hidden="true"></i></button>
            <span class="occa-zoom-label" id="occaZoomVal" title="Click to reset zoom">100%</span>
            <button type="button" class="occa-zoom-btn" id="occaZoomIn" title="Zoom In" aria-label="Zoom In"><i class="fas fa-plus" aria-hidden="true"></i></button>
            <button type="button" class="occa-zoom-reset" id="occaZoomFit" title="Fit to width">Fit</button>
        `;
        canvasBar.append(canvasMeta, zoomControls);

        function applyZoom(scale) {
            currentZoom = Math.min(1.5, Math.max(0.65, scale));
            const zoomValEl = zoomControls.querySelector('#occaZoomVal');
            if (zoomValEl) zoomValEl.textContent = `${Math.round(currentZoom * 100)}%`;
            const activeSheet = previewHost.querySelector('.occa-export-sheet');
            if (activeSheet) {
                activeSheet.style.transform = `scale(${currentZoom})`;
            }
        }

        zoomControls.querySelector('#occaZoomOut').addEventListener('click', () => applyZoom(currentZoom - 0.1));
        zoomControls.querySelector('#occaZoomIn').addEventListener('click', () => applyZoom(currentZoom + 0.1));
        zoomControls.querySelector('#occaZoomVal').addEventListener('click', () => applyZoom(1.0));
        zoomControls.querySelector('#occaZoomFit').addEventListener('click', () => {
            const hostWidth = previewHost.clientWidth - 40;
            if (hostWidth > 300) {
                applyZoom(hostWidth / 1060);
            } else {
                applyZoom(1.0);
            }
        });

        const status = document.createElement('div');
        status.className = 'occa-export-status';
        status.setAttribute('role', 'status');
        status.setAttribute('aria-live', 'polite');

        function selectFormat(format) {
            selectedFormat = format;
            formatButtons.forEach((button, key) => {
                button.classList.toggle('is-active', key === format);
                button.setAttribute('aria-pressed', String(key === format));
            });
            const option = formatLabels.get(format);
            downloadButton.innerHTML = `<i class="fas fa-download" aria-hidden="true"></i><span>Download ${option.label}</span>`;
            previewHost.replaceChildren(renderFormatPreview(config, sections, format));
            applyZoom(currentZoom);
            previewHost.scrollTop = 0;
            previewHost.scrollLeft = 0;
        }

        content.replaceChildren(formatNav, canvasBar, previewHost);

        // Action Buttons in Footer
        const actions = document.createElement('div');
        actions.className = 'occa-export-actions';

        const printButton = document.createElement('button');
        printButton.type = 'button';
        printButton.className = 'occa-export-print';
        printButton.dataset.action = 'print';
        printButton.innerHTML = '<i class="fas fa-print" aria-hidden="true"></i><span>Print</span>';
        printButton.addEventListener('click', () => printReport(config, sections));
        actions.appendChild(printButton);

        if (config.textDownload) {
            const textButton = document.createElement('button');
            textButton.type = 'button';
            textButton.className = 'occa-export-text';
            textButton.innerHTML = '<i class="fas fa-file-lines" aria-hidden="true"></i><span>TXT Log</span>';
            textButton.addEventListener('click', () => downloadText(config, sections));
            actions.appendChild(textButton);
        }

        const downloadButton = document.createElement('button');
        downloadButton.type = 'button';
        downloadButton.className = 'occa-export-download';
        downloadButton.addEventListener('click', () => download(config, sections, selectedFormat, downloadButton, status, formatLabels));
        actions.appendChild(downloadButton);

        const footer = document.createElement('div');
        footer.className = 'occa-export-footer';
        const footerNote = document.createElement('span');
        footerNote.className = 'occa-export-footer-note';
        footerNote.innerHTML = '<i class="fas fa-shield-halved" aria-hidden="true"></i> Official OccaServe platform report generated from live database records.';
        footer.append(footerNote, status, actions);

        selectFormat(selectedFormat);

        dialog.append(toolbar, content, footer);
        overlay.appendChild(dialog);

        const previousOverflow = document.body.style.overflow;
        const close = () => {
            overlay.remove();
            document.body.style.overflow = previousOverflow;
            document.removeEventListener('keydown', closeOnEscape);
        };
        const closeOnEscape = event => {
            if (event.key === 'Escape' && overlay.isConnected) close();
        };

        closeButton.addEventListener('click', close);
        overlay.addEventListener('click', event => { if (event.target === overlay) close(); });
        document.addEventListener('keydown', closeOnEscape);
        document.body.style.overflow = 'hidden';
        document.body.appendChild(overlay);
        closeButton.focus();
    }

    function fileBase(config) {
        return (config.filename || config.title || 'occaserve-report')
            .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'occaserve-report';
    }

    function saveBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    async function loadBrandImage() {
        let response = await fetch('/static/images/occaserve_logo_clean.png', { credentials: 'same-origin' });
        if (!response.ok) {
            response = await fetch('/static/images/brand_icon.png', { credentials: 'same-origin' });
        }
        if (!response.ok) throw new Error('Brand logo image unavailable');
        const image = new Image();
        image.src = URL.createObjectURL(await response.blob());
        await new Promise((resolve, reject) => {
            image.onload = resolve;
            image.onerror = reject;
        });
        const canvas = document.createElement('canvas');
        canvas.width = image.naturalWidth;
        canvas.height = image.naturalHeight;
        canvas.getContext('2d').drawImage(image, 0, 0);
        URL.revokeObjectURL(image.src);
        return canvas.toDataURL('image/png');
    }

    function imageBytes(dataUrl) {
        const binary = atob(dataUrl.split(',')[1]);
        return Uint8Array.from(binary, character => character.charCodeAt(0));
    }

    async function download(config, sections, format, button, status, formatLabels) {
        const label = formatLabels.get(format).label;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i><span>Preparing…</span>';
        status.innerHTML = `<i class="fas fa-circle-notch fa-spin"></i> Preparing ${label} report…`;
        status.classList.remove('is-success', 'is-error');
        try {
            if (format === 'xlsx') await downloadXlsx(config, sections);
            else if (format === 'word') await downloadWordDocument(config, sections);
            else await downloadPdf(config, sections);
            status.innerHTML = `<i class="fas fa-check-circle"></i> ${label} downloaded successfully.`;
            status.classList.add('is-success');
            if (typeof window.showToast === 'function') window.showToast(`${label} report downloaded successfully.`, 'success');
        } catch (error) {
            console.error('OccaServe report export failed:', error);
            status.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${error.message || `Could not generate the ${label} report.`}`;
            status.classList.add('is-error');
            if (window.showError) window.showError(status.textContent);
            else if (typeof window.showToast === 'function') window.showToast(status.textContent, 'error');
            else window.alert(status.textContent);
        } finally {
            button.disabled = false;
            const option = formatLabels.get(format);
            button.innerHTML = `<i class="fas fa-download" aria-hidden="true"></i><span>Download ${option.label}</span>`;
        }
    }

    // =========================================================================
    // WORD (.docx) EXPORT GENERATOR - MATCHING USER BLUEPRINT
    // =========================================================================
    async function downloadWordDocument(config, sections) {
        await loadLibrary(libraries.docx);
        const word = window.docx;
        if (!word || !word.Document || !word.Packer) throw new Error('Word document library is unavailable.');
        const brandImage = await loadBrandImage();
        const totalRecords = sections.reduce((sum, s) => sum + s.rows.length, 0);
        const dateStr = config.generatedAt || new Date().toLocaleString('en-US', {
            month: 'short', day: '2-digit', year: 'numeric',
            hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true
        });

        const children = [
            // Centered Logo
            new word.Paragraph({
                alignment: word.AlignmentType.CENTER,
                children: [
                    new word.ImageRun({ data: imageBytes(brandImage), transformation: { width: 140, height: 28 } })
                ],
                spacing: { after: 60 }
            }),
            // OFFICIAL REPORT
            new word.Paragraph({
                alignment: word.AlignmentType.CENTER,
                children: [
                    new word.TextRun({ text: '——————  OFFICIAL REPORT  ——————', bold: true, color: '061D38', size: 18 })
                ],
                spacing: { after: 60 }
            }),
            // Title
            new word.Paragraph({
                alignment: word.AlignmentType.CENTER,
                children: [
                    new word.TextRun({ text: config.title || 'Bookings Database Report', bold: true, color: '061D38', size: 36 })
                ],
                spacing: { after: 60 }
            }),
            // Metadata Line
            new word.Paragraph({
                alignment: word.AlignmentType.CENTER,
                children: [
                    new word.TextRun({ text: `Generated on ${dateStr}   |   ${totalRecords} bookings matching current search and filters`, color: '334155', size: 18 })
                ],
                border: { bottom: { color: 'F05A28', space: 10, style: word.BorderStyle.SINGLE, size: 16 } },
                spacing: { after: 180 }
            })
        ];

        const pageWidth = 16838;
        const margins = { top: 720, right: 720, bottom: 720, left: 720 };
        const tableWidth = pageWidth - margins.left - margins.right;

        sections.forEach(section => {
            if (section.title) {
                children.push(new word.Paragraph({ text: section.title, heading: word.HeadingLevel.HEADING_2, spacing: { before: 200, after: 100 } }));
            }
            const widths = wordColumnWidths(section, tableWidth);
            const rows = [new word.TableRow({
                children: section.columns.map((column, index) => makeWordCell(
                    word,
                    column.label,
                    true,
                    widths[index],
                    column.type === 'currency' || /amount|price|total|revenue/i.test(String(column.label || ''))
                )),
                tableHeader: true
            })];

            section.rows.forEach(row => rows.push(new word.TableRow({
                cantSplit: true,
                children: section.columns.map((column, index) => {
                    const val = valueFor(row, column, index);
                    const isCurr = column.type === 'currency' || /amount|price|total|revenue/i.test(String(column.label || ''));
                    return makeWordCell(
                        word,
                        isCurr ? formatCurrency(val) : safeText(val),
                        false,
                        widths[index],
                        isCurr
                    );
                })
            })));

            if (!section.columns.length) {
                children.push(new word.Paragraph({ text: 'No matching records.' }));
            } else {
                children.push(new word.Table({
                    rows,
                    width: { size: tableWidth, type: word.WidthType.DXA },
                    columnWidths: widths,
                    layout: word.TableLayoutType.FIXED,
                    borders: {
                        top: { style: word.BorderStyle.NONE, size: 0, color: 'FFFFFF' },
                        bottom: { style: word.BorderStyle.SINGLE, size: 1, color: 'E2E8F0' },
                        left: { style: word.BorderStyle.NONE, size: 0, color: 'FFFFFF' },
                        right: { style: word.BorderStyle.NONE, size: 0, color: 'FFFFFF' },
                        insideHorizontal: { style: word.BorderStyle.SINGLE, size: 1, color: 'E2E8F0' },
                        insideVertical: { style: word.BorderStyle.NONE, size: 0, color: 'FFFFFF' }
                    }
                }));
            }
        });

        // Bottom Orange Line before footer
        children.push(new word.Paragraph({
            border: { top: { color: 'F05A28', space: 8, style: word.BorderStyle.SINGLE, size: 14 } },
            spacing: { before: 180, after: 40 }
        }));

        const pageNumber = word.PageNumber;
        const footer = word.Footer && pageNumber ? {
            default: new word.Footer({
                children: [new word.Paragraph({
                    alignment: word.AlignmentType.BOTH,
                    children: [
                        new word.TextRun({ text: 'OccaServe  |  Confidential Platform Report', bold: true, color: '061D38', size: 16 }),
                        new word.TextRun({ text: '\t\tPage ' }),
                        new word.TextRun({ children: [pageNumber.CURRENT] }),
                        new word.TextRun({ text: ' of ' }),
                        new word.TextRun({ children: [pageNumber.TOTAL_PAGES] })
                    ]
                })]
            })
        } : undefined;

        const document = new word.Document({
            creator: 'OccaServe',
            title: config.title || 'Bookings Database Report',
            sections: [{
                properties: {
                    page: {
                        size: { width: pageWidth, height: 11906, orientation: word.PageOrientation.LANDSCAPE },
                        margin: margins
                    }
                },
                ...(footer ? { footers: footer } : {}),
                children
            }]
        });
        saveBlob(await word.Packer.toBlob(document), `${fileBase(config)}.docx`);
    }

    function makeWordCell(word, value, header = false, width, alignRight = false) {
        return new word.TableCell({
            children: [new word.Paragraph({
                alignment: alignRight ? word.AlignmentType.RIGHT : word.AlignmentType.LEFT,
                spacing: { before: 0, after: 0 },
                children: [new word.TextRun({
                    text: safeText(value),
                    bold: header,
                    color: header ? 'FFFFFF' : (alignRight ? '000000' : '0F172A'),
                    size: header ? 17 : 16
                })]
            })],
            shading: header ? { fill: '061D38', type: word.ShadingType.CLEAR } : undefined,
            margins: { top: 70, bottom: 70, left: 90, right: 90 },
            verticalAlign: word.VerticalAlign.CENTER,
            ...(width ? { width: { size: width, type: word.WidthType.DXA } } : {})
        });
    }

    function wordColumnWidths(section, totalWidth) {
        const weights = wordColumnWeights(section);
        const totalWeight = weights.reduce((sum, weight) => sum + weight, 0) || 1;
        const widths = weights.map(weight => Math.floor(totalWidth * weight / totalWeight));
        if (widths.length) widths[widths.length - 1] += totalWidth - widths.reduce((sum, width) => sum + width, 0);
        return widths;
    }

    function wordColumnWeights(section) {
        return section.columns.map((column, index) => {
            const longestValue = section.rows.slice(0, 100).reduce((longest, row) => (
                Math.max(longest, safeText(valueFor(row, column, index)).split(/\r?\n/).reduce(
                    (maxLine, line) => Math.max(maxLine, line.length), 0
                ))
            ), 0);
            return Math.min(36, Math.max(8, String(column.label).length * 0.8, Math.min(30, longestValue * 0.35)));
        });
    }

    function downloadText(config, sections) {
        const lines = [config.title || 'Bookings Database Report', `Generated ${config.generatedAt || new Date().toLocaleString()}`, ...(config.metadata || []), ''];
        sections.forEach(section => {
            if (section.title) lines.push(section.title);
            lines.push(section.columns.map(column => column.label).join(' | '));
            section.rows.forEach(row => lines.push(section.columns.map((column, index) => safeText(valueFor(row, column, index))).join(' | ')));
            lines.push('');
        });
        saveBlob(new Blob(['\ufeff', lines.join('\r\n')], { type: 'text/plain;charset=utf-8' }), `${fileBase(config)}.txt`);
    }

    // =========================================================================
    // EXCEL (XLSX) EXPORT GENERATOR - EXACT BLUEPRINT MATCHING USER IMAGE
    // =========================================================================
    async function downloadXlsx(config, sections) {
        await loadScript(libraries.xlsx);
        if (!window.ExcelJS) throw new Error('Excel workbook library is unavailable.');
        const workbook = new ExcelJS.Workbook();
        workbook.creator = 'OccaServe Catering Platform';
        workbook.created = new Date();
        const brandImage = await loadBrandImage();
        const brandImageId = workbook.addImage({ base64: brandImage, extension: 'png' });
        const totalRecords = sections.reduce((sum, s) => sum + s.rows.length, 0);
        const dateStr = config.generatedAt || new Date().toLocaleString('en-US', {
            month: 'short', day: '2-digit', year: 'numeric',
            hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true
        });

        sections.forEach((section, sectionIndex) => {
            const worksheetName = (section.title || 'Report').replace(/[\\/?*:[\]]/g, '').slice(0, 31) || `Report ${sectionIndex + 1}`;
            const worksheet = workbook.addWorksheet(worksheetName);
            const columnCount = Math.max(1, section.columns.length);

            // Columns setup
            worksheet.columns = section.columns.map((column, index) => {
                const labelLow = String(column.label || '').toLowerCase();
                const isCurr = column.type === 'currency' || /amount|price|total|revenue/i.test(labelLow);
                const isStatus = /status|payment/i.test(labelLow);
                return {
                    key: `field${index}`,
                    width: Math.min(46, Math.max(16, String(column.label).length + 6, ...section.rows.slice(0, 150).map(row => safeText(valueFor(row, column, index)).length + 3))),
                    style: {
                        font: { name: 'Arial', size: 9 },
                        ...(isCurr ? { numFmt: '"₱"#,##0.00' } : {}),
                        alignment: {
                            horizontal: isCurr ? 'right' : (isStatus ? 'center' : 'left'),
                            vertical: 'middle',
                            wrapText: true
                        }
                    }
                };
            });

            const addMergedLine = (text, style = {}) => {
                const row = worksheet.addRow([text]);
                if (columnCount > 1) worksheet.mergeCells(row.number, 1, row.number, columnCount);
                row.alignment = { vertical: 'middle', horizontal: style.align || 'center', wrapText: true };
                row.height = style.height || 22;
                row.font = {
                    name: 'Arial',
                    ...(style.font || {}),
                    ...(style.color ? { color: { argb: style.color } } : {})
                };
                return row;
            };

            // Row 1: Logo Spacer Row
            const logoRow = addMergedLine('', { height: 42 });
            const midCol = Math.max(0, Math.floor(columnCount / 2) - 1);
            worksheet.addImage(brandImageId, {
                tl: { col: midCol + 0.2, row: logoRow.number - 1 + 0.1 },
                ext: { width: 140, height: 28 }
            });

            // Row 2: —— OFFICIAL REPORT ——
            addMergedLine('——  OFFICIAL REPORT  ——', {
                font: { bold: true, size: 9 },
                color: 'FF061D38',
                height: 18
            });

            // Row 3: Report Title (Bookings Database Report)
            addMergedLine(config.title || 'Bookings Database Report', {
                font: { bold: true, size: 16 },
                color: 'FF061D38',
                height: 28
            });

            // Row 4: Generated on Date | Matching records
            addMergedLine(`Generated on ${dateStr}   |   ${totalRecords} bookings matching current search and filters`, {
                font: { size: 9 },
                color: 'FF334155',
                height: 20
            });

            // Row 5: Orange Bar Divider above table
            const orangeBarRow = worksheet.addRow([]);
            orangeBarRow.height = 6;
            for (let c = 1; c <= columnCount; c++) {
                orangeBarRow.getCell(c).border = { bottom: { style: 'medium', color: { argb: 'FFF05A28' } } };
            }

            // Row 6: Table Header in Deep Navy #061D38 with White Text and White Vertical Borders
            const headerRow = worksheet.addRow(section.columns.map(column => column.label));
            const headerRowNumber = headerRow.number;
            headerRow.height = 26;
            headerRow.font = { name: 'Arial', size: 10, bold: true, color: { argb: 'FFFFFFFF' } };
            headerRow.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF061D38' } };
            headerRow.alignment = { vertical: 'middle', horizontal: 'left', wrapText: true };

            // Apply white borders to header cells
            section.columns.forEach((col, cIndex) => {
                const cell = headerRow.getCell(cIndex + 1);
                const labelLow = String(col.label || '').toLowerCase();
                const isCurr = col.type === 'currency' || /amount|price|total|revenue/i.test(labelLow);
                const isStatus = /status|payment/i.test(labelLow);
                if (isCurr) cell.alignment = { vertical: 'middle', horizontal: 'right', wrapText: true };
                else if (isStatus) cell.alignment = { vertical: 'middle', horizontal: 'center', wrapText: true };

                cell.border = {
                    right: { style: 'thin', color: { argb: 'FFFFFFFF' } },
                    left: cIndex === 0 ? undefined : { style: 'thin', color: { argb: 'FFFFFFFF' } }
                };
            });

            // Data Rows
            let startDataRow = headerRowNumber + 1;
            if (section.columns.length && section.rows.length) {
                section.rows.forEach(row => {
                    const rowValues = section.columns.map((column, index) => {
                        const val = valueFor(row, column, index);
                        const labelLow = String(column.label || '').toLowerCase();
                        const isCurr = column.type === 'currency' || /amount|price|total|revenue/i.test(labelLow);
                        if (isCurr) {
                            const num = parseNumericValue(val);
                            return num !== null ? num : safeText(val);
                        }
                        return safeText(val);
                    });
                    worksheet.addRow(rowValues);
                });
            } else {
                worksheet.addRow(['No matching records found.']);
            }
            let endDataRow = worksheet.rowCount;

            // Zebra Striping & Status Cell Coloring matching the image
            worksheet.eachRow((row, rowNumber) => {
                if (rowNumber <= headerRowNumber || rowNumber > endDataRow) return;
                const isEven = (rowNumber - headerRowNumber) % 2 === 0;
                row.eachCell(cell => {
                    cell.border = { bottom: { style: 'thin', color: { argb: 'FFE2E8F0' } } };
                    if (isEven) {
                        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF4F8FA' } };
                    } else {
                        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFFFFFF' } };
                    }
                    const column = section.columns[cell.col - 1];
                    const labelLow = column ? String(column.label || '').toLowerCase() : '';
                    const isStatus = /status|payment/i.test(labelLow);
                    const isBookingId = /booking[ -]?id|reference|ref/i.test(labelLow);
                    const isCurr = column && (column.type === 'currency' || /amount|price|total|revenue/i.test(labelLow));

                    if (isBookingId) {
                        cell.font = { name: 'Arial', size: 9, bold: true, color: { argb: 'FF061D38' } };
                    }
                    if (isCurr) {
                        cell.font = { name: 'Arial', size: 9, bold: true, color: { argb: 'FF000000' } };
                        cell.alignment = { vertical: 'middle', horizontal: 'right' };
                    }
                    if (isStatus) {
                        cell.alignment = { vertical: 'middle', horizontal: 'center' };
                        const valLow = String(cell.value || '').trim().toLowerCase();
                        if (/^(fully[ -]?paid|confirmed|completed|paid|active)$/i.test(valLow)) {
                            cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFDCFCE7' } };
                            cell.font = { name: 'Arial', size: 9, bold: true, color: { argb: 'FF15803D' } };
                        } else if (/^(partially[ -]?paid|pending|review|draft)$/i.test(valLow)) {
                            cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFFEDD5' } };
                            cell.font = { name: 'Arial', size: 9, bold: true, color: { argb: 'FFEA580C' } };
                        } else if (/^(cancelled|rejected|failed|unpaid)$/i.test(valLow)) {
                            cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFEE2E2' } };
                            cell.font = { name: 'Arial', size: 9, bold: true, color: { argb: 'FFB91C1C' } };
                        }
                    }
                });
                row.height = 22;
            });

            // Orange bottom bar below data
            const bottomOrangeRow = worksheet.addRow([]);
            bottomOrangeRow.height = 6;
            for (let c = 1; c <= columnCount; c++) {
                bottomOrangeRow.getCell(c).border = { bottom: { style: 'medium', color: { argb: 'FFF05A28' } } };
            }

            // Footer Row: OccaServe | Confidential Platform Report (Left) and Page 1 of 1 (Right)
            const footerRow = worksheet.addRow([]);
            footerRow.height = 22;
            footerRow.getCell(1).value = 'OccaServe  |  Confidential Platform Report';
            footerRow.getCell(1).font = { name: 'Arial', size: 9, bold: true, color: { argb: 'FF061D38' } };
            footerRow.getCell(1).alignment = { vertical: 'middle', horizontal: 'left' };

            if (columnCount > 1) {
                footerRow.getCell(columnCount).value = 'Page 1 of 1';
                footerRow.getCell(columnCount).font = { name: 'Arial', size: 9, color: { argb: 'FF334155' } };
                footerRow.getCell(columnCount).alignment = { vertical: 'middle', horizontal: 'right' };
            }

            // Freeze Panes and Auto Filter
            worksheet.views = [{ state: 'frozen', ySplit: headerRowNumber }];
            if (section.columns.length) {
                worksheet.autoFilter = {
                    from: { row: headerRowNumber, column: 1 },
                    to: { row: endDataRow, column: section.columns.length }
                };
            }

            worksheet.pageSetup = {
                paperSize: 9,
                orientation: 'landscape',
                fitToPage: true,
                fitToWidth: 1,
                fitToHeight: 0,
                margins: { left: 0.5, right: 0.5, top: 0.5, bottom: 0.5, header: 0.2, footer: 0.2 }
            };
        });

        const buffer = await workbook.xlsx.writeBuffer();
        saveBlob(new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }), `${fileBase(config)}.xlsx`);
    }

    // =========================================================================
    // PDF EXPORT GENERATOR - EXACT BLUEPRINT MATCHING USER IMAGE
    // =========================================================================
    async function downloadPdf(config, sections) {
        await loadScript(libraries.pdf);
        await loadScript(libraries.table);
        const Pdf = window.jspdf && window.jspdf.jsPDF;
        if (!Pdf) throw new Error('PDF library is unavailable.');
        const doc = new Pdf({ orientation: 'landscape', unit: 'pt', format: 'a4' });
        const brandImage = await loadBrandImage();
        const margin = 36;
        const pageWidth = doc.internal.pageSize.getWidth();
        const pageHeight = doc.internal.pageSize.getHeight();
        const totalRecords = sections.reduce((sum, s) => sum + s.rows.length, 0);
        const dateStr = config.generatedAt || new Date().toLocaleString('en-US', {
            month: 'short', day: '2-digit', year: 'numeric',
            hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true
        });

        sections.forEach((section, index) => {
            let tableStartY = 96;

            if (index > 0 && doc.lastAutoTable) {
                tableStartY = doc.lastAutoTable.finalY + 24;
            }

            const needsNewPage = index > 0 && (tableStartY > pageHeight - 120);
            if (needsNewPage) {
                doc.addPage();
                tableStartY = 96;
            }

            const drawPageHeader = () => {
                // 1. Top Corner Orange Wave Swooshes (matching image)
                doc.setFillColor(254, 215, 170); // peach outer
                doc.ellipse(0, 0, 115, 42, 'F');
                doc.setFillColor(240, 90, 40); // orange inner
                doc.ellipse(0, 0, 75, 26, 'F');

                doc.setFillColor(254, 215, 170); // peach outer
                doc.ellipse(pageWidth, 0, 115, 42, 'F');
                doc.setFillColor(240, 90, 40); // orange inner
                doc.ellipse(pageWidth, 0, 75, 26, 'F');

                // 2. Centered Logo Image
                const logoW = 120;
                const logoH = 24.25;
                const logoX = (pageWidth - logoW) / 2;
                doc.addImage(brandImage, 'PNG', logoX, 14, logoW, logoH);

                // 3. —— OFFICIAL REPORT ——
                const midX = pageWidth / 2;
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(8.5);
                doc.setTextColor(6, 29, 56);
                doc.text('OFFICIAL REPORT', midX, 47, { align: 'center' });

                doc.setDrawColor(6, 29, 56);
                doc.setLineWidth(1.2);
                doc.line(midX - 90, 44.5, midX - 48, 44.5);
                doc.line(midX + 48, 44.5, midX + 90, 44.5);

                // 4. Report Title
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(18);
                doc.setTextColor(6, 29, 56);
                doc.text(config.title || 'Bookings Database Report', midX, 66, { align: 'center' });

                // 5. Metadata Line
                doc.setFont('helvetica', 'normal');
                doc.setFontSize(8);
                doc.setTextColor(51, 65, 85);
                const metaText = `Generated on ${dateStr}   |   ${totalRecords} bookings matching current search and filters`;
                doc.text(metaText, midX, 79, { align: 'center' });

                // 6. Orange Divider Bar above table
                doc.setDrawColor(240, 90, 40);
                doc.setLineWidth(2.2);
                doc.line(margin, 87, pageWidth - margin, 87);
            };

            if (!index || needsNewPage) drawPageHeader();

            const columnCount = Math.max(1, section.columns.length);
            const sectionStartPage = doc.internal.getCurrentPageInfo().pageNumber;
            const pdfColumnWeights = wordColumnWeights(section);
            const totalPdfColumnWeight = pdfColumnWeights.reduce((sum, weight) => sum + weight, 0) || 1;

            doc.autoTable({
                startY: 94,
                head: [section.columns.map(column => column.label)],
                body: section.rows.map(row => section.columns.map((column, columnIndex) => {
                    const labelLow = String(column.label || '').toLowerCase();
                    const isCurr = column.type === 'currency' || /amount|price|total|revenue/i.test(labelLow);
                    const val = valueFor(row, column, columnIndex);
                    return isCurr ? formatCurrency(val) : safeText(val);
                })),
                margin: { top: 94, left: margin, right: margin, bottom: 38 },
                theme: 'grid',
                styles: {
                    font: 'helvetica',
                    fontSize: Math.max(6, Math.min(8.5, 8.5 - Math.max(0, columnCount - 6) * 0.4)),
                    cellPadding: 6,
                    overflow: 'linebreak',
                    valign: 'middle',
                    textColor: [15, 23, 42],
                    lineColor: [226, 232, 240],
                    lineWidth: 0.5
                },
                headStyles: {
                    fillColor: [6, 29, 56], // Deep Navy matching image
                    textColor: [255, 255, 255],
                    fontStyle: 'bold',
                    valign: 'middle',
                    lineColor: [255, 255, 255],
                    lineWidth: 0.6
                },
                alternateRowStyles: {
                    fillColor: [244, 248, 250] // Pale Cool Mint/Slate matching image
                },
                columnStyles: Object.fromEntries(section.columns.map((column, columnIndex) => {
                    const labelLow = String(column.label || '').toLowerCase();
                    const isCurr = column.type === 'currency' || /amount|price|total|revenue/i.test(labelLow);
                    const isStatus = /status|payment/i.test(labelLow);
                    return [
                        columnIndex,
                        {
                            cellWidth: (pageWidth - margin * 2) * pdfColumnWeights[columnIndex] / totalPdfColumnWeight,
                            halign: isCurr ? 'right' : (isStatus ? 'center' : 'left'),
                            fontStyle: isCurr ? 'bold' : 'normal',
                            textColor: isCurr ? [0, 0, 0] : [15, 23, 42]
                        }
                    ];
                })),
                didDrawCell: (data) => {
                    // Status Pill Badges drawn in exact soft pastel colors
                    if (data.section === 'body') {
                        const rawText = String(data.cell.raw || '').trim().toLowerCase();
                        let badgeBg = null;
                        let badgeTextColor = null;

                        if (/^(fully[ -]?paid|confirmed|completed|paid|active)$/i.test(rawText)) {
                            badgeBg = [220, 252, 231]; // soft green #DCFCE7
                            badgeTextColor = [21, 128, 61]; // dark green #15803D
                        } else if (/^(partially[ -]?paid|pending|review|draft)$/i.test(rawText)) {
                            badgeBg = [255, 237, 213]; // soft orange #FFEDD5
                            badgeTextColor = [234, 88, 12]; // dark orange #EA580C
                        } else if (/^(cancelled|rejected|failed|unpaid)$/i.test(rawText)) {
                            badgeBg = [254, 226, 226]; // soft red #FEE2E2
                            badgeTextColor = [185, 28, 28]; // dark red #B91C1C
                        }

                        if (badgeBg && badgeTextColor) {
                            const paddingH = 6;
                            const pillH = 15;
                            const pillW = Math.min(data.cell.width - 8, Math.max(48, String(data.cell.raw).length * 5.6 + 12));
                            const pillX = data.cell.x + (data.cell.width - pillW) / 2;
                            const pillY = data.cell.y + (data.cell.height - pillH) / 2;

                            doc.setFillColor(badgeBg[0], badgeBg[1], badgeBg[2]);
                            doc.roundedRect(pillX, pillY, pillW, pillH, 3, 3, 'F');

                            doc.setFont('helvetica', 'bold');
                            doc.setFontSize(data.cell.styles.fontSize);
                            doc.setTextColor(badgeTextColor[0], badgeTextColor[1], badgeTextColor[2]);
                            doc.text(
                                String(data.cell.raw),
                                data.cell.x + data.cell.width / 2,
                                pillY + pillH / 2 + 3,
                                { align: 'center' }
                            );
                        }
                    }
                },
                didDrawPage: () => {
                    if (doc.internal.getCurrentPageInfo().pageNumber > sectionStartPage) {
                        drawPageHeader();
                    }
                }
            });

            // Orange divider bar below table on last page
            if (doc.lastAutoTable) {
                const bottomY = Math.min(pageHeight - 28, doc.lastAutoTable.finalY + 12);
                doc.setDrawColor(240, 90, 40);
                doc.setLineWidth(2.2);
                doc.line(margin, bottomY, pageWidth - margin, bottomY);
            }
        });

        const pageCount = doc.internal.getNumberOfPages();
        for (let pageNumber = 1; pageNumber <= pageCount; pageNumber += 1) {
            doc.setPage(pageNumber);
            const footY = pageHeight - 15;

            // Left footer: OccaServe  |  Confidential Platform Report
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(10);
            doc.setTextColor(6, 29, 56);
            doc.text('OccaServe', margin, footY);

            doc.setFont('helvetica', 'normal');
            doc.setFontSize(8.5);
            doc.setTextColor(51, 65, 85);
            doc.text('  |   Confidential Platform Report', margin + 50, footY);

            // Right footer: Page X of Y
            doc.setFont('helvetica', 'normal');
            doc.setFontSize(8.5);
            doc.setTextColor(51, 65, 85);
            doc.text(`Page ${pageNumber} of ${pageCount}`, pageWidth - margin, footY, { align: 'right' });
        }
        doc.save(`${fileBase(config)}.pdf`);
    }

    function printReport(config, sections) {
        const win = window.open('', '_blank');
        if (!win) throw new Error('Please allow pop-ups to print this report.');
        const totalRecords = sections.reduce((sum, s) => sum + s.rows.length, 0);
        const dateStr = config.generatedAt || new Date().toLocaleString('en-US', {
            month: 'short', day: '2-digit', year: 'numeric',
            hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true
        });

        const sectionHtml = sections.map(section => `
            <section>
                ${section.title ? `<h2>${escapeHtml(section.title)}</h2>` : ''}
                <table>
                    <thead>
                        <tr>${section.columns.map(column => `<th>${escapeHtml(column.label)}</th>`).join('')}</tr>
                    </thead>
                    <tbody>
                        ${section.rows.map(row => `<tr>${section.columns.map((column, index) => {
                            const labelLow = String(column.label || '').toLowerCase();
                            const isCurrency = column.type === 'currency' || /amount|price|total|revenue/i.test(labelLow);
                            const isStatus = /status|payment/i.test(labelLow);
                            const isBookingId = /booking[ -]?id|reference|ref/i.test(labelLow);
                            const val = valueFor(row, column, index);

                            if (isCurrency) {
                                return `<td style="text-align:right;font-weight:700;">${escapeHtml(formatCurrency(val))}</td>`;
                            } else if (isStatus) {
                                const badge = getStatusBadgeHtml(val);
                                return `<td style="text-align:center;">${badge || escapeHtml(safeText(val))}</td>`;
                            } else if (isBookingId) {
                                return `<td style="font-weight:700;">${escapeHtml(safeText(val))}</td>`;
                            }
                            return `<td>${escapeHtml(safeText(val))}</td>`;
                        }).join('')}</tr>`).join('')}
                    </tbody>
                </table>
            </section>
        `).join('');

        win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${escapeHtml(config.title || 'Bookings Database Report')}</title><style>@page{size:landscape;margin:10mm}body{font:10px/1.45 'Poppins',Arial,sans-serif;color:#061D38;padding:12px}.logo{text-align:center;margin-bottom:6px}.logo img{height:42px}.badge{text-align:center;font-size:11px;font-weight:800;letter-spacing:.2em;color:#061D38;margin:4px 0 8px}h1{font-size:22px;text-align:center;margin:0 0 6px 0;color:#061D38}.meta{text-align:center;font-size:10px;color:#334155;margin-bottom:14px}.orange-bar{width:100%;height:2.5px;background:#F05A28;margin-bottom:12px}table{width:100%;border-collapse:collapse;font-size:9px}th{background:#061D38;color:#fff;padding:8px 10px;text-align:left;border:none;border-right:1px solid rgba(255,255,255,.3)}td{padding:8px 10px;border-bottom:1px solid #E2E8F0}tr:nth-child(even){background:#F4F8FA}.status-fully-paid{background:#DCFCE7;color:#15803D;padding:3px 8px;border-radius:4px;font-weight:700}.status-partially-paid{background:#FFEDD5;color:#EA580C;padding:3px 8px;border-radius:4px;font-weight:700}.status-cancelled{background:#FEE2E2;color:#B91C1C;padding:3px 8px;border-radius:4px;font-weight:700}footer{margin-top:14px;border-top:2px solid #F05A28;padding-top:8px;display:flex;justify-content:space-between;font-size:10px;color:#334155}</style></head><body><div class="logo"><img src="${window.location.origin}/static/images/occaserve_logo_clean.png" alt="OccaServe" onerror="this.src='${window.location.origin}/static/images/brand_icon.png'"></div><div class="badge">—— OFFICIAL REPORT ——</div><h1>${escapeHtml(config.title || 'Bookings Database Report')}</h1><div class="meta">Generated on ${dateStr}   |   ${totalRecords} bookings matching current search and filters</div><div class="orange-bar"></div>${sectionHtml}<footer><div><strong>OccaServe</strong> | Confidential Platform Report</div><div>Page 1 of 1</div></footer><script>window.onload=()=>window.print()<\/script></body></html>`);
        win.document.close();
    }

    window.OccaExportPreview = { open: createPreview };
}());
