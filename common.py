from openstack import connection
import os, time, subprocess, logging
LOG = logging.getLogger(__name__)

# OpenStack helper
def conn_from_rc(rc_path):
    env = {}
    with open(rc_path) as fh:
        for line in fh:
            if line.startswith("export"):
                k, v = line.split(None, 1)[1].split("=", 1)
                env[k] = v.strip().strip('"').strip("'")
    return connection.Connection(
        auth_url=env["OS_AUTH_URL"],
        project_name=env["OS_PROJECT_NAME"],
        username=env["OS_USERNAME"],
        password=env["OS_PASSWORD"],
        user_domain_name=env.get("OS_USER_DOMAIN_NAME", "Default"),
        project_domain_name=env.get("OS_PROJECT_DOMAIN_NAME", "Default"),
        region_name=env.get("OS_REGION_NAME"),
    )

def pick_image(conn, pattern="Ubuntu 20.04"):
    imgs = [i for i in conn.compute.images() if pattern in i.name]
    if not imgs:
        raise RuntimeError(f'No image with "{pattern}" in name')
    return sorted(imgs, key=lambda i: i.updated_at)[-1]

def wait_active(conn, server, timeout=900):
    for _ in range(timeout // 5):
        srv = conn.compute.get_server(server.id)
        if srv.status == "ACTIVE":
            return srv
        time.sleep(5)
    raise TimeoutError(f"{server.name} not ACTIVE within {timeout}s")

def choose_flavor(conn, min_vcpu=1, min_ram=0):
    c = [f for f in conn.compute.flavors() if f.vcpus >= min_vcpu and f.ram >= min_ram]
    if not c:
        raise RuntimeError("No flavor meets vCPU/RAM requirements")
    return sorted(c, key=lambda f: (f.vcpus, f.ram))[0]

#wait_ssh helper
def wait_ssh(host, user="ubuntu", key_path=None, timeout=900, ssh_config=None):
    """
    Wait until SSH to user@host works.

    *ssh_config* – path to an OpenSSH config to use (adds “-F <file>”).
    Returns True on success, False on timeout (no exception).
    """
    key_path = key_path or os.path.expanduser("~/.ssh/id_rsa")
    start = time.time()
    while time.time() - start < timeout:
        cmd = [
            "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=5"
        ]
        if ssh_config:
            cmd += ["-F", ssh_config]
        cmd += ["-i", key_path, f"{user}@{host}", "true"]

        if subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            return True
        time.sleep(5)
    LOG.warning("SSH to %s@%s not ready after %ds", user, host, timeout)
    return False
