import re

filepath = r'c:\OccaServe\OccaShare\templates\shared\contract_content_partial.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_js = """
<script>
    function downloadContractPDF() {
        const paper = document.querySelector('.contract-paper');
        const refNo = "{% if booking.document_type == 'invoice' %}ORD-{% else %}BK-{% endif %}{{ booking.id }}";
        
        const btn = document.querySelector('.pdf-action-bar button');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating PDF...';
        btn.disabled = true;

        // 1. Gather all active stylesheets (Tailwind, Fonts, FontAwesome, Custom CSS)
        // This ensures the typography and boxes look exactly as professional as the system.
        let styles = '';
        document.querySelectorAll('style, link[rel="stylesheet"]').forEach(el => {
            styles += el.outerHTML;
        });

        // 2. Build a completely ISOLATED html string.
        // By doing this, we completely bypass the Sidebar, the Scrollbars, and the Centering bugs
        // that cause the left-side to get cut off. It renders from a pure, invisible (0,0) iframe!
        const pureHtml = `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                ${styles}
                <style>
                    /* Force html2pdf to respect the exact A4 layout with 0.5 inch margins */
                    body, html { 
                        margin: 0 !important; 
                        padding: 0 !important; 
                        background: #fff !important; 
                    }
                    .pdf-export-wrapper {
                        width: 816px !important; 
                        padding: 48px !important; 
                        background: #fff !important; 
                        box-sizing: border-box !important;
                        margin: 0 !important;
                    }
                    /* Override print media queries that might wipe out padding */
                    @media print {
                        .pdf-export-wrapper { padding: 48px !important; }
                    }
                    .contract-paper {
                        width: 100% !important;
                        max-width: 100% !important;
                        padding: 0 !important;
                        box-shadow: none !important;
                        margin: 0 !important;
                        border: none !important;
                    }
                    /* Convert CSS Grid to Flexbox for bulletproof html2canvas compatibility */
                    /* html2canvas sometimes struggles with grid columns, causing broken boxes */
                    .contract-parties-layout { 
                        display: flex !important; 
                        justify-content: space-between !important; 
                        gap: 2rem !important; 
                    }
                    .party-card-pro { 
                        flex: 1 !important; 
                        width: 45% !important; 
                    }
                </style>
            </head>
            <body>
                <div class="pdf-export-wrapper">
                    <div class="contract-paper">
                        ${paper.innerHTML}
                    </div>
                </div>
            </body>
            </html>
        `;

        const opt = {
            margin:       0, // Handled internally by the 48px padding
            filename:     `OccaServe_${refNo}_Document.pdf`,
            image:        { type: 'jpeg', quality: 1 },
            pagebreak:    { mode: ['css', 'legacy'] },
            html2canvas:  { 
                scale: 2, 
                useCORS: true, 
                logging: false,
                letterRendering: true
            },
            jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
        };

        // html2pdf will create a hidden iframe, inject the HTML string, wait for fonts, and screenshot it.
        html2pdf().set(opt).from(pureHtml).save().then(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }).catch(err => {
            console.error("PDF Generation Error:", err);
            btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
            btn.disabled = false;
        });
    }
</script>
"""

content = re.sub(r'<script>\s*function downloadContractPDF\(\).*?</script>', new_js, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied Isolated HTML String Export Fix!")
