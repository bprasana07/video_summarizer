import requests
try:
    r = requests.get("https://www.youtube.com/watch?v=dQw4w9WgXcQ", timeout=5)
    print(r.status_code)
except Exception as e:
    print(e)