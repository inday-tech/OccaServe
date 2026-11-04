(function () {
    'use strict';

    const libraries = {
        xlsx: 'https://cdn.jsdelivr.net/npm/exceljs@4.4.0/dist/exceljs.min.js',
        pdf: 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js',
        table: 'https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.28/jspdf.plugin.autotable.min.js'
    };
    const loadPromises = new Map();

    function loadScript(src) {
        if (loadPromises.has(src)) return loadPromises.get(src);
        const existing = Array.from(document.scripts).find(script => script.src === src);
        const promise = existing ? Promise.resolve() : new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = () => reject(new Error('Export library failed to load.'));
            document.head.appendChild(script);
        });
        loadPromises.set(src, promise);
        return promise;
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
        toolbar.innerHTML = '<div class="occa-export-brand"><img src="/static/images/brand_icon.png" alt=""><span>OccaServe</span></div>';
        const actions = document.createElement('div');
        actions.className = 'occa-export-actions';
        [['PDF', 'pdf'], ['Excel (.xlsx)', 'xlsx'], ['CSV', 'csv']].forEach(([label, format]) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.dataset.format = format;
            button.textContent = `Download ${label}`;
            button.addEventListener('click', () => download(config, sections, format, button));
            actions.appendChild(button);
        });
        const wordButton = document.createElement('button');
        wordButton.type = 'button';
        wordButton.dataset.format = 'word';
        wordButton.textContent = 'Download Word';
        wordButton.addEventListener('click', () => downloadWord(config, sections, wordButton));
        actions.appendChild(wordButton);
        if (config.textDownload) {
            const textButton = document.createElement('button');
            textButton.type = 'button';
            textButton.dataset.format = 'txt';
            textButton.textContent = 'Download TXT';
            textButton.addEventListener('click', () => downloadText(config, sections));
            actions.appendChild(textButton);
        }
        const printButton = document.createElement('button');
        printButton.type = 'button';
        printButton.dataset.action = 'print';
        printButton.textContent = 'Print';
        printButton.addEventListener('click', () => printReport(config, sections));
        actions.appendChild(printButton);
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'occa-export-close';
        closeButton.setAttribute('aria-label', 'Close preview');
        closeButton.textContent = '×';
        closeButton.addEventListener('click', () => overlay.remove());
        toolbar.append(actions, closeButton);

        const content = document.createElement('main');
        content.className = 'occa-export-content';
        const sheet = document.createElement('article');
        sheet.className = 'occa-export-sheet';
        const heading = document.createElement('h1');
        heading.textContent = config.title || 'OccaServe Report';
        sheet.appendChild(heading);
        const metadata = document.createElement('div');
        metadata.className = 'occa-export-meta';
        const details = [`Generated ${config.generatedAt || new Date().toLocaleString()}`].concat(config.metadata || []);
        metadata.textContent = details.filter(Boolean).join(' · ');
        sheet.appendChild(metadata);

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
                        td.textContent = safeText(valueFor(row, column, index));
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
        content.appendChild(sheet);
        const footer = document.createElement('div');
        footer.className = 'occa-export-footer';
        footer.textContent = 'OccaServe · Report preview uses the records and filters selected on this page.';
        dialog.append(toolbar, content, footer);
        overlay.appendChild(dialog);
        overlay.addEventListener('click', event => { if (event.target === overlay) overlay.remove(); });
        document.addEventListener('keydown', function closeOnEscape(event) {
            if (event.key === 'Escape' && overlay.isConnected) {
                overlay.remove();
                document.removeEventListener('keydown', closeOnEscape);
            }
        });
        document.body.appendChild(overlay);
        closeButton.focus();
    }

    function csvCell(value) {
        let text = safeText(value);
        if (/^[\s]*[=+\-@]/.test(text)) text = `'${text}`;
        return `"${text.replace(/"/g, '""')}"`;
    }

    function downloadCsv(config, sections) {
        const lines = [];
        if (sections.length > 1) lines.push([config.title || 'OccaServe Report'], [`Generated ${config.generatedAt || new Date().toLocaleString()}`], []);
        sections.forEach(section => {
            if (sections.length > 1 && section.title) lines.push([section.title]);
            lines.push(section.columns.map(column => column.label));
            section.rows.forEach(row => lines.push(section.columns.map((column, index) => valueFor(row, column, index))));
            lines.push([]);
        });
        const csv = '\ufeff' + lines.map(row => row.map(csvCell).join(',')).join('\r\n');
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

    async function download(config, sections, format, button) {
        const label = button.textContent;
        button.disabled = true;
        button.textContent = 'Preparing…';
        try {
            if (format === 'csv') return downloadCsv(config, sections);
            if (format === 'xlsx') return await downloadXlsx(config, sections);
            await downloadPdf(config, sections);
        } catch (error) {
            console.error('OccaServe report export failed:', error);
            if (window.showError) window.showError(error.message || 'Could not generate this report.');
            else window.alert(error.message || 'Could not generate this report.');
        } finally {
            button.disabled = false;
            button.textContent = label;
        }
    }

    async function downloadWord(config, sections, button) {
        const label = button.textContent;
        button.disabled = true;
        button.textContent = 'Preparing…';
        try {
            if (config.wordUrl) {
                const response = await fetch(config.wordUrl, { credentials: 'same-origin' });
                if (!response.ok) throw new Error('Word report could not be generated.');
                const blob = await response.blob();
                const disposition = response.headers.get('Content-Disposition') || '';
                const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || `${fileBase(config)}.docx`;
                saveBlob(blob, filename);
            } else {
                const blocks = sections.map(section => `<h2>${escapeHtml(section.title)}</h2><table border="1"><thead><tr>${section.columns.map(column => `<th>${escapeHtml(column.label)}</th>`).join('')}</tr></thead><tbody>${section.rows.map(row => `<tr>${section.columns.map((column, index) => `<td>${escapeHtml(valueFor(row, column, index))}</td>`).join('')}</tr>`).join('')}</tbody></table>`).join('');
                const documentHtml = `<html><head><meta charset="utf-8"><title>${escapeHtml(config.title || 'OccaServe Report')}</title></head><body><h1>OccaServe</h1><h2>${escapeHtml(config.title || 'Report')}</h2><p>Generated ${escapeHtml(config.generatedAt || new Date().toLocaleString())}</p>${blocks}</body></html>`;
                saveBlob(new Blob(['\ufeff', documentHtml], { type: 'application/msword;charset=utf-8' }), `${fileBase(config)}.doc`);
            }
        } catch (error) {
            if (window.showError) window.showError(error.message);
            else window.alert(error.message);
        } finally {
            button.disabled = false;
            button.textContent = label;
        }
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
        sections.forEach((section, sectionIndex) => {
            const worksheetName = (section.title || 'Report').replace(/[\\/?*:[\]]/g, '').slice(0, 31) || `Report ${sectionIndex + 1}`;
            const worksheet = workbook.addWorksheet(worksheetName);
            worksheet.columns = section.columns.map((column, index) => ({
                header: column.label,
                key: `field${index}`,
                width: Math.min(42, Math.max(14, String(column.label).length + 4, ...section.rows.slice(0, 150).map(row => safeText(valueFor(row, column, index)).length + 2))),
                style: column.type === 'currency' ? { numFmt: '"PHP "#,##0.00' } : column.type === 'number' ? { numFmt: '#,##0.##' } : {}
            }));
            section.rows.forEach(row => worksheet.addRow(Object.fromEntries(section.columns.map((column, index) => [`field${index}`, valueFor(row, column, index)]))));
            worksheet.autoFilter = { from: { row: 1, column: 1 }, to: { row: Math.max(1, worksheet.rowCount), column: Math.max(1, section.columns.length) } };
            const heading = worksheet.getRow(1);
            heading.height = 24;
            heading.font = { bold: true, color: { argb: 'FFFFFFFF' } };
            heading.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF0F172A' } };
            heading.alignment = { vertical: 'middle', wrapText: true };
            worksheet.eachRow((row, rowNumber) => {
                row.eachCell(cell => {
                    cell.border = { bottom: { style: 'thin', color: { argb: 'FFCBD5E1' } } };
                    if (rowNumber > 1 && rowNumber % 2 === 0) cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF1F5F9' } };
                    cell.alignment = { vertical: 'top', wrapText: true };
                });
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
            doc.setTextColor(244, 123, 85);
            if (brandImage) doc.addImage(brandImage, 'PNG', margin, 13, 18, 18);
            doc.text('OCCASERVE', margin + 22, 30);
            doc.setFontSize(19);
            doc.setTextColor(15, 23, 42);
            doc.text(config.title || 'Report', margin, 56);
            doc.setFont('helvetica', 'normal');
            doc.setFontSize(8);
            doc.setTextColor(100, 116, 139);
            doc.text(`Generated ${config.generatedAt || new Date().toLocaleString()}${(config.metadata || []).length ? ` · ${(config.metadata || []).join(' · ')}` : ''}`, margin, 72, { maxWidth: 750 });
            if (section.title) {
                doc.setFontSize(11);
                doc.setTextColor(51, 65, 85);
                doc.text(section.title, margin, 94);
            }
            doc.autoTable({
                startY: section.title ? 104 : 88,
                head: [section.columns.map(column => column.label)],
                body: section.rows.map(row => section.columns.map((column, columnIndex) => safeText(valueFor(row, column, columnIndex)))),
                margin: { left: margin, right: margin, bottom: 30 },
                theme: 'grid',
                styles: { font: 'helvetica', fontSize: 7.5, cellPadding: 5, overflow: 'linebreak', textColor: [30, 41, 59] },
                headStyles: { fillColor: [15, 23, 42], textColor: [255, 255, 255], fontStyle: 'bold' },
                alternateRowStyles: { fillColor: [248, 250, 252] },
                didDrawPage: data => {
                    const pageCount = doc.internal.getNumberOfPages();
                    doc.setFontSize(8);
                    doc.setTextColor(100, 116, 139);
                    doc.text('OccaServe · Confidential report', margin, data.pageSize.height - 16);
                    doc.text(`Page ${data.pageNumber} of ${pageCount}`, data.pageSize.width - margin, data.pageSize.height - 16, { align: 'right' });
                }
            });
        });
        doc.save(`${fileBase(config)}.pdf`);
    }

    function printReport(config, sections) {
        const win = window.open('', '_blank');
        if (!win) throw new Error('Allow pop-ups to print this report.');
        const sectionHtml = sections.map(section => `<section><h2>${escapeHtml(section.title)}</h2><table><thead><tr>${section.columns.map(column => `<th>${escapeHtml(column.label)}</th>`).join('')}</tr></thead><tbody>${section.rows.map(row => `<tr>${section.columns.map((column, index) => `<td>${escapeHtml(valueFor(row, column, index))}</td>`).join('')}</tr>`).join('')}</tbody></table></section>`).join('');
        win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${escapeHtml(config.title || 'OccaServe Report')}</title><style>@page{size:landscape;margin:15mm}body{font:11px/1.5 Arial,sans-serif;color:#0f172a}header{border-bottom:3px solid #f47b55;padding-bottom:12px;margin-bottom:20px}header strong{color:#f47b55}h1{font-size:22px;margin:10px 0 4px}small{color:#64748b}section{margin:20px 0;break-inside:avoid}h2{font-size:14px}table{width:100%;border-collapse:collapse;font-size:9px}th,td{border:1px solid #dbe3ec;padding:6px;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#0f172a;color:white}tr:nth-child(even){background:#f8fafc}footer{position:fixed;bottom:0;color:#64748b;font-size:9px}</style></head><body><header><strong>OCCASERVE</strong><h1>${escapeHtml(config.title || 'Report')}</h1><small>Generated ${escapeHtml(config.generatedAt || new Date().toLocaleString())}${(config.metadata || []).length ? ` · ${escapeHtml((config.metadata || []).join(' · '))}` : ''}</small></header>${sectionHtml}<footer>OccaServe · Confidential report</footer><script>window.onload=()=>window.print()<\/script></body></html>`);
        win.document.close();
    }

    window.OccaExportPreview = { open: createPreview };
}());
