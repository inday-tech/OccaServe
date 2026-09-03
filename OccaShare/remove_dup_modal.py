with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

modal_marker = 'id=\"manualBookingModal\" class=\"occ-modal-overlay\"'
first_pos = content.find(modal_marker)
second_pos = content.find(modal_marker, first_pos + 1)

print(f"First modal at position: {first_pos}")
print(f"Second modal at position: {second_pos}")

if second_pos != -1:
    # Find the div tag start (go back to <div)
    div_start = content.rfind('<div', 0, second_pos)
    print(f"Second modal div starts at: {div_start}")
    
    # Count div depth to find the end
    depth = 0
    pos = div_start
    end_pos = -1
    while pos < len(content):
        if content[pos:pos+4] == '<div':
            depth += 1
        elif content[pos:pos+5] == '</div':
            depth -= 1
            if depth == 0:
                end_pos = pos + 6
                break
        pos += 1
    
    print(f"Second modal ends at: {end_pos}")
    
    if end_pos != -1:
        # Remove from div_start to end_pos
        removed_chunk = content[div_start:end_pos]
        print(f"Removing chunk of {len(removed_chunk)} chars")
        content = content[:div_start] + content[end_pos:]
        
        # Verify
        remaining = content.count(modal_marker)
        print(f"Remaining manualBookingModal occurrences: {remaining}")
        
        with open('templates/caterer/calendar.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Saved!")
