from flask import Flask, jsonify, request, Response
from functools import wraps
import datetime
import subprocess

app = Flask(__name__)

USERNAME = "admin"
PASSWORD = "123987"

SYSTEMS = {
    "ocp-ztp-01": {"Name": "ocp-ztp-01", "MemoryGB": 16, "CPUs": 4, "Serial": "LABNODE-001"},
    "ocp-ztp-02": {"Name": "ocp-ztp-02", "MemoryGB": 16, "CPUs": 4, "Serial": "LABNODE-002"},
    "ocp-ztp-03": {"Name": "ocp-ztp-03", "MemoryGB": 16, "CPUs": 4, "Serial": "LABNODE-003"},
    "ocp-ztp-04": {"Name": "ocp-ztp-04", "MemoryGB": 8, "CPUs": 4, "Serial": "LABNODE-004"},
}

VIRTUAL_MEDIA = {"Image": None, "Inserted": False}


# =========================
# VMware Integration
# =========================

def vmware_power(vm_name, action):
    try:
        result = subprocess.run(
            ["/usr/local/bin/vmware-power.sh", vm_name, action],
            capture_output=True,
            text=True,
            timeout=30
        )
        print(f"[VMWARE] {vm_name} {action} rc={result.returncode}")
        print(result.stdout)
        print(result.stderr)
    except Exception as e:
        print(f"[VMWARE ERROR] {e}")


def get_power_state(vm_name):
    try:
        result = subprocess.run(
            ["/usr/local/bin/vmware-power.sh", vm_name, "status"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if "poweredOn" in result.stdout or "on" in result.stdout.lower():
            return "On"
        return "Off"
    except Exception as e:
        print(f"[VMWARE STATUS ERROR] {e}")
        return "Off"


# =========================
# AUTH
# =========================

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response("Auth required", 401, {"WWW-Authenticate": 'Basic realm="Redfish"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

def log_request():
    print(f"[{datetime.datetime.now()}] {request.method} {request.path}")


# =========================
# SERVICE ROOT (NO AUTH)
# =========================

@app.route("/redfish/v1/", methods=["GET"])
def service_root():
    log_request()
    return jsonify({
        "@odata.type": "#ServiceRoot.v1_11_0.ServiceRoot",
        "Id": "RootService",
        "Name": "Mock Redfish Service",
        "RedfishVersion": "1.11.0",
        "Systems": {"@odata.id": "/redfish/v1/Systems"}
    })


# =========================
# SYSTEMS
# =========================

@app.route("/redfish/v1/Systems", methods=["GET"])
@requires_auth
def systems_collection():
    log_request()
    members = [{"@odata.id": f"/redfish/v1/Systems/{sid}"} for sid in SYSTEMS]
    return jsonify({"Members@odata.count": len(members), "Members": members})


@app.route("/redfish/v1/Systems/<system_id>", methods=["GET", "PATCH"])
@requires_auth
def system(system_id):
    log_request()
    sys = SYSTEMS.get(system_id)
    if not sys:
        return jsonify({"error": "System not found"}), 404

    # Handle Boot override (PATCH)
    if request.method == "PATCH":
        data = request.json
        boot = data.get("Boot", {})
        print(f"🔧 Boot override for {system_id}: {boot}")
        return jsonify({"result": "Boot updated"}), 200

    return jsonify({
        "@odata.type": "#ComputerSystem.v1_17_0.ComputerSystem",
        "Id": system_id,
        "Name": sys["Name"],
        "SystemType": "Physical",
        "PowerState": get_power_state(system_id),
        "SerialNumber": sys["Serial"],
        "Boot": {
            "BootSourceOverrideEnabled": "Disabled",
            "BootSourceOverrideTarget": "None",
            "BootSourceOverrideMode": "UEFI",
            "BootSourceOverrideTarget@Redfish.AllowableValues": ["None", "Pxe", "Cd", "Hdd"]
        },
        "ProcessorSummary": {"Count": sys["CPUs"], "Model": "Intel Xeon"},
        "MemorySummary": {"TotalSystemMemoryGiB": sys["MemoryGB"]},
        "Links": {"ManagedBy": [{"@odata.id": "/redfish/v1/Managers/BMC1"}]},
        "Actions": {
            "#ComputerSystem.Reset": {
                "target": f"/redfish/v1/Systems/{system_id}/Actions/ComputerSystem.Reset",
                "ResetType@Redfish.AllowableValues": ["On", "ForceOff", "GracefulShutdown", "ForceRestart"]
            }
        }
    })


# =========================
# POWER CONTROL
# =========================

@app.route("/redfish/v1/Systems/<system_id>/Actions/ComputerSystem.Reset", methods=["POST"])
@requires_auth
def reset_system(system_id):
    log_request()
    data = request.json
    reset_type = data.get("ResetType")

    if reset_type in ["On", "ForceRestart"]:
        vmware_power(system_id, "on")
    elif reset_type in ["ForceOff", "GracefulShutdown"]:
        vmware_power(system_id, "off")

    print(f"⚡ {system_id} → requested {reset_type}")
    return jsonify({"result": "OK"})


# =========================
# MANAGER + VIRTUAL MEDIA
# =========================

@app.route("/redfish/v1/Managers", methods=["GET"])
@requires_auth
def managers_collection():
    log_request()
    return jsonify({
        "Members@odata.count": 1,
        "Members": [{"@odata.id": "/redfish/v1/Managers/BMC1"}]
    })


@app.route("/redfish/v1/Managers/BMC1", methods=["GET"])
@requires_auth
def manager():
    log_request()
    return jsonify({
        "@odata.type": "#Manager.v1_10_0.Manager",
        "Id": "BMC1",
        "Name": "Mock BMC Manager",
        "ManagerType": "BMC",
        "FirmwareVersion": "1.00",
        "Status": {"State": "Enabled", "Health": "OK"},
        "Links": {
            "ManagerForServers": [{"@odata.id": f"/redfish/v1/Systems/{sid}"} for sid in SYSTEMS]
        },
        "VirtualMedia": {"@odata.id": "/redfish/v1/Managers/BMC1/VirtualMedia"}
    })


@app.route("/redfish/v1/Managers/BMC1/VirtualMedia", methods=["GET"])
@requires_auth
def virtual_media_collection():
    log_request()
    return jsonify({
        "Members@odata.count": 1,
        "Members": [{"@odata.id": "/redfish/v1/Managers/BMC1/VirtualMedia/CD1"}]
    })


@app.route("/redfish/v1/Managers/BMC1/VirtualMedia/CD1", methods=["GET"])
@requires_auth
def virtual_cd():
    log_request()
    return jsonify({
        "@odata.type": "#VirtualMedia.v1_3_0.VirtualMedia",
        "Id": "CD1",
        "Name": "Virtual CD",
        "MediaTypes": ["CD", "DVD"],
        "Image": VIRTUAL_MEDIA["Image"],
        "Inserted": VIRTUAL_MEDIA["Inserted"],
        "ConnectedVia": "URI",
        "WriteProtected": True,
        "Actions": {
            "#VirtualMedia.InsertMedia": {"target": "/redfish/v1/Managers/BMC1/VirtualMedia/CD1/Actions/VirtualMedia.InsertMedia"},
            "#VirtualMedia.EjectMedia": {"target": "/redfish/v1/Managers/BMC1/VirtualMedia/CD1/Actions/VirtualMedia.EjectMedia"}
        }
    })


@app.route("/redfish/v1/Managers/BMC1/VirtualMedia/CD1/Actions/VirtualMedia.InsertMedia", methods=["POST"])
@requires_auth
def insert_media():
    log_request()
    VIRTUAL_MEDIA["Image"] = request.json.get("Image")
    VIRTUAL_MEDIA["Inserted"] = True
    print(f"📀 ISO inserida: {VIRTUAL_MEDIA['Image']}")
    return jsonify({"result": "Media inserted"})


@app.route("/redfish/v1/Managers/BMC1/VirtualMedia/CD1/Actions/VirtualMedia.EjectMedia", methods=["POST"])
@requires_auth
def eject_media():
    log_request()
    VIRTUAL_MEDIA["Image"] = None
    VIRTUAL_MEDIA["Inserted"] = False
    print("⏏️ ISO ejetada")
    return jsonify({"result": "Media ejected"})


# =========================
# RUN
# =========================

if __name__ == "__main__":
    print("🚀 Mock Redfish server com integração VMware rodando na porta 8000")
    app.run(host="0.0.0.0", port=8000)
