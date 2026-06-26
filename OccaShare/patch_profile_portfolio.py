import re
with open(r'C:\OccaServe\OccaShare\templates\caterer\profile.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''                    {% for item in public_portfolios %}
                    <div class="aspect-square rounded-2xl overflow-hidden bg-white p-1.5 border border-slate-200 transition-all hover:scale-105 hover:shadow-lg cursor-pointer group relative" 
                         onclick="openPublicImage('{{ item.media_url }}')">
                        <div class="w-full h-full rounded-xl overflow-hidden relative">
                            <img src="{{ item.media_url }}" class="w-full h-full object-cover" alt="Gallery Photo">'''

new_code = '''                    {% for item in public_portfolios %}
                    {% set cover_img = (item.images | selectattr('is_cover', 'equalto', True) | first) %}
                    {% set img_url = cover_img.image_url if cover_img else (item.images[0].image_url if item.images else '/static/images/default-portfolio.jpg') %}
                    <div class="aspect-square rounded-2xl overflow-hidden bg-white p-1.5 border border-slate-200 transition-all hover:scale-105 hover:shadow-lg cursor-pointer group relative" 
                         onclick="openPublicImage('{{ img_url }}')">
                        <div class="w-full h-full rounded-xl overflow-hidden relative">
                            <img src="{{ img_url }}" class="w-full h-full object-cover" alt="Gallery Photo">'''

content = content.replace(old_code, new_code)

with open(r'C:\OccaServe\OccaShare\templates\caterer\profile.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done patching profile.html for visual portfolio")
