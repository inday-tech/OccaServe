import codecs

with codecs.open('c:\\OccaServe\\OccaShare\\templates\\customer\\item_details_page.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the layout
content = content.replace("{% set active_page = 'marketplace' %}\n{% extends \"customer/layout.html\" %}", "{% extends \"landing_base.html\" %}")

# Insert root variables for colors
css_vars = """<style>
    :root {
        --hub-primary: {{ caterer.primary_color if caterer.primary_color else "var(--primary-color, #FF7B54)" }};
        --hub-brand: {{ caterer.accent_color if caterer.accent_color else "var(--primary-color, #e66640)" }};
        --hub-text-dark: #0f172a;
        --hub-slate-50: #f8fafc;
        --hub-slate-100: #f1f5f9;
        --hub-slate-200: #e2e8f0;
        --hub-slate-300: #cbd5e1;
        --hub-slate-400: #94a3b8;
        --hub-slate-500: #64748b;
        --hub-slate-600: #475569;
        --hub-slate-700: #334155;
    }
"""
content = content.replace('<style>', css_vars, 1)

with codecs.open('c:\\OccaServe\\OccaShare\\templates\\caterer\\components\\item_details_page.html', 'w', encoding='utf-8') as f:
    f.write(content)
