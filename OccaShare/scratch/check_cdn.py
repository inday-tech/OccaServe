import urllib.request

try:
    url = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.8"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        print("Final URL:", response.geturl())
        content = response.read()[:500]
        print("Content prefix:")
        print(content.decode('utf-8', errors='ignore'))
except Exception as e:
    print("Error:", e)
