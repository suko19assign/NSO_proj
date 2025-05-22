from openstack import connection
import os, time, logging

log = logging.getLogger(__name__)

def conn_from_rc(rc_path: str) -> connection.Connection:
    """
    Parse a standard OpenStack openrc file (export KEY=val lines)
    and return an authenticated openstacksdk Connection object.
    """
    env = {}
    with open(rc_path) as fh:
        for line in fh:
            line = line.strip()
            if not line.startswith("export "):
                continue
            key, val = line.split(None, 1)[1].split("=", 1)
            env[key] = val.strip().strip('"').strip("'")

    required = ("OS_AUTH_URL", "OS_USERNAME", "OS_PASSWORD", "OS_PROJECT_NAME")
    missing = [k for k in required if k not in env]
    if missing:
        raise RuntimeError(f"RC file is missing: {', '.join(missing)}")

    return connection.Connection(
        auth_url            = env["OS_AUTH_URL"],
        project_name        = env["OS_PROJECT_NAME"],
        username            = env["OS_USERNAME"],
        password            = env["OS_PASSWORD"],
        user_domain_name    = env.get("OS_USER_DOMAIN_NAME",    "Default"),
        project_domain_name = env.get("OS_PROJECT_DOMAIN_NAME", "Default"),
        region_name         = env.get("OS_REGION_NAME"),       
    )


def pick_image(conn, pattern: str = "Ubuntu 20.04"):
    """Return the newest image whose name contains *pattern*."""
    images = [img for img in conn.compute.images() if pattern in img.name]
    if not images:
        raise RuntimeError(f"No image matching '{pattern}' found")
    return sorted(images, key=lambda i: i.updated_at)[-1]


def wait_active(conn, server, timeout: int = 300):
    """Block until *server* status becomes ACTIVE or timeout."""
    for _ in range(timeout // 5):
        srv = conn.compute.get_server(server.id)
        if srv.status == "ACTIVE":
            return srv
        time.sleep(5)
    raise TimeoutError(f"{server.name} did not reach ACTIVE within {timeout}s")
