#!/bin/bash

export GOVC_URL='https://blablabla'
export GOVC_USERNAME='usuario@vsphere.local'
export GOVC_PASSWORD='senha'
export GOVC_INSECURE=1

VM_NAME="$1"
ACTION="$2"

if [ -z "$VM_NAME" ] || [ -z "$ACTION" ]; then
  echo "Usage: $0 <vm-name> <on|off|reboot|status>"
  exit 1
fi

case "$ACTION" in
  on)
    govc vm.power -on "$VM_NAME"
    ;;
  off)
    govc vm.power -off "$VM_NAME"
    ;;
  reboot)
    govc vm.power -reset "$VM_NAME"
    ;;
  status)
    govc vm.info -json "$VM_NAME" | jq -r '.virtualMachines[0].runtime.powerState'
    ;;
  *)
    echo "Invalid action"
    exit 2
esac
