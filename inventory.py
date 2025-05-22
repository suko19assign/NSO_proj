#!/usr/bin/env python3
import json, os, common
conn=common.conn_from_rc(os.environ['OPENRC'])
tag = os.environ['TAG']
inv={"proxy":{"hosts":{}},
     "bastion":{"hosts":{}},
     "nodes":{"hosts":{}}}
for s in conn.compute.servers(details=False):
    if not s.name.startswith(f"{tag}_"): continue
    if s.name.endswith("_proxy"):
        inv["proxy"]["hosts"][s.name]={"ansible_host":s.access_ipv4}
    elif s.name.endswith("_bastion"):
        inv["bastion"]["hosts"][s.name]={"ansible_host":s.access_ipv4}
    else:
        inv["nodes"]["hosts"][s.name]={"ansible_host":s.access_ipv4}
print(json.dumps({"all":{"children":inv}}))
