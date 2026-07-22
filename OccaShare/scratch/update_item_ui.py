import codecs
import re

file_path = 'c:\\OccaServe\\OccaShare\\templates\\customer\\item_details_page.html'
with codecs.open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Image Size reduction
content = content.replace('grid-template-columns: 360px 1fr 340px;', 'grid-template-columns: 300px 1fr 340px;')
content = content.replace('aspect-ratio: 3/4;', 'aspect-ratio: 1/1;')

# 2. Remove Reviews block
reviews_html = """                <div class="ratings">
                    <div class="stars">
                        <i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star-half-alt"></i>
                    </div>
                    <span>4.8 (25 reviews)</span>
                </div>"""
content = content.replace(reviews_html, '')

# 3. Move Product Details below description
info_regex = re.compile(r'<!-- Info Section \(Real Data Only\) -->.*?<div class="info-content-grid">.*?</div>\s*</div>\s*</div>', re.DOTALL)
match = info_regex.search(content)
if match:
    info_html = match.group(0)
    content = content.replace(info_html, '')
    info_html = info_html.replace('margin-top: 3rem;', 'margin-top: 0.5rem;')
    info_html = info_html.replace('padding: 2rem;', 'padding: 0rem; border: none; background: transparent;')
    info_html = info_html.replace('info-content-grid"', 'info-content-grid" style="gap: 1.5rem;"')
    
    insert_pos = content.find('</p>', content.find('class="short-desc"')) + 4
    content = content[:insert_pos] + '\n' + info_html + content[insert_pos:]

# 4. Make "Need Help?" a link
help_html = """<div class="help-box">
                <i class="fas fa-clipboard-list help-icon"></i>
                <div>
                    <div class="help-text">Need help?</div>
                    <div class="help-sub">Contact the caterer</div>
                </div>
            </div>"""
new_help_html = """<a href="mailto:{{ caterer.user.email if caterer.user else '' }}" class="help-box" style="text-decoration: none; display: flex;">
                <i class="fas fa-envelope help-icon"></i>
                <div>
                    <div class="help-text">Need help?</div>
                    <div class="help-sub">Message caterer directly</div>
                </div>
            </a>"""
content = content.replace(help_html, new_help_html)

# 5. Fix minimum quantity in JS
content = content.replace("let val = parseInt(input.value) || 1;", "let val = parseInt(input.value) || MIN_QTY;")
content = content.replace("if (val < 1) val = 1;", "if (val < MIN_QTY) val = MIN_QTY;")
content = content.replace("document.getElementById('qty-minus').disabled = (val <= 1);", "document.getElementById('qty-minus').disabled = (val <= MIN_QTY);")

js_init = 'const HAS_VARIANTS = '
js_min = "const MIN_QTY = parseInt('{{ item.min_order_qty|default(1) if catalog_type == \\\'menu\\\' else 1 }}') || 1;\n    " + js_init
content = content.replace(js_init, js_min)

content = content.replace('id="item-qty" value="1"', 'id="item-qty" value="{{ item.min_order_qty|default(1) if catalog_type == \'menu\' else 1 }}"')

qty_row = '<span class="qty-label">Quantity</span>'
qty_row_new = '<span class="qty-label" style="display:flex; flex-direction:column;">Quantity <span style="font-size: 0.75rem; color: #f97316;">Min. Order: {{ item.min_order_qty|default(1) if catalog_type == "menu" else 1 }}</span></span>'
content = content.replace(qty_row, qty_row_new)

with codecs.open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
