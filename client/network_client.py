import socket
import threading

from PySide6.QtCore import QObject, Signal

from shared.config import HOST, PORT, BUFFER_SIZE, ENCODING
from shared.protocol import create_packet, encode_packet, decode_packets


class NetworkClient(QObject):
    login_success = Signal(dict)
    login_failed = Signal(str)
    public_message_received = Signal(dict)
    private_message_received = Signal(dict)
    room_message_received = Signal(dict)
    join_notice_received = Signal(str)
    leave_notice_received = Signal(str)
    room_joined = Signal(str)
    user_list_received = Signal(list)
    room_list_received = Signal(list)
    error_received = Signal(str)
    admin_response_received = Signal(str)
    disconnected = Signal()

    def __init__(self):
        super().__init__()
        self.socket = None
        self.username = None
        self.buffer = ""
        self.connected = False

    def connect_to_server(self, username, host=HOST, port=PORT):
        try:
            self.username = username
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.connected = True

            login_packet = create_packet(
                packet_type="login",
                sender=username
            )
            self.socket.sendall(encode_packet(login_packet))

            receiver_thread = threading.Thread(
                target=self.receive_loop,
                daemon=True
            )
            receiver_thread.start()

        except Exception as error:
            self.login_failed.emit(f"Connection failed: {error}")

    def receive_loop(self):
        try:
            while self.connected:
                data = self.socket.recv(BUFFER_SIZE)
                if not data:
                    break

                self.buffer += data.decode(ENCODING)
                packets, self.buffer = decode_packets(self.buffer)

                for packet in packets:
                    packet_type = packet.get("type")

                    if packet_type == "login_success":
                        self.login_success.emit(packet)

                    elif packet_type == "login_failed":
                        self.login_failed.emit(packet.get("message", "Login failed."))

                    elif packet_type == "public_message":
                        self.public_message_received.emit(packet)

                    elif packet_type == "private_message":
                        self.private_message_received.emit(packet)

                    elif packet_type == "room_message":
                        self.room_message_received.emit(packet)

                    elif packet_type == "join_notice":
                        self.join_notice_received.emit(packet.get("message", ""))

                    elif packet_type == "leave_notice":
                        self.leave_notice_received.emit(packet.get("message", ""))

                    elif packet_type == "room_joined":
                        self.room_joined.emit(packet.get("message", ""))

                    elif packet_type == "user_list":
                        self.user_list_received.emit(packet.get("users", []))

                    elif packet_type == "room_list":
                        self.room_list_received.emit(packet.get("rooms", []))

                    elif packet_type == "admin_response":
                        self.admin_response_received.emit(packet.get("message", ""))

                    elif packet_type == "error":
                        self.error_received.emit(packet.get("message", ""))

        except Exception:
            pass
        finally:
            self.connected = False
            self.disconnected.emit()

    def send_public_message(self, message):
        self._send_packet(create_packet(
            packet_type="public_message",
            sender=self.username,
            message=message
        ))

    def send_private_message(self, target, message):
        self._send_packet(create_packet(
            packet_type="private_message",
            sender=self.username,
            target=target,
            message=message
        ))

    def join_room(self, room_name):
        self._send_packet(create_packet(
            packet_type="join_room",
            sender=self.username,
            room=room_name
        ))

    def send_room_message(self, room_name, message):
        self._send_packet(create_packet(
            packet_type="room_message",
            sender=self.username,
            room=room_name,
            message=message
        ))

    def kick_user(self, target):
        self._send_packet(create_packet(
            packet_type="kick",
            sender=self.username,
            target=target
        ))

    def ban_user(self, target):
        self._send_packet(create_packet(
            packet_type="ban",
            sender=self.username,
            target=target
        ))

    def disconnect(self):
        self.connected = False
        try:
            if self.socket:
                self.socket.close()
        except Exception:
            pass

    def _send_packet(self, packet):
        try:
            if self.socket and self.connected:
                self.socket.sendall(encode_packet(packet))
        except Exception as error:
            self.error_received.emit(f"Send failed: {error}")