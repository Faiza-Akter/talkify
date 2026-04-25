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

    typing_received = Signal(dict)
    message_status_received = Signal(dict)
    profile_updated = Signal(dict)

    join_notice_received = Signal(str)
    leave_notice_received = Signal(str)
    room_joined = Signal(str)
    user_list_received = Signal(list)
    room_list_received = Signal(list)

    error_received = Signal(str)
    admin_response_received = Signal(str)
    admin_data_received = Signal(dict)
    disconnected = Signal()

    message_deleted = Signal(dict)

    def __init__(self):
        super().__init__()
        self.socket = None
        self.username = None
        self.buffer = ""
        self.connected = False
        self.latest_users = []
        self.latest_rooms = []
        

    def connect_to_server(self, username, host=HOST, port=PORT):
        try:
            self.username = username
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.connected = True

            self._send_packet(create_packet("login", sender=username))

            threading.Thread(target=self.receive_loop, daemon=True).start()
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
                        self._auto_ack(packet)

                    elif packet_type == "private_message":
                        self.private_message_received.emit(packet)
                        self._auto_ack(packet)

                    elif packet_type == "room_message":
                        self.room_message_received.emit(packet)
                        self._auto_ack(packet)

                    elif packet_type == "typing":
                        self.typing_received.emit(packet)

                    elif packet_type == "message_status":
                        self.message_status_received.emit(packet)

                    elif packet_type == "profile_updated":
                        self.profile_updated.emit(packet)

                    elif packet_type == "join_notice":
                        self.join_notice_received.emit(packet.get("message", ""))

                    elif packet_type == "leave_notice":
                        self.leave_notice_received.emit(packet.get("message", ""))

                    elif packet_type == "room_joined":
                        self.room_joined.emit(packet.get("message", ""))

                    elif packet_type == "delete_message":
                        self.message_deleted.emit(packet)

                    elif packet_type == "user_list":
                        users = packet.get("users", [])

                        normalized_users = []
                        for user in users:
                            if isinstance(user, dict):
                                username = user.get("username", "")
                                if username:
                                    normalized_users.append({
                                        "username": username,
                                        "online": user.get("online", True),
                                        "is_admin": user.get("is_admin", False),
                                        "profile_picture": user.get("profile_picture", "default_avatar.png"),
                                    })
                            elif isinstance(user, str):
                                normalized_users.append({
                                    "username": user,
                                    "online": True,
                                    "is_admin": False,
                                    "profile_picture": "default_avatar.png",
                                })

                        self.latest_users = normalized_users
                        self.user_list_received.emit(normalized_users)

                    elif packet_type == "room_list":
                        rooms = packet.get("rooms", [])
                        self.latest_rooms = rooms
                        self.room_list_received.emit(rooms)

                    elif packet_type == "admin_data":
                        self.admin_data_received.emit(packet)

                    elif packet_type == "admin_response":
                        self.admin_response_received.emit(packet.get("message", ""))

                    elif packet_type == "error":
                        self.error_received.emit(packet.get("message", ""))

        except Exception:
            pass
        finally:
            self.connected = False
            self.disconnected.emit()

    def _auto_ack(self, packet):
        sender = packet.get("sender")
        message_id = packet.get("message_id")
        if sender and message_id and sender != self.username:
            self.ack_message_delivery(message_id)

    def send_public_message(self, message, reply_to=None):
        self._send_packet(create_packet(
            packet_type="public_message",
            sender=self.username,
            message=message,
            extra={"reply_to": reply_to}
        ))

    def send_private_message(self, target, message, reply_to=None):
        self._send_packet(create_packet(
            packet_type="private_message",
            sender=self.username,
            target=target,
            message=message,
            extra={"reply_to": reply_to}
        ))

    def join_room(self, room_name):
        self._send_packet(create_packet(
            packet_type="join_room",
            sender=self.username,
            room=room_name
        ))

    def send_room_message(self, room_name, message, reply_to=None):
        self._send_packet(create_packet(
            packet_type="room_message",
            sender=self.username,
            room=room_name,
            message=message,
            extra={"reply_to": reply_to}
        ))

    def send_typing(self, target_mode, target=None, room=None, is_typing=True):
        self._send_packet(create_packet(
            packet_type="typing",
            sender=self.username,
            target=target,
            room=room,
            extra={
                "target_mode": target_mode,
                "is_typing": is_typing
            }
        ))

    def ack_message_delivery(self, message_id):
        self._send_packet(create_packet(
            packet_type="delivered_ack",
            sender=self.username,
            extra={"message_id": message_id}
        ))

    def update_profile_picture(self, profile_picture):
        self._send_packet(create_packet(
            packet_type="update_profile_picture",
            sender=self.username,
            extra={"profile_picture": profile_picture}
        ))

    def kick_user(self, target):
        self._send_packet(create_packet(
            packet_type="kick",
            sender=self.username,
            target=target
        ))

    def ban_user(self, target, reason="No reason provided"):
        self._send_packet(create_packet(
            packet_type="ban",
            sender=self.username,
            target=target,
            message=reason
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

    def delete_message(self, message_id):
        self._send_packet(create_packet(
            packet_type="delete_message",
            sender=self.username,
            extra={"message_id": message_id}
        ))

    def request_admin_data(self):
        self._send_packet(create_packet(
            packet_type="request_admin_data",
            sender=self.username
        ))