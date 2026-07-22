import pyjsparser

code = """
const item = { name: "abc" };
const x = item.name.replace(/'/g, \\'\\\\\\'\\');
"""

try:
    pyjsparser.parse(code)
    print("Syntax OK")
except Exception as e:
    print("Syntax Error:", e)
