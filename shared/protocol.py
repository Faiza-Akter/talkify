# shared/protocol.py

import json
from datetime import datetime


def current_timestamp():
    """Return current timestamp as string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_packet(packet_type, sender=None, message="", target=None, room=None, extra=None):
    """
    Create a standard dictionary packet.
    """
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
    """
    Convert packet dictionary to bytes for socket sending.
    Appends newline for easy packet separation.
    """
    return (json.dumps(packet) + "\n").encode("utf-8")


def decode_packets(buffer):
    """
    Split incoming buffer by newline and decode complete JSON packets.
    
    Returns:
        packets (list): list of decoded packet dictionaries
        remaining_buffer (str): incomplete leftover data
    """
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
            # Ignore broken packet for now
            pass

    return packets, remaining_buffer