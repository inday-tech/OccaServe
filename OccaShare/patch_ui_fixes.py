import re
with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix the layout by moving the closing div of hub-tab-menu
# Current:
# </div>
# </div>
#                 
#                 <!-- RENTALS & SERVICES -->
old_divs = '''                    {% else %}
                    <p style="color: var(--hub-slate-400); font-size: 0.9rem;">No dishes available yet.</p>
                    {% endif %}
                </div>
                </div>
                
                <!-- RENTALS & SERVICES -->'''

new_divs = '''                    {% else %}
                    <p style="color: var(--hub-slate-400); font-size: 0.9rem;">No dishes available yet.</p>
                    {% endif %}
                </div>
                
                <!-- RENTALS & SERVICES -->'''

content = content.replace(old_divs, new_divs)

# Now close hub-tab-menu after Rentals & Services
old_end = '''                    {% else %}
                    <p style="color: var(--hub-slate-400); font-size: 0.9rem;">No rentals or services available yet.</p>
                    {% endif %}
                </div>
            </div>

            <!-- PORTFOLIO TAB -->'''

new_end = '''                    {% else %}
                    <p style="color: var(--hub-slate-400); font-size: 0.9rem;">No rentals or services available yet.</p>
                    {% endif %}
                </div>
            </div> <!-- Closes hub-tab-menu -->

            <!-- PORTFOLIO TAB -->'''
            
content = content.replace(old_end, new_end)


# 2. Fix ui-avatars to use nice food images for Food
content = content.replace(
    '''{% set final_img = 'https://ui-avatars.com/api/?name=' ~ (cat|urlencode) ~ '&background=f1f5f9&color=64748b&size=400&font-size=0.2' %}''',
    '''{% set final_img = 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=400' %}'''
)

# 3. Simple English changes
content = content.replace('Business Story', 'About Us')
content = content.replace('Active Dishes', 'Food Options')
content = content.replace('Rentals & Services', 'Event Rentals & Services')
content = content.replace('Catering Packages', 'Ready-to-Book Packages')
content = content.replace('Event Highlights', 'Recent Events')
content = content.replace('A La Carte Menu', 'Food Menu')
content = content.replace('Operational Policies', 'Booking Rules')

with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
