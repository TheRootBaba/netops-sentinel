import ipaddress
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "inventory"


class InventoryError(Exception):
    pass


def load_list(filename, key):
    path = INVENTORY / filename
    if not path.is_file():
        raise InventoryError(f"Missing file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError) as exc:
        raise InventoryError(f"Cannot read {path}: {exc}") from exc

    items = data.get(key)
    if not isinstance(items, list):
        raise InventoryError(f"{filename} must contain a '{key}' list")
    return items


def validate_inventory():
    networks = load_list("networks.json", "networks")
    devices = load_list("devices.json", "devices")
    endpoints = load_list("endpoints.json", "endpoints")
    interfaces = load_list("interfaces.json", "interfaces")
    routing = load_list("routing.json", "routers")

    errors = []
    network_by_id = {}
    network_objects = {}

    for item in networks:
        net_id = item.get("id")
        if not net_id or net_id in network_by_id:
            errors.append(f"Missing or duplicate network id: {net_id!r}")
            continue
        network_by_id[net_id] = item
        try:
            network_objects[net_id] = ipaddress.ip_network(
                item["cidr"], strict=True
            )
        except (KeyError, ValueError) as exc:
            errors.append(f"Network {net_id}: invalid CIDR: {exc}")

    device_ids = [d.get("id") for d in devices]
    if len(device_ids) != len(set(device_ids)):
        errors.append("Duplicate device IDs")

    endpoint_ids = set()
    endpoint_ips = set()

    for endpoint in endpoints:
        endpoint_id = endpoint.get("id")
        if not endpoint_id or endpoint_id in endpoint_ids:
            errors.append(f"Missing or duplicate endpoint id: {endpoint_id!r}")
        endpoint_ids.add(endpoint_id)

        try:
            ip = ipaddress.ip_address(endpoint["ip"])
            if not isinstance(ip, ipaddress.IPv4Address):
                raise ValueError("IPv4 address required")

            prefix = int(endpoint["prefix"])
            if not 0 <= prefix <= 32:
                raise ValueError("prefix must be between 0 and 32")

            network_id = endpoint["network_id"]
            net = network_objects[network_id]

            if ip not in net:
                errors.append(f"{endpoint_id}: {ip} is outside {net}")
            if ip in (net.network_address, net.broadcast_address):
                errors.append(f"{endpoint_id}: address is network/broadcast")
            if str(ip) in endpoint_ips:
                errors.append(f"Duplicate endpoint IP: {ip}")
            endpoint_ips.add(str(ip))

            gateway = ipaddress.ip_address(endpoint["gateway"])
            if gateway not in net:
                errors.append(f"{endpoint_id}: gateway {gateway} is outside {net}")
            if gateway == ip:
                errors.append(f"{endpoint_id}: gateway equals endpoint IP")

        except (KeyError, ValueError, TypeError) as exc:
            errors.append(f"{endpoint_id}: invalid endpoint data: {exc}")

    for interface in interfaces:
        interface_id = interface.get("id", "<unknown>")
        try:
            address = ipaddress.ip_interface(interface["ip"])
            net = network_objects[interface["network_id"]]
            if address.ip not in net:
                errors.append(
                    f"{interface_id}: {address.ip} is outside {net}"
                )
            if interface.get("device_id") not in device_ids:
                errors.append(
                    f"{interface_id}: unknown device {interface.get('device_id')!r}"
                )
            peer = interface.get("peer_device_id")
            if peer not in device_ids:
                errors.append(f"{interface_id}: unknown peer {peer!r}")
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(f"{interface_id}: invalid interface data: {exc}")

    network_items = list(network_objects.items())
    for index, (left_id, left) in enumerate(network_items):
        for right_id, right in network_items[index + 1:]:
            if left.overlaps(right):
                errors.append(
                    f"Overlapping networks: {left_id} ({left}) and "
                    f"{right_id} ({right})"
                )

    known_router_ids = {
        d["id"] for d in devices
        if d.get("role") in ("core_router", "branch_router")
    }
    routing_ids = [r.get("device_id") for r in routing]
    if set(routing_ids) != known_router_ids:
        errors.append("Routing inventory must contain each router exactly once")
    if len(routing_ids) != len(set(routing_ids)):
        errors.append("Duplicate router in routing inventory")

    if errors:
        raise InventoryError("\n".join(errors))

    return [
        f"Devices checked: {len(devices)}",
        f"Networks checked: {len(networks)}",
        f"Endpoints checked: {len(endpoints)}",
        f"Interfaces checked: {len(interfaces)}",
        "Routing intent: static only; live routes not yet verified",
        "Inventory validation: PASS"
    ]


def main():
    try:
        print("\n".join(validate_inventory()))
        return 0
    except InventoryError as exc:
        print(f"Inventory validation: FAIL\n{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
