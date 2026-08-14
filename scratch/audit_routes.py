import sys
sys.path.insert(0, '.')
from server.main import app

def print_routes(routes, prefix=""):
    for route in routes:
        if hasattr(route, "methods") and route.methods:
            print(f"{list(route.methods)} {prefix}{route.path}")
        elif hasattr(route, "path"):
            print(f"MOUNT {prefix}{route.path}")
        elif hasattr(route, "original_router"):
            for sub_route in route.original_router.routes:
                sub_methods = getattr(sub_route, "methods", None)
                sub_path = getattr(sub_route, "path", str(sub_route))
                print(f"{list(sub_methods) if sub_methods else 'MOUNT'} {prefix}{sub_path}")
        elif hasattr(route, "routes"):
            print_routes(route.routes, prefix=prefix)
        else:
            print(f"OTHER {route}")

print_routes(app.routes)
