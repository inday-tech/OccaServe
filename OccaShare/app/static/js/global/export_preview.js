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

    // Status Pill Detection Helper
    function getStatusBadgeHtml(value) {
        if (value == null) return null;
        const str = String(value).trim();
        const low = str.toLowerCase();

        // Success / Positive
        if (/^(confirmed|completed|paid|active|approved|verified|delivered|healthy|success)$/i.test(low)) {
            return `<span class="occa-badge occa-badge-success"><i class="fas fa-check-circle" aria-hidden="true"></i> ${escapeHtml(str)}</span>`;
        }
        // Warning / Pending / In-progress
        if (/^(pending|in[ -]?progress|partial|partially[ -]?paid|review|under[ -]?review|draft|resubmit|waiting)$/i.test(low)) {
            return `<span class="occa-badge occa-badge-warning"><i class="fas fa-clock" aria-hidden="true"></i> ${escapeHtml(str)}</span>`;
        }
        // Danger / Cancelled / Rejected
        if (/^(cancelled|rejected|failed|unpaid|inactive|suspended|disputed|declined|terminated|fraud)$/i.test(low)) {
            return `<span class="occa-badge occa-badge-danger"><i class="fas fa-times-circle" aria-hidden="true"></i> ${escapeHtml(str)}</span>`;
        }
        // Info / Neutral
        if (/^(info|scheduled|assigned|inquiry|processing|new)$/i.test(low)) {
            return `<span class="occa-badge occa-badge-info"><i class="fas fa-info-circle" aria-hidden="true"></i> ${escapeHtml(str)}</span>`;
        }
        return null;
    }

    // Calculate Summary Metrics for a section
    function calculateSectionMetrics(section) {
        const totalRows = section.rows.length;
        let currencySum = 0;
        let hasCurrency = false;
        let currencyColIndex = -1;

        section.columns.forEach((col, idx) => {
            const isCurr = col.type === 'currency' ||
                /amount|price|total|revenue|collected|fee|dues|cost/i.test(String(col.label || ''));
            if (isCurr && currencyColIndex === -1) {
                currencyColIndex = idx;
                hasCurrency = true;
            }
        });

        if (hasCurrency && currencyColIndex !== -1) {
            section.rows.forEach(row => {
                const val = valueFor(row, section.columns[currencyColIndex], currencyColIndex);
                const num = parseNumericValue(val);
                if (num !== null) currencySum += num;
            });
        }

        return {
            totalRows,
            hasCurrency,
            currencyColIndex,
            currencySum,
            avgAmount: totalRows > 0 ? (currencySum / totalRows) : 0
        };
    }

    function appendReportHeader(sheet, config) {
        const brand = document.createElement('div');
        brand.className = 'occa-export-document-brand';
        const logo = document.createElement('img');
        logo.src = '/static/images/brand_icon.png';
        logo.alt = 'OccaServe Brand';
        brand.appendChild(logo);
        const brandName = document.createElement('strong');
        brandName.textContent = 'OCCASERVE';
        brand.appendChild(brandName);
        sheet.appendChild(brand);

        const heading = document.createElement('h1');
        heading.textContent = config.title || 'OccaServe Official Report';
        sheet.appendChild(heading);

        if (config.catererName) {
            const caterer = document.createElement('div');
            caterer.className = 'occa-export-caterer';
            caterer.innerHTML = `<i class="fas fa-utensils" aria-hidden="true"></i> ${escapeHtml(config.catererName)}`;
            sheet.appendChild(caterer);
        }

        const metadata = document.createElement('div');
        metadata.className = 'occa-export-meta';
        metadata.textContent = [`Generated ${config.generatedAt || new Date().toLocaleString()}`]
            .concat(config.metadata || []).filter(Boolean).join(' · ');
        sheet.appendChild(metadata);
    }

    function renderKpiRibbon(metrics) {
        const ribbon = document.createElement('div');
        ribbon.className = 'occa-export-kpi-ribbon';

        const cardTotal = document.createElement('div');
        cardTotal.className = 'occa-kpi-card';
        cardTotal.innerHTML = `
            <span class="occa-kpi-label"><i class="fas fa-list-check" aria-hidden="true"></i> Total Entries</span>
            <strong class="occa-kpi-val">${metrics.totalRows.toLocaleString()}</strong>
            <small class="occa-kpi-sub">Matching records in report</small>
        `;
        ribbon.appendChild(cardTotal);

        if (metrics.hasCurrency) {
            const cardSum = document.createElement('div');
            cardSum.className = 'occa-kpi-card occa-kpi-card-highlight';
            cardSum.innerHTML = `
                <span class="occa-kpi-label"><i class="fas fa-peso-sign" aria-hidden="true"></i> Total Gross Sum</span>
                <strong class="occa-kpi-val">${formatCurrency(metrics.currencySum)}</strong>
                <small class="occa-kpi-sub">Combined value of entries</small>
            `;
            ribbon.appendChild(cardSum);

            const cardAvg = document.createElement('div');
            cardAvg.className = 'occa-kpi-card';
            cardAvg.innerHTML = `
                <span class="occa-kpi-label"><i class="fas fa-chart-pie" aria-hidden="true"></i> Average Amount</span>
                <strong class="occa-kpi-val">${formatCurrency(metrics.avgAmount)}</strong>
                <small class="occa-kpi-sub">Per item baseline</small>
            `;
            ribbon.appendChild(cardAvg);
        }
        return ribbon;
    }

    function renderFormatPreview(config, sections, format) {
        const sheet = document.createElement('article');
        sheet.className = `occa-export-sheet occa-export-sheet-${format}`;
        appendReportHeader(sheet, config);

        sections.forEach((section, sIndex) => {
            const sectionEl = document.createElement('section');
            sectionEl.className = 'occa-export-section';

            if (section.title) {
                const sectionTitle = document.createElement('h2');
                sectionTitle.textContent = section.title;
                sectionEl.appendChild(sectionTitle);
            }

            const metrics = calculateSectionMetrics(section);
            if (sIndex === 0 && metrics.totalRows > 0) {
                sectionEl.appendChild(renderKpiRibbon(metrics));
            }

            if (!section.columns.length || !section.rows.length) {
                const empty = document.createElement('div');
                empty.className = 'occa-export-empty';
                empty.innerHTML = `<i class="fas fa-inbox fa-2x" style="display:block;margin-bottom:8px;color:#94a3b8;"></i> ${section.rows.length ? 'No columns available.' : 'No matching records found for this report.'}`;
                sectionEl.appendChild(empty);
            } else {
                const wrap = document.createElement('div');
                wrap.className = 'occa-export-table-wrap';
                const table = document.createElement('table');
                table.className = 'occa-export-table';

                if (format === 'xlsx') {
                    table.style.minWidth = `${Math.max(760, section.columns.length * 115)}px`;
                } else {
                    table.style.width = '100%';
                }

                if (format === 'word' || format === 'pdf') {
                    table.style.tableLayout = 'fixed';
                    const weights = wordColumnWeights(section);
                    const totalWeight = weights.reduce((sum, weight) => sum + weight, 0) || 1;
                    const colgroup = document.createElement('colgroup');
                    weights.forEach(weight => {
                        const col = document.createElement('col');
                        col.style.width = `${(weight / totalWeight) * 100}%`;
                        colgroup.appendChild(col);
                    });
                    table.appendChild(colgroup);
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
                        const isCurrency = column.type === 'currency' ||
                            /amount|price|total|revenue|fee|dues|cost/i.test(String(column.label || ''));

                        if (isCurrency) {
                            td.textContent = formatCurrency(value);
                            td.classList.add('is-currency');
                        } else {
                            const badgeHtml = getStatusBadgeHtml(value);
                            if (badgeHtml) {
                                td.innerHTML = badgeHtml;
                            } else {
                                td.textContent = safeText(value);
                            }
                        }
                        tr.appendChild(td);
                    });
                    body.appendChild(tr);
                });

                table.append(head, body);

                // Add Table Footer / Total Row if currency exists
                if (metrics.hasCurrency && metrics.totalRows > 0) {
                    const tfoot = document.createElement('tfoot');
                    const footRow = document.createElement('tr');
                    footRow.className = 'occa-export-total-row';
                    section.columns.forEach((column, index) => {
                        const td = document.createElement('td');
                        if (index === 0) {
                            td.innerHTML = `<strong>TOTAL (${metrics.totalRows})</strong>`;
                        } else if (index === metrics.currencyColIndex) {
                            td.className = 'is-currency';
                            td.innerHTML = `<strong>${formatCurrency(metrics.currencySum)}</strong>`;
                        } else {
                            td.textContent = '';
                        }
                        footRow.appendChild(td);
                    });
                    tfoot.appendChild(footRow);
                    table.appendChild(tfoot);
                }

                wrap.appendChild(table);
                sectionEl.appendChild(wrap);
            }
            sheet.appendChild(sectionEl);
        });
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

        // Toolbar
        const toolbar = document.createElement('div');
        toolbar.className = 'occa-export-toolbar';
        toolbar.innerHTML = `
            <div class="occa-export-brand">
                <img src="/static/images/brand_icon.png" alt="OccaServe logo">
                <div>
                    <span>OCCASERVE REPORT</span>
                    <strong>${escapeHtml(config.title || 'Export Preview')}</strong>
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

        // Segmented Format Navigation
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
            <button type="button" class="occa-zoom-reset" id="occaZoomFit" title="Fit to container">Fit</button>
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
        footerNote.innerHTML = '<i class="fas fa-shield-halved" aria-hidden="true"></i> Certified accurate live snapshot from OccaServe system.';
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
        const response = await fetch('/static/images/brand_icon.png', { credentials: 'same-origin' });
        if (!response.ok) throw new Error('Brand image unavailable');
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

    async function downloadWordDocument(config, sections) {
        await loadLibrary(libraries.docx);
        const word = window.docx;
        if (!word || !word.Document || !word.Packer) throw new Error('Word document library is unavailable.');
        const brandImage = await loadBrandImage();
        const children = [
            new word.Paragraph({
                children: [
                    new word.ImageRun({ data: imageBytes(brandImage), transformation: { width: 48, height: 48 } }),
                    new word.TextRun({ text: '  OCCASERVE REPORT', bold: true, color: 'F07835', size: 22 })
                ],
                spacing: { after: 100 },
                alignment: word.AlignmentType.LEFT
            }),
            new word.Paragraph({
                children: [new word.TextRun({ text: config.title || 'OccaServe Official Report', bold: true, color: '0F172A', size: 34 })],
                spacing: { after: 60 }
            }),
            ...(config.catererName ? [new word.Paragraph({
                children: [new word.TextRun({ text: `Caterer: ${config.catererName}`, bold: true, color: '334155', size: 22 })],
                spacing: { after: 60 }
            })] : []),
            new word.Paragraph({
                children: [new word.TextRun({
                    text: `Generated ${config.generatedAt || new Date().toLocaleString()}${(config.metadata || []).length ? ` · ${(config.metadata || []).join(' · ')}` : ''}`,
                    color: '64748B',
                    size: 18
                })],
                border: { bottom: { color: 'F07835', space: 8, style: word.BorderStyle.SINGLE, size: 12 } },
                spacing: { after: 200 }
            })
        ];

        const pageWidth = 16838;
        const margins = { top: 720, right: 720, bottom: 720, left: 720 };
        const tableWidth = pageWidth - margins.left - margins.right;

        sections.forEach(section => {
            if (section.title) children.push(new word.Paragraph({ text: section.title, heading: word.HeadingLevel.HEADING_1, spacing: { before: 240, after: 120 } }));
            const widths = wordColumnWidths(section, tableWidth);
            const rows = [new word.TableRow({
                children: section.columns.map((column, index) => makeWordCell(
                    word,
                    column.label,
                    true,
                    widths[index],
                    column.type === 'currency' || column.type === 'number'
                )),
                tableHeader: true
            })];
            section.rows.forEach(row => rows.push(new word.TableRow({
                cantSplit: true,
                children: section.columns.map((column, index) => makeWordCell(
                    word,
                    column.type === 'currency' ? formatCurrency(valueFor(row, column, index)) : valueFor(row, column, index),
                    false,
                    widths[index],
                    column.type === 'currency' || column.type === 'number'
                ))
            })));
            if (!section.columns.length) children.push(new word.Paragraph({ text: 'No matching records.' }));
            else children.push(new word.Table({
                rows,
                width: { size: tableWidth, type: word.WidthType.DXA },
                columnWidths: widths,
                layout: word.TableLayoutType.FIXED,
                borders: Object.fromEntries(['top', 'bottom', 'left', 'right', 'insideHorizontal', 'insideVertical'].map(edge => [edge, { style: word.BorderStyle.SINGLE, size: 1, color: 'D7DEE8' }]))
            }));
        });

        const pageNumber = word.PageNumber;
        const footer = word.Footer && pageNumber ? {
            default: new word.Footer({
                children: [new word.Paragraph({
                    alignment: word.AlignmentType.RIGHT,
                    children: [
                        new word.TextRun({ children: [pageNumber.CURRENT] }),
                        new word.TextRun({ text: ' of ' }),
                        new word.TextRun({ children: [pageNumber.TOTAL_PAGES] })
                    ]
                })]
            })
        } : undefined;

        const document = new word.Document({
            creator: 'OccaServe',
            title: config.title || 'OccaServe Report',
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
                    color: header ? 'FFFFFF' : '1E293B',
                    size: header ? 17 : 16
                })]
            })],
            shading: header ? { fill: '0F172A', type: word.ShadingType.CLEAR } : undefined,
            margins: { top: 70, bottom: 70, left: 90, right: 90 },
            verticalAlign: word.VerticalAlign.TOP,
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

    function estimateWrappedLines(value, width) {
        return safeText(value).split(/\r?\n/).reduce((total, line) => (
            total + Math.max(1, Math.ceil(line.length / Math.max(1, width - 2)))
        ), 0);
    }

    function downloadText(config, sections) {
        const lines = [config.title || 'OccaServe Report', `Generated ${config.generatedAt || new Date().toLocaleString()}`, ...(config.metadata || []), ''];
        sections.forEach(section => {
            if (section.title) lines.push(section.title);
            lines.push(section.columns.map(column => column.label).join(' | '));
            section.rows.forEach(row => lines.push(section.columns.map((column, index) => safeText(valueFor(row, column, index))).join(' | ')));
            lines.push('');
        });
        saveBlob(new Blob(['\ufeff', lines.join('\r\n')], { type: 'text/plain;charset=utf-8' }), `${fileBase(config)}.txt`);
    }

    // =========================================================================
    // EXCEL (XLSX) EXPORT GENERATOR - EXECUTIVE DESIGN
    // =========================================================================
    async function downloadXlsx(config, sections) {
        await loadScript(libraries.xlsx);
        if (!window.ExcelJS) throw new Error('Excel workbook library is unavailable.');
        const workbook = new ExcelJS.Workbook();
        workbook.creator = 'OccaServe Catering Platform';
        workbook.created = new Date();
        const brandImage = await loadBrandImage();
        const brandImageId = workbook.addImage({ base64: brandImage, extension: 'png' });

        sections.forEach((section, sectionIndex) => {
            const worksheetName = (section.title || 'Report').replace(/[\\/?*:[\]]/g, '').slice(0, 31) || `Report ${sectionIndex + 1}`;
            const worksheet = workbook.addWorksheet(worksheetName);
            const metrics = calculateSectionMetrics(section);

            // Columns setup
            worksheet.columns = section.columns.map((column, index) => {
                const isCurr = column.type === 'currency' || /amount|price|total|revenue|fee|dues/i.test(String(column.label || ''));
                return {
                    key: `field${index}`,
                    width: Math.min(48, Math.max(15, String(column.label).length + 5, ...section.rows.slice(0, 150).map(row => safeText(valueFor(row, column, index)).length + 2))),
                    style: {
                        font: { name: 'Arial', size: 9 },
                        ...(isCurr ? { numFmt: '"₱"#,##0.00' } : {}),
                        alignment: {
                            horizontal: isCurr ? 'right' : 'left',
                            vertical: 'middle',
                            wrapText: true
                        }
                    }
                };
            });

            const columnCount = Math.max(1, section.columns.length);
            const addMergedLine = (text, style = {}) => {
                const row = worksheet.addRow([text]);
                if (columnCount > 1) worksheet.mergeCells(row.number, 1, row.number, columnCount);
                row.alignment = { vertical: 'middle', wrapText: true, indent: style.indent || 0 };
                row.height = style.height || 22;
                row.font = {
                    name: 'Arial',
                    ...(style.font || {}),
                    ...(style.color ? { color: { argb: style.color } } : {})
                };
                if (style.fill) {
                    row.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: style.fill } };
                }
                return row;
            };

            // Brand Header Row
            const brandRow = addMergedLine('OCCASERVE ENTERPRISE REPORT', {
                font: { bold: true, size: 10 },
                color: 'FFF07835',
                height: 48,
                indent: 5
            });

            worksheet.addImage(brandImageId, {
                tl: { col: 0, row: brandRow.number - 1 },
                ext: { width: 44, height: 44 }
            });

            // Report Title
            addMergedLine(config.title || 'OccaServe Official Report', {
                font: { bold: true, size: 14 },
                color: 'FF0F172A',
                height: 26
            });

            if (config.catererName) {
                addMergedLine(`Caterer Partner: ${config.catererName}`, {
                    font: { bold: true, size: 11 },
                    color: 'FF334155',
                    height: 20
                });
            }

            const metadata = [`Generated ${config.generatedAt || new Date().toLocaleString()}`, ...(config.metadata || [])];
            const metadataRow = addMergedLine(metadata.filter(Boolean).join(' · '), {
                font: { size: 9 },
                color: 'FF64748B',
                height: 18
            });
            metadataRow.border = { bottom: { style: 'medium', color: { argb: 'FFF07835' } } };

            worksheet.addRow([]); // Blank spacer

            // KPI Summary block in Excel
            if (metrics.totalRows > 0) {
                const kpiTitleRow = addMergedLine('EXECUTIVE SNAPSHOT', {
                    font: { bold: true, size: 9 },
                    color: 'FF64748B',
                    height: 18
                });
                kpiTitleRow.border = { bottom: { style: 'thin', color: { argb: 'FFE2E8F0' } } };

                const kpiRow = worksheet.addRow([]);
                kpiRow.height = 24;
                const kpiValRow = worksheet.addRow([]);
                kpiValRow.height = 28;

                kpiRow.getCell(1).value = 'TOTAL RECORDS';
                kpiRow.getCell(1).font = { name: 'Arial', size: 9, bold: true, color: { argb: 'FF64748B' } };
                kpiValRow.getCell(1).value = metrics.totalRows;
                kpiValRow.getCell(1).font = { name: 'Arial', size: 13, bold: true, color: { argb: 'FF0F172A' } };

                if (metrics.hasCurrency) {
                    kpiRow.getCell(2).value = 'TOTAL GROSS AMOUNT';
                    kpiRow.getCell(2).font = { name: 'Arial', size: 9, bold: true, color: { argb: 'FFC2410C' } };
                    kpiValRow.getCell(2).value = metrics.currencySum;
                    kpiValRow.getCell(2).numFmt = '"₱"#,##0.00';
                    kpiValRow.getCell(2).font = { name: 'Arial', size: 13, bold: true, color: { argb: 'FFF07835' } };

                    if (columnCount >= 3) {
                        kpiRow.getCell(3).value = 'AVERAGE AMOUNT';
                        kpiRow.getCell(3).font = { name: 'Arial', size: 9, bold: true, color: { argb: 'FF64748B' } };
                        kpiValRow.getCell(3).value = metrics.avgAmount;
                        kpiValRow.getCell(3).numFmt = '"₱"#,##0.00';
                        kpiValRow.getCell(3).font = { name: 'Arial', size: 13, bold: true, color: { argb: 'FF0F172A' } };
                    }
                }
                worksheet.addRow([]); // Blank spacer
            }

            if (section.title) {
                addMergedLine(section.title, { font: { bold: true, size: 11 }, color: 'FF0F172A', height: 22 });
            }

            // Table Header Row
            const headerRow = worksheet.addRow(section.columns.map(column => column.label));
            const headerRowNumber = headerRow.number;
            headerRow.height = 26;
            headerRow.font = { name: 'Arial', size: 10, bold: true, color: { argb: 'FFFFFFFF' } };
            headerRow.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF0F172A' } };
            headerRow.alignment = { vertical: 'middle', horizontal: 'left', wrapText: true };

            // Align header for currency columns to right
            section.columns.forEach((col, cIndex) => {
                const isCurr = col.type === 'currency' || /amount|price|total|revenue|fee|dues/i.test(String(col.label || ''));
                if (isCurr) {
                    headerRow.getCell(cIndex + 1).alignment = { vertical: 'middle', horizontal: 'right', wrapText: true };
                }
            });

            // Data Rows
            let startDataRow = headerRowNumber + 1;
            if (section.columns.length && section.rows.length) {
                section.rows.forEach(row => {
                    const rowValues = section.columns.map((column, index) => {
                        const val = valueFor(row, column, index);
                        const isCurr = column.type === 'currency' || /amount|price|total|revenue|fee|dues/i.test(String(column.label || ''));
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

            // Excel Footer Row with =SUM() Formula
            if (metrics.hasCurrency && metrics.totalRows > 0) {
                const colLetter = String.fromCharCode(65 + metrics.currencyColIndex);
                const totalRowValues = new Array(section.columns.length).fill('');
                totalRowValues[0] = `TOTAL (${metrics.totalRows} ENTRIES)`;
                const totalExcelRow = worksheet.addRow(totalRowValues);
                totalExcelRow.height = 24;
                totalExcelRow.font = { name: 'Arial', size: 10, bold: true, color: { argb: 'FF0F172A' } };
                totalExcelRow.getCell(metrics.currencyColIndex + 1).value = {
                    formula: `SUM(${colLetter}${startDataRow}:${colLetter}${endDataRow})`,
                    result: metrics.currencySum
                };
                totalExcelRow.getCell(metrics.currencyColIndex + 1).numFmt = '"₱"#,##0.00';
                totalExcelRow.getCell(metrics.currencyColIndex + 1).font = { name: 'Arial', size: 11, bold: true, color: { argb: 'FFF07835' } };

                totalExcelRow.eachCell(cell => {
                    cell.border = {
                        top: { style: 'thin', color: { argb: 'FF0F172A' } },
                        bottom: { style: 'double', color: { argb: 'FF0F172A' } }
                    };
                    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF1F5F9' } };
                });
            }

            // Freeze Panes & Auto-filters
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

            // Zebra Striping and Styling
            worksheet.eachRow((row, rowNumber) => {
                if (rowNumber <= headerRowNumber || rowNumber > endDataRow) return;
                const isEven = (rowNumber - headerRowNumber) % 2 === 0;
                row.eachCell(cell => {
                    cell.border = { bottom: { style: 'thin', color: { argb: 'FFE2E8F0' } } };
                    if (isEven) {
                        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF8FAFC' } };
                    }
                    const column = section.columns[cell.col - 1];
                    const isCurr = column && (column.type === 'currency' || /amount|price|total|revenue|fee|dues/i.test(String(column.label || '')));
                    if (isCurr) {
                        cell.alignment = { vertical: 'middle', horizontal: 'right' };
                    }
                });
                row.height = 22;
            });
        });

        const buffer = await workbook.xlsx.writeBuffer();
        saveBlob(new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }), `${fileBase(config)}.xlsx`);
    }

    // =========================================================================
    // PDF EXPORT GENERATOR - EXECUTIVE DESIGN WITH KPI CARDS & STATUS BADGES
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

        sections.forEach((section, index) => {
            const metrics = calculateSectionMetrics(section);
            let tableStartY = 112;

            if (index > 0 && doc.lastAutoTable) {
                tableStartY = doc.lastAutoTable.finalY + 24;
            }

            const needsNewPage = index > 0 && (tableStartY > pageHeight - 120);
            if (needsNewPage) {
                doc.addPage();
                tableStartY = 112;
            }

            const drawPageHeader = () => {
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(9);
                doc.setTextColor(240, 120, 53);
                doc.addImage(brandImage, 'PNG', margin, 12, 42, 42);
                doc.text('OCCASERVE OFFICIAL REPORT', margin + 50, 34);

                doc.setFontSize(15);
                doc.setTextColor(15, 23, 42);
                const titleLines = doc.splitTextToSize(config.title || 'Official Report', pageWidth - margin * 2 - 60);
                doc.text(titleLines, margin, 58);

                doc.setFont('helvetica', 'normal');
                doc.setFontSize(8);
                doc.setTextColor(100, 116, 139);
                const subtitle = [config.catererName ? `Caterer: ${config.catererName}` : null, `Generated ${config.generatedAt || new Date().toLocaleString()}`, ...(config.metadata || [])].filter(Boolean).join(' · ');
                const subtitleLines = doc.splitTextToSize(subtitle, pageWidth - margin * 2);
                doc.text(subtitleLines, margin, 74);

                // Orange Brand Accent Rule
                doc.setDrawColor(240, 120, 53);
                doc.setLineWidth(1.5);
                doc.line(margin, 84, pageWidth - margin, 84);
            };

            if (!index || needsNewPage) drawPageHeader();

            // Draw KPI Metric Cards on Page 1 if currency metrics exist
            if (index === 0 && metrics.totalRows > 0) {
                const cardY = 94;
                const cardH = 34;
                const cardW = 160;

                // Card 1: Total Records
                doc.setFillColor(248, 250, 252);
                doc.setDrawColor(226, 232, 240);
                doc.roundedRect(margin, cardY, cardW, cardH, 4, 4, 'FD');
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(7);
                doc.setTextColor(100, 116, 139);
                doc.text('TOTAL RECORDS', margin + 8, cardY + 12);
                doc.setFontSize(12);
                doc.setTextColor(15, 23, 42);
                doc.text(String(metrics.totalRows), margin + 8, cardY + 27);

                if (metrics.hasCurrency) {
                    // Card 2: Total Gross Sum (Highlighted)
                    const card2X = margin + cardW + 12;
                    doc.setFillColor(255, 247, 237);
                    doc.setDrawColor(254, 215, 170);
                    doc.roundedRect(card2X, cardY, cardW + 20, cardH, 4, 4, 'FD');
                    doc.setFont('helvetica', 'bold');
                    doc.setFontSize(7);
                    doc.setTextColor(194, 65, 12);
                    doc.text('TOTAL GROSS AMOUNT', card2X + 8, cardY + 12);
                    doc.setFontSize(12);
                    doc.setTextColor(240, 120, 53);
                    doc.text(formatCurrency(metrics.currencySum), card2X + 8, cardY + 27);

                    // Card 3: Average Amount
                    const card3X = card2X + cardW + 32;
                    doc.setFillColor(248, 250, 252);
                    doc.setDrawColor(226, 232, 240);
                    doc.roundedRect(card3X, cardY, cardW, cardH, 4, 4, 'FD');
                    doc.setFont('helvetica', 'bold');
                    doc.setFontSize(7);
                    doc.setTextColor(100, 116, 139);
                    doc.text('AVERAGE AMOUNT', card3X + 8, cardY + 12);
                    doc.setFontSize(12);
                    doc.setTextColor(15, 23, 42);
                    doc.text(formatCurrency(metrics.avgAmount), card3X + 8, cardY + 27);
                }

                tableStartY = cardY + cardH + 16;
            }

            if (section.title) {
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(11);
                doc.setTextColor(15, 23, 42);
                const titleLines = doc.splitTextToSize(section.title, pageWidth - margin * 2);
                doc.text(titleLines, margin, tableStartY);
                tableStartY += titleLines.length * 14;
            }

            const columnCount = Math.max(1, section.columns.length);
            const sectionStartPage = doc.internal.getCurrentPageInfo().pageNumber;
            const pdfColumnWeights = wordColumnWeights(section);
            const totalPdfColumnWeight = pdfColumnWeights.reduce((sum, weight) => sum + weight, 0) || 1;

            // Prepare Foot Row
            let footData = null;
            if (metrics.hasCurrency && metrics.totalRows > 0) {
                const footRow = new Array(section.columns.length).fill('');
                footRow[0] = `TOTAL (${metrics.totalRows})`;
                footRow[metrics.currencyColIndex] = formatCurrency(metrics.currencySum);
                footData = [footRow];
            }

            doc.autoTable({
                startY: tableStartY,
                head: [section.columns.map(column => column.label)],
                body: section.rows.map(row => section.columns.map((column, columnIndex) => {
                    const isCurr = column.type === 'currency' || /amount|price|total|revenue|fee|dues/i.test(String(column.label || ''));
                    return isCurr ? formatCurrency(valueFor(row, column, columnIndex)) : safeText(valueFor(row, column, columnIndex));
                })),
                foot: footData,
                margin: { top: 96, left: margin, right: margin, bottom: 32 },
                theme: 'grid',
                styles: {
                    font: 'helvetica',
                    fontSize: Math.max(6, Math.min(8.5, 8.5 - Math.max(0, columnCount - 6) * 0.4)),
                    cellPadding: columnCount > 8 ? 3.5 : 5.5,
                    overflow: 'linebreak',
                    valign: 'middle',
                    textColor: [30, 41, 59],
                    lineColor: [226, 232, 240],
                    lineWidth: 0.5
                },
                headStyles: {
                    fillColor: [15, 23, 42],
                    textColor: [255, 255, 255],
                    fontStyle: 'bold',
                    valign: 'middle'
                },
                footStyles: {
                    fillColor: [241, 245, 249],
                    textColor: [15, 23, 42],
                    fontStyle: 'bold',
                    lineWidth: 0.8,
                    lineColor: [15, 23, 42]
                },
                alternateRowStyles: {
                    fillColor: [248, 250, 252]
                },
                columnStyles: Object.fromEntries(section.columns.map((column, columnIndex) => {
                    const isCurr = column.type === 'currency' || /amount|price|total|revenue|fee|dues/i.test(String(column.label || ''));
                    return [
                        columnIndex,
                        {
                            cellWidth: (pageWidth - margin * 2) * pdfColumnWeights[columnIndex] / totalPdfColumnWeight,
                            halign: isCurr ? 'right' : 'left'
                        }
                    ];
                })),
                didDrawCell: (data) => {
                    // Draw soft badge pills behind status cells in the body
                    if (data.section === 'body') {
                        const rawText = String(data.cell.raw || '').trim().toLowerCase();
                        let badgeColor = null;

                        if (/^(confirmed|completed|paid|active|approved|verified)$/i.test(rawText)) {
                            badgeColor = [220, 252, 231]; // soft green
                        } else if (/^(pending|partial|review|draft)$/i.test(rawText)) {
                            badgeColor = [254, 249, 195]; // soft yellow
                        } else if (/^(cancelled|rejected|failed|unpaid|disputed)$/i.test(rawText)) {
                            badgeColor = [254, 226, 226]; // soft red
                        }

                        if (badgeColor) {
                            const padding = 2;
                            doc.setFillColor(badgeColor[0], badgeColor[1], badgeColor[2]);
                            doc.roundedRect(
                                data.cell.x + padding,
                                data.cell.y + padding,
                                data.cell.width - padding * 2,
                                data.cell.height - padding * 2,
                                3, 3, 'F'
                            );
                            // redraw text in crisp color over pill
                            doc.setFont('helvetica', 'bold');
                            doc.setFontSize(data.cell.styles.fontSize);
                            doc.setTextColor(30, 41, 59);
                            doc.text(
                                String(data.cell.raw),
                                data.cell.x + padding + 4,
                                data.cell.y + data.cell.height / 2 + 2.5
                            );
                        }
                    }
                },
                didDrawPage: () => {
                    if (doc.internal.getCurrentPageInfo().pageNumber > sectionStartPage) {
                        drawPageHeader();
                    }
                    doc.setFont('helvetica', 'normal');
                    doc.setFontSize(8);
                    doc.setTextColor(100, 116, 139);
                    doc.text('OccaServe Event Platform · Official & Confidential Report', margin, pageHeight - 16);
                }
            });
        });

        const pageCount = doc.internal.getNumberOfPages();
        for (let pageNumber = 1; pageNumber <= pageCount; pageNumber += 1) {
            doc.setPage(pageNumber);
            doc.setFont('helvetica', 'normal');
            doc.setFontSize(8);
            doc.setTextColor(100, 116, 139);
            doc.text(`Page ${pageNumber} of ${pageCount}`, pageWidth - margin, pageHeight - 16, { align: 'right' });
        }
        doc.save(`${fileBase(config)}.pdf`);
    }

    function printReport(config, sections) {
        const win = window.open('', '_blank');
        if (!win) throw new Error('Please allow pop-ups to print this report.');
        const sectionHtml = sections.map(section => {
            const metrics = calculateSectionMetrics(section);
            const kpiHtml = metrics.totalRows > 0 ? `
                <div style="display:flex;gap:12px;margin-bottom:14px;">
                    <div style="padding:10px 14px;border:1px solid #cbd5e1;border-radius:8px;background:#f8fafc;">
                        <div style="font-size:9px;font-weight:700;color:#64748b;">TOTAL RECORDS</div>
                        <div style="font-size:16px;font-weight:800;color:#0f172a;">${metrics.totalRows}</div>
                    </div>
                    ${metrics.hasCurrency ? `
                    <div style="padding:10px 14px;border:1px solid #fed7aa;border-radius:8px;background:#fff7ed;">
                        <div style="font-size:9px;font-weight:700;color:#c2410c;">TOTAL GROSS SUM</div>
                        <div style="font-size:16px;font-weight:800;color:#f07835;">${formatCurrency(metrics.currencySum)}</div>
                    </div>` : ''}
                </div>
            ` : '';

            return `
                <section>
                    ${section.title ? `<h2>${escapeHtml(section.title)}</h2>` : ''}
                    ${kpiHtml}
                    <table>
                        <thead>
                            <tr>${section.columns.map(column => `<th>${escapeHtml(column.label)}</th>`).join('')}</tr>
                        </thead>
                        <tbody>
                            ${section.rows.map(row => `<tr>${section.columns.map((column, index) => {
                                const isCurr = column.type === 'currency' || /amount|price|total|revenue|fee|dues/i.test(String(column.label || ''));
                                return `<td style="${isCurr ? 'text-align:right;font-weight:600;' : ''}">${escapeHtml(isCurr ? formatCurrency(valueFor(row, column, index)) : valueFor(row, column, index))}</td>`;
                            }).join('')}</tr>`).join('')}
                        </tbody>
                        ${metrics.hasCurrency && metrics.totalRows > 0 ? `
                        <tfoot>
                            <tr style="background:#f1f5f9;font-weight:bold;">
                                <td>TOTAL (${metrics.totalRows})</td>
                                ${section.columns.slice(1).map((col, idx) => {
                                    if (idx + 1 === metrics.currencyColIndex) {
                                        return `<td style="text-align:right;color:#f07835;">${formatCurrency(metrics.currencySum)}</td>`;
                                    }
                                    return '<td></td>';
                                }).join('')}
                            </tr>
                        </tfoot>` : ''}
                    </table>
                </section>
            `;
        }).join('');

        win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${escapeHtml(config.title || 'OccaServe Report')}</title><style>@page{size:landscape;margin:12mm}body{font:10px/1.45 'Segoe UI',Arial,sans-serif;color:#0f172a}.brand{display:flex;align-items:center;gap:10px;margin-bottom:10px;color:#f07835;font-size:14px;font-weight:800;letter-spacing:.08em}.brand img{width:42px;height:42px;object-fit:contain}header{border-bottom:2px solid #f07835;padding-bottom:10px;margin-bottom:14px}h1{font-size:18px;line-height:1.2;margin:0 0 4px 0;color:#0f172a}header small{display:block;color:#64748b;font-size:9.5px}section{margin:14px 0 18px;break-inside:avoid}h2{font-size:12px;color:#0f172a;margin:0 0 8px}table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:8.5px}th,td{border:1px solid #cbd5e1;padding:5px 6px;text-align:left;vertical-align:middle;overflow-wrap:anywhere}th{background:#0f172a;color:white;font-weight:700}tr:nth-child(even){background:#f8fafc}footer{position:fixed;bottom:0;color:#64748b;font-size:8px}</style></head><body><header><div class="brand"><img src="${window.location.origin}/static/images/brand_icon.png" alt="">OCCASERVE OFFICIAL REPORT</div><h1>${escapeHtml(config.title || 'Report')}</h1><small>${escapeHtml([config.catererName ? `Caterer: ${config.catererName}` : null, `Generated ${config.generatedAt || new Date().toLocaleString()}`, ...(config.metadata || [])].filter(Boolean).join(' · '))}</small></header>${sectionHtml}<footer>OccaServe · Official & Confidential Platform Report</footer><script>window.onload=()=>window.print()<\/script></body></html>`);
        win.document.close();
    }

    window.OccaExportPreview = { open: createPreview };
}());
