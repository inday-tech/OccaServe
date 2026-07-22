import codecs

with codecs.open('c:\\OccaServe\\OccaShare\\templates\\customer\\caterer_profile_view.html', 'r', 'utf-8') as f:
    content = f.read()

content = content.replace(
    '        gallery_images: pkg.gallery_images ? pkg.gallery_images : [],',
    '        gallery_images: {{ (pkg.gallery_images)|tojson if pkg.gallery_images else "[]" }},'
)

with codecs.open('c:\\OccaServe\\OccaShare\\templates\\customer\\caterer_profile_view.html', 'w', 'utf-8') as f:
    f.write(content)
print('Fixed!')
