#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Use: $0 <openrc> <tag> <ssh_key>" >&2
  exit 1
fi

OPENRC=$(realpath "$1")
TAG=$2
SSH_KEY=$(realpath "$3")
shift 3                     

export OPENRC TAG SSH_KEY
export ANSIBLE_HOST_KEY_CHECKING=False
export ANSIBLE_SSH_COMMON_ARGS="-F ${TAG}_SSHconfig"

ansible-playbook -i common.py site.yaml "$@"

