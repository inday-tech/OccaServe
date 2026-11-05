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
        const amount = Number(value);
        return Number.isFinite(amount)
            ? `₱${amount.toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            : safeText(value);
    }

    function appendReportHeader(sheet, config) {
        const brand = document.createElement('div');
        brand.className = 'occa-export-document-brand';
        const logo = document.createElement('img');
        logo.src = '/static/images/brand_icon.png';
        logo.alt = '';
        brand.appendChild(logo);
        const brandName = document.createElement('strong');
        brandName.textContent = 'OCCASERVE';
        brand.appendChild(brandName);
        sheet.appendChild(brand);

        const heading = document.createElement('h1');
        heading.textContent = config.title || 'OccaServe Report';
        sheet.appendChild(heading);
        if (config.catererName) {
            const caterer = document.createElement('div');
            caterer.className = 'occa-export-caterer';
            caterer.textContent = config.catererName;
            sheet.appendChild(caterer);
        }
        const metadata = document.createElement('div');
        metadata.className = 'occa-export-meta';
        metadata.textContent = [`Generated ${config.generatedAt || new Date().toLocaleString()}`]
            .concat(config.metadata || []).filter(Boolean).join(' · ');
        sheet.appendChild(metadata);
    }

    function appendReportSummary(sheet, config, format) {
        const summary = config.summary;
        if (!summary || (!summary.items?.length && !summary.statusBreakdown?.length)) return;
        const section = document.createElement('section');
        section.className = 'occa-export-summary';
        const title = document.createElement('h2');
        title.textContent = 'Report summary';
        section.appendChild(title);
        if (format === 'word') {
            (summary.items || []).forEach(item => {
                const line = document.createElement('p');
                const label = document.createElement('strong');
                label.textContent = `${item.label}: `;
                line.append(label, document.createTextNode(item.value));
                section.appendChild(line);
            });
            if (summary.statusBreakdown?.length) {
                const breakdownTitle = document.createElement('h3');
                breakdownTitle.textContent = 'Payment status breakdown';
                section.appendChild(breakdownTitle);
                summary.statusBreakdown.forEach(item => {
                    const line = document.createElement('p');
                    line.textContent = `${item.label}: ${item.count}`;
                    section.appendChild(line);
                });
            }
            sheet.appendChild(section);
            return;
        }
        const summaryTable = document.createElement('table');
        summaryTable.className = 'occa-export-summary-table';
        const summaryBody = document.createElement('tbody');
        if (format !== 'pdf') {
            const summaryHead = document.createElement('thead');
            const summaryHeadRow = document.createElement('tr');
            ['Metric', 'Value'].forEach(label => {
                const cell = document.createElement('th');
                cell.textContent = label;
                summaryHeadRow.appendChild(cell);
            });
            summaryHead.appendChild(summaryHeadRow);
            summaryTable.appendChild(summaryHead);
        }
        [...(summary.items || []), ...(summary.statusBreakdown || []).map(item => ({
            label: `Payment status · ${item.label}`,
            value: String(item.count)
        }))].forEach(item => {
            const row = document.createElement('tr');
            [item.label, item.value].forEach(value => {
                const cell = document.createElement('td');
                cell.textContent = value;
                row.appendChild(cell);
            });
            summaryBody.appendChild(row);
        });
        summaryTable.appendChild(summaryBody);
        section.appendChild(summaryTable);
        sheet.appendChild(section);
    }

    function renderFormatPreview(config, sections, format) {
        const sheet = document.createElement('article');
        sheet.className = `occa-export-sheet occa-export-sheet-${format}`;
        if (format === 'csv') {
            const preview = document.createElement('pre');
            preview.className = 'occa-export-csv-preview';
            preview.textContent = buildCsvContent(config, sections).replace(/^\uFEFF/, '');
            sheet.appendChild(preview);
            return sheet;
        }
        appendReportHeader(sheet, config);
        appendReportSummary(sheet, config, format);
        sections.forEach(section => {
            const sectionEl = document.createElement('section');
            sectionEl.className = 'occa-export-section';
            if (section.title) {
                const sectionTitle = document.createElement('h2');
                sectionTitle.textContent = section.title;
                sectionEl.appendChild(sectionTitle);
            }
            if (!section.columns.length || !section.rows.length) {
                const empty = document.createElement('div');
                empty.className = 'occa-export-empty';
                empty.textContent = section.rows.length ? 'No columns available.' : 'No matching records.';
                sectionEl.appendChild(empty);
            } else {
                const wrap = document.createElement('div');
                wrap.className = 'occa-export-table-wrap';
                const table = document.createElement('table');
                table.className = 'occa-export-table';
                if (format === 'xlsx') {
                    table.style.minWidth = `${Math.max(760, section.columns.length * 112)}px`;
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
                        td.textContent = column.type === 'currency' ? formatCurrency(value) : safeText(value);
                        if (column.type === 'currency') td.classList.add('is-currency');
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
        const toolbar = document.createElement('div');
        toolbar.className = 'occa-export-toolbar';
        toolbar.innerHTML = `<div class="occa-export-brand"><img src="/static/images/brand_icon.png" alt="OccaServe logo"><div><span>OccaServe</span><strong>${escapeHtml(config.title || 'Report Preview')}</strong></div></div>`;
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'occa-export-close';
        closeButton.setAttribute('aria-label', 'Close preview');
        closeButton.textContent = '×';
        toolbar.appendChild(closeButton);

        const content = document.createElement('main');
        content.className = 'occa-export-content';
        const formatNav = document.createElement('nav');
        formatNav.className = 'occa-export-formats';
        formatNav.setAttribute('aria-label', 'Preview format');
        const formatOptions = [
            ['pdf', 'PDF', '.pdf', 'fa-file-pdf'],
            ['xlsx', 'Excel', '.xlsx', 'fa-file-excel'],
            ['csv', 'CSV', '.csv', 'fa-file-csv'],
            ['word', 'Word', '.docx', 'fa-file-word']
        ];
        const previewHost = document.createElement('div');
        previewHost.className = 'occa-export-preview-host';
        const formatButtons = new Map();
        const formatLabels = new Map(formatOptions.map(([format, label, extension]) => [format, { label, extension }]));
        let selectedFormat = 'pdf';
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
        const previewLabel = document.createElement('div');
        previewLabel.className = 'occa-export-preview-label';
        const previewTitle = document.createElement('span');
        previewLabel.appendChild(previewTitle);
        const previewHint = document.createElement('small');
        previewLabel.appendChild(previewHint);
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
            previewTitle.textContent = `${option.label} report preview`;
            previewHint.textContent = `Previewing ${option.extension} file`;
            downloadButton.innerHTML = `<i class="fas fa-download" aria-hidden="true"></i><span>Download ${option.label}</span>`;
            previewHost.replaceChildren(renderFormatPreview(config, sections, format));
            previewHost.scrollTop = 0;
            previewHost.scrollLeft = 0;
        }
        content.replaceChildren(formatNav, previewLabel, previewHost);

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
            textButton.textContent = 'Download TXT';
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
        footerNote.textContent = 'Your report includes the records and filters selected on this page.';
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

    function csvCell(value) {
        let text = safeText(value);
        if (/^[\s]*[=+\-@]/.test(text)) text = `'${text}`;
        return `"${text.replace(/"/g, '""')}"`;
    }

    function buildCsvContent(config, sections) {
        const lines = [];
        if (config.summary) {
            lines.push([config.title || 'OccaServe Report']);
            if (config.catererName) lines.push(['Caterer', config.catererName]);
            lines.push(['Generated', config.generatedAt || new Date().toLocaleString()]);
            (config.metadata || []).forEach(item => lines.push(['Filter', item]));
            if (config.summary.items?.length || config.summary.statusBreakdown?.length) {
                lines.push([], ['Report summary'], ['Metric', 'Value']);
                (config.summary.items || []).forEach(item => lines.push([item.label, item.value]));
                if (config.summary.statusBreakdown?.length) {
                    lines.push([], ['Payment status breakdown'], ['Status', 'Count']);
                    config.summary.statusBreakdown.forEach(item => lines.push([item.label, item.count]));
                }
            }
            lines.push([]);
        }
        if (sections.length > 1) lines.push([config.title || 'OccaServe Report'], [`Generated ${config.generatedAt || new Date().toLocaleString()}`], []);
        sections.forEach(section => {
            if (sections.length > 1 && section.title) lines.push([section.title]);
            lines.push(section.columns.map(column => column.label));
            section.rows.forEach(row => lines.push(section.columns.map((column, index) => valueFor(row, column, index))));
            lines.push([]);
        });
        return '\ufeff' + lines.map(row => row.map(csvCell).join(',')).join('\r\n');
    }

    function downloadCsv(config, sections) {
        const csv = buildCsvContent(config, sections);
        saveBlob(new Blob([csv], { type: 'text/csv;charset=utf-8' }), `${fileBase(config)}.csv`);
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

    async function download(config, sections, format, button, status, formatLabels) {
        const label = formatLabels.get(format).label;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i><span>Preparing…</span>';
        status.textContent = `Preparing ${label} report…`;
        status.classList.remove('is-success', 'is-error');
        try {
            if (format === 'csv') downloadCsv(config, sections);
            else if (format === 'xlsx') await downloadXlsx(config, sections);
            else if (format === 'word') await downloadWordDocument(config, sections);
            else await downloadPdf(config, sections);
            status.textContent = `${label} report downloaded successfully.`;
            status.classList.add('is-success');
            if (typeof window.showToast === 'function') window.showToast(`${label} report downloaded.`, 'success');
        } catch (error) {
            console.error('OccaServe report export failed:', error);
            status.textContent = error.message || `Could not generate the ${label} report.`;
            status.classList.add('is-error');
            if (window.showError) window.showError(status.textContent);
            else window.alert(status.textContent);
        } finally {
            button.disabled = false;
            const option = formatLabels.get(format);
            button.innerHTML = `<i class="fas fa-download" aria-hidden="true"></i><span>Download ${option.label}</span>`;
        }
    }

    async function downloadWordDocument(config, sections) {
        if (config.wordUrl) {
            const response = await fetch(config.wordUrl, { credentials: 'same-origin' });
            if (!response.ok) throw new Error('Word report could not be generated.');
            const blob = await response.blob();
            const disposition = response.headers.get('Content-Disposition') || '';
            const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || `${fileBase(config)}.docx`;
            saveBlob(blob, filename);
            return;
        }
        await loadLibrary(libraries.docx);
        const word = window.docx;
        if (!word || !word.Document || !word.Packer) throw new Error('Word document library is unavailable.');
        const children = [
            new word.Paragraph({ children: [new word.TextRun({ text: 'OCCASERVE', bold: true, color: 'F07835', size: 24 })], spacing: { after: 120 } }),
            new word.Paragraph({ text: config.title || 'OccaServe Report', heading: word.HeadingLevel.TITLE }),
            ...(config.catererName ? [new word.Paragraph({ text: config.catererName, heading: word.HeadingLevel.HEADING_2 })] : []),
            new word.Paragraph({ text: `Generated ${config.generatedAt || new Date().toLocaleString()}${(config.metadata || []).length ? ` · ${(config.metadata || []).join(' · ')}` : ''}`, spacing: { after: 240 } })
        ];
        appendWordSummary(word, children, config);
        const pageWidth = 16838;
        const margins = { top: 600, right: 540, bottom: 600, left: 540 };
        const tableWidth = pageWidth - margins.left - margins.right;
        sections.forEach(section => {
            if (section.title) children.push(new word.Paragraph({ text: section.title, heading: word.HeadingLevel.HEADING_1, spacing: { before: 240, after: 120 } }));
            const widths = wordColumnWidths(section, tableWidth);
            const rows = [new word.TableRow({
                children: section.columns.map((column, index) => makeWordCell(word, column.label, true, widths[index])),
                tableHeader: true
            })];
            section.rows.forEach(row => rows.push(new word.TableRow({
                cantSplit: true,
                children: section.columns.map((column, index) => makeWordCell(
                    word,
                    column.type === 'currency' ? formatCurrency(valueFor(row, column, index)) : valueFor(row, column, index),
                    false,
                    widths[index]
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

    function appendWordSummary(word, children, config) {
        const summary = config.summary;
        if (!summary || (!summary.items?.length && !summary.statusBreakdown?.length)) return;
        children.push(new word.Paragraph({ text: 'Report summary', heading: word.HeadingLevel.HEADING_1, spacing: { before: 240, after: 120 } }));
        (summary.items || []).forEach(item => children.push(new word.Paragraph({ text: `${item.label}: ${item.value}` })));
        if (summary.statusBreakdown?.length) {
            children.push(new word.Paragraph({ text: 'Payment status breakdown', heading: word.HeadingLevel.HEADING_2, spacing: { before: 160, after: 80 } }));
            summary.statusBreakdown.forEach(item => children.push(new word.Paragraph({ text: `${item.label}: ${item.count}` })));
        }
    }

    function makeWordCell(word, value, header = false, width) {
        return new word.TableCell({
            children: [new word.Paragraph({
                spacing: { before: 0, after: 0 },
                children: [new word.TextRun({
                    text: safeText(value),
                    bold: header,
                    color: header ? 'FFFFFF' : '1E293B',
                    size: header ? 17 : 16
                })]
            })],
            shading: header ? { fill: '172033', type: word.ShadingType.CLEAR } : undefined,
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

    async function downloadXlsx(config, sections) {
        await loadScript(libraries.xlsx);
        if (!window.ExcelJS) throw new Error('Excel workbook library is unavailable.');
        const workbook = new ExcelJS.Workbook();
        workbook.creator = 'OccaServe';
        workbook.created = new Date();
        if (config.summary) {
            const summarySheet = workbook.addWorksheet('Summary');
            summarySheet.addRows([
                [config.title || 'OccaServe Report'],
                ...(config.catererName ? [['Caterer', config.catererName]] : []),
                ['Generated', config.generatedAt || new Date().toLocaleString()],
                ...(config.metadata || []).map(item => ['Filter', item]),
                [],
                ['Report summary'],
                ['Metric', 'Value'],
                ...(config.summary.items || []).map(item => [item.label, item.value]),
                ...(config.summary.statusBreakdown?.length ? [[], ['Payment status breakdown'], ['Status', 'Count']] : []),
                ...(config.summary.statusBreakdown || []).map(item => [item.label, item.count])
            ]);
            summarySheet.columns = [{ width: 30 }, { width: 28 }];
            summarySheet.pageSetup = {
                paperSize: 9,
                orientation: 'landscape',
                fitToPage: true,
                fitToWidth: 1,
                fitToHeight: 1,
                margins: { left: 0.35, right: 0.35, top: 0.5, bottom: 0.5, header: 0.2, footer: 0.2 }
            };
            summarySheet.getRow(1).font = { bold: true, size: 16, color: { argb: 'FF0F172A' } };
            summarySheet.eachRow((row, rowNumber) => {
                row.eachCell(cell => {
                    if (rowNumber !== 1) cell.border = { bottom: { style: 'thin', color: { argb: 'FFCBD5E1' } } };
                    cell.alignment = { vertical: 'middle', wrapText: true };
                });
            });
            summarySheet.eachRow(row => {
                if (['Report summary', 'Metric', 'Payment status breakdown', 'Status'].includes(String(row.getCell(1).value || ''))) {
                    row.font = { bold: true, color: { argb: 'FFFFFFFF' } };
                    row.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF0F172A' } };
                }
            });
        }
        sections.forEach((section, sectionIndex) => {
            const worksheetName = (section.title || 'Report').replace(/[\\/?*:[\]]/g, '').slice(0, 31) || `Report ${sectionIndex + 1}`;
            const worksheet = workbook.addWorksheet(worksheetName);
            worksheet.columns = section.columns.map((column, index) => ({
                header: column.label,
                key: `field${index}`,
                width: Math.min(48, Math.max(14, String(column.label).length + 4, ...section.rows.slice(0, 150).map(row => safeText(valueFor(row, column, index)).length + 2))),
                style: column.type === 'currency' ? { numFmt: '"PHP "#,##0.00' } : column.type === 'number' ? { numFmt: '#,##0.##' } : {}
            }));
            section.rows.forEach(row => worksheet.addRow(Object.fromEntries(section.columns.map((column, index) => [`field${index}`, valueFor(row, column, index)]))));
            worksheet.views = [{ state: 'frozen', ySplit: 1 }];
            worksheet.pageSetup = {
                paperSize: 9,
                orientation: 'landscape',
                fitToPage: true,
                fitToWidth: 1,
                fitToHeight: 0,
                margins: { left: 0.25, right: 0.25, top: 0.5, bottom: 0.5, header: 0.2, footer: 0.2 }
            };
            worksheet.autoFilter = { from: { row: 1, column: 1 }, to: { row: Math.max(1, worksheet.rowCount), column: Math.max(1, section.columns.length) } };
            const heading = worksheet.getRow(1);
            heading.height = 24;
            heading.font = { bold: true, color: { argb: 'FFFFFFFF' } };
            heading.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF0F172A' } };
            heading.alignment = { vertical: 'middle', wrapText: true };
            worksheet.eachRow((row, rowNumber) => {
                let rowLines = 1;
                row.eachCell(cell => {
                    cell.border = { bottom: { style: 'thin', color: { argb: 'FFCBD5E1' } } };
                    if (rowNumber > 1 && rowNumber % 2 === 0) cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF1F5F9' } };
                    cell.alignment = { vertical: 'top', wrapText: true };
                    const columnWidth = worksheet.getColumn(cell.col).width || 14;
                    const value = cell.value && typeof cell.value === 'object' && 'text' in cell.value
                        ? cell.value.text
                        : cell.value;
                    rowLines = Math.max(rowLines, estimateWrappedLines(value, columnWidth));
                });
                row.height = Math.min(409, Math.max(22, rowLines * 14 + 8));
            });
        });
        const buffer = await workbook.xlsx.writeBuffer();
        saveBlob(new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }), `${fileBase(config)}.xlsx`);
    }

    async function downloadPdf(config, sections) {
        await loadScript(libraries.pdf);
        await loadScript(libraries.table);
        const Pdf = window.jspdf && window.jspdf.jsPDF;
        if (!Pdf) throw new Error('PDF library is unavailable.');
        const doc = new Pdf({ orientation: 'landscape', unit: 'pt', format: 'a4' });
        let brandImage = null;
        try { brandImage = await loadBrandImage(); } catch (_) {}
        const margin = 36;
        sections.forEach((section, index) => {
            if (index) doc.addPage();
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(9);
            doc.setTextColor(240, 120, 53);
            if (brandImage) doc.addImage(brandImage, 'PNG', margin, 13, 18, 18);
            doc.text('OCCASERVE', margin + 22, 30);
            doc.setFontSize(19);
            doc.setTextColor(15, 23, 42);
            const titleLines = doc.splitTextToSize(config.title || 'Report', doc.internal.pageSize.getWidth() - margin * 2);
            doc.text(titleLines, margin, 56);
            doc.setFont('helvetica', 'normal');
            doc.setFontSize(8);
            doc.setTextColor(100, 116, 139);
            const subtitle = [config.catererName, `Generated ${config.generatedAt || new Date().toLocaleString()}`, ...(config.metadata || [])].filter(Boolean).join(' · ');
            const subtitleLines = doc.splitTextToSize(subtitle, doc.internal.pageSize.getWidth() - margin * 2);
            const subtitleY = 56 + titleLines.length * 20 + 4;
            doc.text(subtitleLines, margin, subtitleY);
            let tableStartY = subtitleY + subtitleLines.length * 10 + 12;
            if (!index && config.summary) {
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(9);
                doc.setTextColor(51, 65, 85);
                doc.text('REPORT SUMMARY', margin, tableStartY);
                tableStartY += 14;
                const summaryRows = [
                    ...(config.summary.items || []).map(item => [item.label, item.value]),
                    ...(config.summary.statusBreakdown || []).map(item => [`Payment status · ${item.label}`, String(item.count)])
                ];
                if (summaryRows.length) {
                    doc.autoTable({
                        startY: tableStartY,
                        body: summaryRows,
                        margin: { left: margin, right: margin, bottom: 30 },
                        theme: 'plain',
                        styles: { font: 'helvetica', fontSize: 8, cellPadding: 2, textColor: [51, 65, 85] },
                        columnStyles: { 0: { fontStyle: 'bold', cellWidth: 150 } }
                    });
                    tableStartY = doc.lastAutoTable.finalY + 8;
                }
            }
            if (section.title) {
                doc.setFontSize(11);
                doc.setTextColor(51, 65, 85);
                const titleLines = doc.splitTextToSize(section.title, doc.internal.pageSize.getWidth() - margin * 2);
                doc.text(titleLines, margin, tableStartY);
                tableStartY += titleLines.length * 13 + 4;
            }
            const columnCount = Math.max(1, section.columns.length);
            doc.autoTable({
                startY: tableStartY,
                head: [section.columns.map(column => column.label)],
                body: section.rows.map(row => section.columns.map((column, columnIndex) => column.type === 'currency'
                    ? formatCurrency(valueFor(row, column, columnIndex))
                    : safeText(valueFor(row, column, columnIndex)))),
                margin: { left: margin, right: margin, bottom: 30 },
                theme: 'grid',
                styles: {
                    font: 'helvetica',
                    fontSize: Math.max(5.5, Math.min(8, 8 - Math.max(0, columnCount - 5) * 0.35)),
                    cellPadding: columnCount > 8 ? 3 : 5,
                    overflow: 'linebreak',
                    valign: 'top',
                    textColor: [30, 41, 59]
                },
                headStyles: { fillColor: [15, 23, 42], textColor: [255, 255, 255], fontStyle: 'bold', valign: 'middle' },
                alternateRowStyles: { fillColor: [248, 250, 252] },
                didDrawPage: () => {
                    const pageHeight = doc.internal.pageSize.getHeight();
                    doc.setFontSize(8);
                    doc.setTextColor(100, 116, 139);
                    doc.text('OccaServe · Confidential report', margin, pageHeight - 16);
                }
            });
        });
        const pageCount = doc.internal.getNumberOfPages();
        const pageWidth = doc.internal.pageSize.getWidth();
        const pageHeight = doc.internal.pageSize.getHeight();
        for (let pageNumber = 1; pageNumber <= pageCount; pageNumber += 1) {
            doc.setPage(pageNumber);
            doc.setFontSize(8);
            doc.setTextColor(100, 116, 139);
            doc.text(`Page ${pageNumber} of ${pageCount}`, pageWidth - margin, pageHeight - 16, { align: 'right' });
        }
        doc.save(`${fileBase(config)}.pdf`);
    }

    function printReport(config, sections) {
        const win = window.open('', '_blank');
        if (!win) throw new Error('Allow pop-ups to print this report.');
        const summaryHtml = config.summary ? `<section><h2>Report summary</h2><p>${(config.summary.items || []).map(item => `<strong>${escapeHtml(item.label)}:</strong> ${escapeHtml(item.value)}`).join(' · ')}</p>${config.summary.statusBreakdown?.length ? `<p><strong>Payment status:</strong> ${config.summary.statusBreakdown.map(item => `${escapeHtml(item.label)} (${item.count})`).join(' · ')}</p>` : ''}</section>` : '';
        const sectionHtml = summaryHtml + sections.map(section => `<section><h2>${escapeHtml(section.title)}</h2><table><thead><tr>${section.columns.map(column => `<th>${escapeHtml(column.label)}</th>`).join('')}</tr></thead><tbody>${section.rows.map(row => `<tr>${section.columns.map((column, index) => `<td>${escapeHtml(column.type === 'currency' ? formatCurrency(valueFor(row, column, index)) : valueFor(row, column, index))}</td>`).join('')}</tr>`).join('')}</tbody></table></section>`).join('');
        win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${escapeHtml(config.title || 'OccaServe Report')}</title><style>@page{size:landscape;margin:15mm}body{font:11px/1.5 Arial,sans-serif;color:#0f172a}header{border-bottom:3px solid #F07835;padding-bottom:12px;margin-bottom:20px}header strong{color:#F07835}h1{font-size:22px;margin:10px 0 4px}small{color:#64748b}section{margin:20px 0;break-inside:avoid}h2{font-size:14px}table{width:100%;border-collapse:collapse;font-size:9px}th,td{border:1px solid #dbe3ec;padding:6px;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#0f172a;color:white}tr:nth-child(even){background:#f8fafc}footer{position:fixed;bottom:0;color:#64748b;font-size:9px}</style></head><body><header><strong>OCCASERVE</strong><h1>${escapeHtml(config.title || 'Report')}</h1><small>${escapeHtml([config.catererName, `Generated ${config.generatedAt || new Date().toLocaleString()}`, ...(config.metadata || [])].filter(Boolean).join(' · '))}</small></header>${sectionHtml}<footer>OccaServe · Confidential report</footer><script>window.onload=()=>window.print()<\/script></body></html>`);
        const printStyles = win.document.createElement('style');
        printStyles.textContent = 'section{break-inside:auto!important}h2{break-after:avoid}thead{display:table-header-group}tr{break-inside:avoid}th,td{white-space:pre-wrap;overflow-wrap:anywhere}';
        win.document.head.appendChild(printStyles);
        win.document.close();
    }

    window.OccaExportPreview = { open: createPreview };
}());
