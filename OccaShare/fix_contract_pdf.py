import re

filepath = r'c:\OccaServe\OccaShare\templates\shared\contract_content_partial.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the downloadContractPDF function
new_js = """
<script>
    function downloadContractPDF() {
        const originalElement = document.querySelector('.contract-paper');
        const refNo = "{% if booking.document_type == 'invoice' %}ORD-{% else %}BK-{% endif %}{{ booking.id }}";
        
        // Show loading state
        const btn = document.querySelector('.pdf-action-bar button');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating PDF...';
        btn.disabled = true;

        // Temporarily modify the original element for perfect PDF rendering
        const originalWidth = originalElement.style.width;
        const originalMargin = originalElement.style.margin;
        const originalBoxShadow = originalElement.style.boxShadow;
        
        // Force fixed width for A4/Letter size translation
        originalElement.style.width = '800px';
        originalElement.style.margin = '0 auto';
        originalElement.style.boxShadow = 'none';

        const opt = {
            margin:       [0.5, 0.5, 0.5, 0.5], // Top, Left, Bottom, Right
            filename:     `OccaServe_${refNo}_Document.pdf`,
            image:        { type: 'jpeg', quality: 0.98 },
            pagebreak:    { mode: ['css', 'legacy'] }, // Prevents cutting elements in half (use page-break-inside: avoid)
            html2canvas:  { 
                scale: 2, 
                useCORS: true, 
                logging: false,
                letterRendering: true
            },
            jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
        };

        html2pdf().set(opt).from(originalElement).save().then(() => {
            // Restore original styles
            originalElement.style.width = originalWidth;
            originalElement.style.margin = originalMargin;
            originalElement.style.boxShadow = originalBoxShadow;
            
            btn.innerHTML = originalText;
            btn.disabled = false;
        }).catch(err => {
            console.error("PDF Generation Error:", err);
            // Restore original styles
            originalElement.style.width = originalWidth;
            originalElement.style.margin = originalMargin;
            originalElement.style.boxShadow = originalBoxShadow;
            
            btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
            btn.disabled = false;
        });
    }
</script>
"""

# Isolate the script tag and replace it
content = re.sub(r'<script>\s*function downloadContractPDF\(\).*?</script>', new_js, content, flags=re.DOTALL)

# Fix the watermark positioning in CSS to ensure it doesn't overlap or fall off
# In the original file, it has `.verified-seal-watermark { position: absolute; ... }`
# Wait, let's find `.verified-seal-watermark` in the content and update it.
watermark_css = """
    .verified-seal-watermark {
        position: absolute;
        bottom: 40px;
        right: 40px;
        width: 120px;
        height: 120px;
        border: 4px solid rgba(22, 163, 74, 0.2);
        border-radius: 50%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: rgba(22, 163, 74, 0.25);
        transform: rotate(-15deg);
        pointer-events: none;
        z-index: 10;
        padding: 10px;
        text-align: center;
    }
    .verified-seal-watermark i {
        font-size: 2.5rem;
        margin-bottom: 0.25rem;
    }
    .verified-seal-watermark span {
        font-size: 0.75rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 1px;
        line-height: 1.1;
    }
    
    /* Prevent elements from being cut in half during PDF export */
    .formal-doc-header, .contract-section-formal, .signatures-wrapper-formal {
        page-break-inside: avoid;
    }
"""

content = re.sub(
    r'\.verified-seal-watermark \{[^}]+\}.*?\.verified-seal-watermark span \{[^}]+\}', 
    watermark_css, 
    content, 
    flags=re.DOTALL
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated Contract PDF export logic and CSS!")
