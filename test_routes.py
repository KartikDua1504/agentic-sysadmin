import sys
try:
    from server.app import app
    print("Routes:")
    for route in app.routes:
        print(getattr(route, 'path', route.name), getattr(route, 'methods', None))
except Exception as e:
    print("Error:", e)
