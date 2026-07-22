import codecs

def fix_file(file_path):
    with codecs.open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    bad_syntax = "const MIN_QTY = parseInt('{{ item.min_order_qty|default(1) if catalog_type == \\\'menu\\\' else 1 }}') || 1;"
    good_syntax = "const MIN_QTY = parseInt('{{ item.min_order_qty|default(1) if catalog_type == \"menu\" else 1 }}') || 1;"
    
    content = content.replace(bad_syntax, good_syntax)
    
    with codecs.open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

fix_file('c:\\OccaServe\\OccaShare\\templates\\customer\\item_details_page.html')
fix_file('c:\\OccaServe\\OccaShare\\templates\\caterer\\components\\item_details_page.html')
