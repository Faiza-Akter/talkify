import json
from datetime import datetime


def current_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_packet(packet_type, sender=None, message="", target=None, room=None, extra=None):
    packet = {
        "type": packet_type,
        "sender": sender,
        "target": target,
        "room": room,
        "message": message,
        "timestamp": current_timestamp()
    }
    if extra and isinstance(extra, dict):
        packet.update(extra)
    return packet


def encode_packet(packet):
    return (json.dumps(packet) + "\n").encode("utf-8")


def decode_packets(buffer):
    lines = buffer.split("\n")
    complete_lines = lines[:-1]
    remaining_buffer = lines[-1]

    packets = []
    for line in complete_lines:
        line = line.strip()
        if not line:
            continue
        try:
            packets.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    return packets, remaining_buffer
