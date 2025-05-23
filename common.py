#!/usr/bin/env python3
"""
common.py  – shared OpenStack helper

Imported by install / operate / cleanup, and usable directly as:

    $ OPENRC=path/to/openrc TAG=mytag SSH_KEY=~/.ssh/id_rsa \
      python common.py

which prints the Ansible expects.
"""
from openstack import connection
import json
import logging
import os
import subprocess
import sys
import time

LOG = logging.getLogger(__name__)

#helper
def conn_from_rc(rc_path):
    """Return an OpenStackSDK Connection using variables in an openrc file."""
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
    """Block until *server* status becomes ACTIVE, or raise TimeoutError."""
    for _ in range(timeout // 5):
        srv = conn.compute.get_server(server.id)
        if srv.status == "ACTIVE":
            return srv
        time.sleep(5)
    raise TimeoutError(f"{server.name} not ACTIVE within {timeout}s")


def choose_flavor(conn, min_vcpu=1, min_ram=0):
    cands = [f for f in conn.compute.flavors()
             if f.vcpus >= min_vcpu and f.ram >= min_ram]
    if not cands:
        raise RuntimeError("No flavor meets vCPU/RAM requirements")
    return sorted(cands, key=lambda f: (f.vcpus, f.ram))[0]


def wait_ssh(host, user="ubuntu", key_path=None, timeout=900, ssh_config=None):
    """
    Return True when SSH to *user@host* succeeds, False after *timeout* seconds.
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

        if subprocess.run(cmd,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0:
            return True
        time.sleep(5)
    LOG.warning("SSH to %s@%s not ready after %ds", user, host, timeout)
    return False

#implementation
def _collect_inventory(conn, tag, key_path):
    """Return dict suitable for Ansible JSON inventory."""
    proxy_hosts, bastion_hosts, node_hosts = [], [], []
    hostvars = {}

    for srv in conn.compute.servers():
        name = srv.name
        if not name.startswith(f"{tag}_"):
            continue

        # Pick floating IP first, else first fixed IP
        chosen_ip = None
        for net in srv.addresses.values():
            for a in net:
                if a.get("OS-EXT-IPS:type") == "floating":
                    chosen_ip = a["addr"]
                    break
            if chosen_ip:
                break
        if not chosen_ip:
            chosen_ip = next(iter(srv.addresses.values()))[0]["addr"]

        hostvars[name] = {
            "ansible_host": chosen_ip,
            "ansible_user": "ubuntu",
            "ansible_ssh_private_key_file": key_path,
        }

        if name.endswith("_proxy"):
            proxy_hosts.append(name)
        elif name.endswith("_bastion"):
            bastion_hosts.append(name)
        else:
            node_hosts.append(name)

    return {
        "_meta": {"hostvars": hostvars},
        "proxy":   {"hosts": proxy_hosts},
        "bastion": {"hosts": bastion_hosts},
        "nodes":   {"hosts": node_hosts},
    }


def inventory_main():
    """Entry-point used by inventory.py or when running common.py directly."""
    rc_path = os.environ.get("OPENRC")
    tag     = os.environ.get("TAG")
    if not rc_path or not tag:
        sys.exit("You must export OPENRC and TAG")

    key_path = os.path.expanduser(os.environ.get("SSH_KEY", "~/.ssh/id_rsa"))
    conn = conn_from_rc(rc_path)
    inventory = _collect_inventory(conn, tag, key_path)
    print(json.dumps(inventory, indent=2))


if __name__ == "__main__":
    inventory_main()
