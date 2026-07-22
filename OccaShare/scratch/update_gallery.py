import codecs

with codecs.open('c:\\OccaServe\\OccaShare\\templates\\customer\\caterer_profile_view.html', 'r', 'utf-8') as f:
    content = f.read()

gallery_html = '''                ${pkg.desc ? `<p style="font-size:0.85rem;color:var(--hub-slate-600);line-height:1.65;margin-bottom:1.25rem;">${pkg.desc}</p>` : ''}
                ${(pkg.gallery_images && pkg.gallery_images.length > 0) ? `
                <div style="margin-bottom:1.25rem; display:flex; gap:8px; overflow-x:auto; padding-bottom:8px;">
                    ${pkg.gallery_images.map(img => `<img src="${img}" style="width:100px; height:75px; object-fit:cover; border-radius:8px; border:1px solid #e2e8f0; flex-shrink:0;">`).join('')}
                </div>` : ''}'''

content = content.replace(
    '''                ${pkg.desc ? `<p style="font-size:0.85rem;color:var(--hub-slate-600);line-height:1.65;margin-bottom:1.25rem;">${pkg.desc}</p>` : ''}''',
    gallery_html
)

with codecs.open('c:\\OccaServe\\OccaShare\\templates\\customer\\caterer_profile_view.html', 'w', 'utf-8') as f:
    f.write(content)
print('Done!')
