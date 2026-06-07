with open('c:\\OccaServe\\OccaShare\\app\\static\\js\\caterer\\layout.js', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("querySelectorAll('.profile-dropdown')", "querySelectorAll('.premium-dropdown, .profile-dropdown')")
content = content.replace("querySelectorAll('.profile-trigger, .header-action-btn')", "querySelectorAll('.profile-trigger, .header-action-btn, .hdr-btn')")

with open('c:\\OccaServe\\OccaShare\\app\\static\\js\\caterer\\layout.js', 'w', encoding='utf-8') as f:
    f.write(content)
