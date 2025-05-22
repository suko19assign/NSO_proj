from openstack import connection
import os, time

def conn_from_rc(rc_path):
    env={}
    with open(rc_path) as f:
        for line in f:
            if not line.startswith("export"): continue
            k,v=line.split(None,1)[1].split("=",1)
            env[k]=v.strip().strip('"').strip("'")
    return connection.Connection(
        auth_url=env["OS_AUTH_URL"],
        project_name=env["OS_PROJECT_NAME"],
        username=env["OS_USERNAME"],
        password=env["OS_PASSWORD"],
        user_domain_name=env.get("OS_USER_DOMAIN_NAME","Default"),
        project_domain_name=env.get("OS_PROJECT_DOMAIN_NAME","Default"),
        region_name=env.get("OS_REGION_NAME")
    )

def pick_image(conn, pattern="Ubuntu 20.04"):
    imgs=[i for i in conn.compute.images() if pattern in i.name]
    return sorted(imgs, key=lambda i:i.updated_at)[-1]

def wait_active(conn, server, timeout=300):
    for _ in range(timeout//5):
        server=conn.compute.get_server(server.id)
        if server.status=="ACTIVE":
            return server
        time.sleep(5)
    raise TimeoutError(f"{server.name} not ACTIVE")
