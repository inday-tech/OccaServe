import re

path = 'templates/maintenance.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update body CSS
old_body = """        body {
            font-family: 'Poppins', sans-serif;
            /* Vibrant Orange Shade Background */
            background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 50%, #fed7aa 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            color: var(--navy);
        }"""
new_body = """        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 50%, #fed7aa 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow-x: hidden;
            overflow-y: auto;
            color: var(--navy);
            padding: 2rem 1rem;
        }"""
content = content.replace(old_body, new_body)

# 2. Add media queries before </style>
media_queries = """
        @media (max-width: 768px) {
            .maintenance-card {
                padding: 2.5rem 1.5rem;
                width: 100%;
                border-radius: 32px;
            }
            .logo-container {
                width: 100px;
                height: 100px;
                padding: 15px;
                margin-bottom: 2rem;
            }
            h1 {
                font-size: 2rem;
            }
            p {
                font-size: 0.95rem;
                margin-bottom: 2rem;
            }
            .status-badge {
                font-size: 0.7rem;
                padding: 6px 16px;
            }
        }
        @media (max-height: 700px) {
            body {
                align-items: flex-start;
            }
        }
"""
content = content.replace('    </style>', media_queries + '    </style>')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Maintenance UI patched!")
