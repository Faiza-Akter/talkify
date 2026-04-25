import socket
import threading

from shared.config import HOST, PORT, BUFFER_SIZE, ENCODING, DEFAULT_ROOM
from shared.protocol import create_packet, encode_packet, decode_packets
from server.room_manager import RoomManager
from server.database import Database
from server.admin_manager import AdminManager
from server.message_store import MessageStore


class ChatServer:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.is_running = False

        self.clients = {}               # username -> socket
        self.client_usernames = {}      # socket -> username
        self.connected_profiles = {}    # username -> profile dict

        self.lock = threading.Lock()
        self.room_manager = RoomManager()
        self.database = Database()
        self.admin_manager = AdminManager(self, self.database)
        self.message_store = MessageStore()

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        self.is_running = True

        print(f"[SERVER STARTED] Listening on {self.host}:{self.port}")

        while self.is_running:
            try:
                client_socket, client_address = self.server_socket.accept()
                print(f"[NEW CONNECTION] {client_address}")

                thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                thread.start()

            except KeyboardInterrupt:
                print("\n[SERVER STOPPED BY USER]")
                self.stop()
                break
            except OSError:
                break
            except Exception as error:
                print(f"[ACCEPT ERROR] {error}")

    def stop(self):
        self.is_running = False
        with self.lock:
            sockets_to_close = list(self.client_usernames.keys())
            self.clients.clear()
            self.client_usernames.clear()
            self.connected_profiles.clear()

        for sock in sockets_to_close:
            try:
                sock.close()
            except Exception:
                pass

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

        print("[SERVER CLOSED]")

    def handle_client(self, client_socket, client_address):
        username = None
        text_buffer = ""

        try:
            while True:
                data = client_socket.recv(BUFFER_SIZE)
                if not data:
                    break

                text_buffer += data.decode(ENCODING)
                packets, text_buffer = decode_packets(text_buffer)

                for packet in packets:
                    packet_type = packet.get("type")

                    if packet_type == "login":
                        if client_socket in self.client_usernames:
                            self.send_error(client_socket, "You are already logged in.")
                            continue

                        requested_username = packet.get("sender", "").strip()
                        if not requested_username:
                            self.send_login_failed(client_socket, "Username cannot be empty.")
                            continue

                        if self.database.is_user_banned(requested_username):
                            self.send_login_failed(client_socket, "You are banned from the server.")
                            continue

                        self.database.ensure_user_exists(requested_username)
                        profile = self.database.get_user_profile(requested_username) or {
                            "username": requested_username,
                            "is_admin": False,
                            "profile_picture": "default_avatar.png"
                        }

                        with self.lock:
                            if requested_username in self.clients:
                                self.send_login_failed(client_socket, "Username already taken.")
                                continue

                            self.clients[requested_username] = client_socket
                            self.client_usernames[client_socket] = requested_username
                            self.connected_profiles[requested_username] = profile

                        username = requested_username
                        self.room_manager.add_user_to_room(username, DEFAULT_ROOM)

                        success_packet = create_packet(
                            packet_type="login_success",
                            sender="server",
                            message=f"Welcome, {username}!",
                            extra={
                                "room": DEFAULT_ROOM,
                                "is_admin": bool(profile.get("is_admin")),
                                "profile_picture": profile.get("profile_picture", "default_avatar.png")
                            }
                        )
                        self.send_packet(client_socket, success_packet)

                        print(f"[LOGIN] {username} joined from {client_address}")

                        self.broadcast(
                            create_packet(
                                packet_type="join_notice",
                                sender="server",
                                message=f"{username} joined the chat."
                            ),
                            exclude_socket=client_socket
                        )

                        self.send_user_list()
                        self.send_room_list()

                    elif packet_type == "public_message":
                        self.handle_public_message(client_socket, packet)

                    elif packet_type == "private_message":
                        self.handle_private_message(client_socket, packet)

                    elif packet_type == "room_message":
                        self.handle_room_message(client_socket, packet)

                    elif packet_type == "join_room":
                        self.handle_join_room(client_socket, packet)

                    elif packet_type == "typing":
                        self.handle_typing(client_socket, packet)

                    elif packet_type == "delivered_ack":
                        self.handle_delivered_ack(client_socket, packet)

                    elif packet_type == "update_profile_picture":
                        self.handle_profile_picture_update(client_socket, packet)

                    elif packet_type == "kick":
                        self.handle_kick(client_socket, packet)

                    elif packet_type == "ban":
                        self.handle_ban(client_socket, packet)
                    
                    elif packet_type == "delete_message":
                        self.handle_delete_message(client_socket, packet)

                    else:
                        self.send_error(client_socket, f"Unknown packet type: {packet_type}")

        except ConnectionResetError:
            print(f"[DISCONNECTED] {client_address} forcibly closed the connection.")
        except Exception as error:
            print(f"[CLIENT ERROR] {client_address}: {error}")
        finally:
            self.remove_client(client_socket)

    def require_login(self, client_socket):
        if client_socket not in self.client_usernames:
            self.send_error(client_socket, "You must log in first.")
            return None
        return self.client_usernames[client_socket]

    def get_profile_picture(self, username):
        profile = self.connected_profiles.get(username, {})
        return profile.get("profile_picture", "default_avatar.png")

    def handle_public_message(self, client_socket, packet):
        username = self.require_login(client_socket)
        if not username:
            return

        content = packet.get("message", "").strip()
        reply_to = packet.get("reply_to")
        if not content:
            return

        message = self.message_store.create_message(
            scope="public",
            sender=username,
            content=content,
            reply_to=reply_to,
            sender_profile_picture=self.get_profile_picture(username)
        )

        message_packet = create_packet(
            packet_type="public_message",
            sender=username,
            message=content,
            extra={
                "message_id": message["message_id"],
                "status": "sent",
                "reply_to": reply_to,
                "sender_profile_picture": message["sender_profile_picture"]
            }
        )

        self.broadcast(message_packet)
        self.send_status_to_sender(username, message["message_id"], "sent", "public")
        print(f"[PUBLIC] {username}: {content}")

    def handle_private_message(self, client_socket, packet):
        username = self.require_login(client_socket)
        if not username:
            return

        target_username = packet.get("target", "").strip()
        content = packet.get("message", "").strip()
        reply_to = packet.get("reply_to")

        if not target_username or not content:
            self.send_error(client_socket, "Private message target and message are required.")
            return

        with self.lock:
            target_socket = self.clients.get(target_username)
            sender_socket = self.clients.get(username)

        if not target_socket:
            self.send_error(sender_socket, f"User '{target_username}' is not online.")
            return

        message = self.message_store.create_message(
            scope="private",
            sender=username,
            target=target_username,
            content=content,
            reply_to=reply_to,
            sender_profile_picture=self.get_profile_picture(username)
        )

        msg_packet = create_packet(
            packet_type="private_message",
            sender=username,
            target=target_username,
            message=content,
            extra={
                "message_id": message["message_id"],
                "status": "sent",
                "reply_to": reply_to,
                "sender_profile_picture": message["sender_profile_picture"]
            }
        )

        self.send_packet(target_socket, msg_packet)
        if sender_socket and sender_socket != target_socket:
            self.send_packet(sender_socket, msg_packet)

        self.send_status_to_sender(username, message["message_id"], "sent", "private", target=target_username)
        print(f"[PRIVATE] {username} -> {target_username}: {content}")

    def handle_room_message(self, client_socket, packet):
        username = self.require_login(client_socket)
        if not username:
            return

        room_name = packet.get("room", "").strip()
        content = packet.get("message", "").strip()
        reply_to = packet.get("reply_to")

        if not room_name or not content:
            self.send_error(client_socket, "Room name and message are required.")
            return

        if not self.room_manager.is_user_in_room(username, room_name):
            self.send_error(client_socket, f"You are not a member of room '{room_name}'.")
            return

        message = self.message_store.create_message(
            scope="room",
            sender=username,
            room=room_name,
            content=content,
            reply_to=reply_to,
            sender_profile_picture=self.get_profile_picture(username)
        )

        room_packet = create_packet(
            packet_type="room_message",
            sender=username,
            room=room_name,
            message=content,
            extra={
                "message_id": message["message_id"],
                "status": "sent",
                "reply_to": reply_to,
                "sender_profile_picture": message["sender_profile_picture"]
            }
        )

        self.broadcast_to_room(room_name, room_packet)
        self.send_status_to_sender(username, message["message_id"], "sent", "room", room=room_name)
        print(f"[ROOM:{room_name}] {username}: {content}")

    def handle_join_room(self, client_socket, packet):
        username = self.require_login(client_socket)
        if not username:
            return

        room_name = packet.get("room", "").strip()
        if not room_name:
            self.send_error(client_socket, "Room name cannot be empty.")
            return

        self.room_manager.add_user_to_room(username, room_name)

        joined_packet = create_packet(
            packet_type="room_joined",
            sender="server",
            room=room_name,
            message=f"{username} joined room '{room_name}'."
        )
        self.send_packet(client_socket, joined_packet)
        self.send_room_list()

    def handle_typing(self, client_socket, packet):
        username = self.require_login(client_socket)
        if not username:
            return

        target_mode = packet.get("target_mode", "public")
        target = packet.get("target")
        room = packet.get("room")
        is_typing = bool(packet.get("is_typing", False))

        typing_packet = create_packet(
            packet_type="typing",
            sender=username,
            target=target,
            room=room,
            extra={
                "target_mode": target_mode,
                "is_typing": is_typing
            }
        )

        if target_mode == "private" and target:
            with self.lock:
                target_socket = self.clients.get(target)
            if target_socket:
                self.send_packet(target_socket, typing_packet)

        elif target_mode == "room" and room:
            self.broadcast_to_room(room, typing_packet, exclude_username=username)

        elif target_mode == "public":
            self.broadcast(typing_packet, exclude_socket=client_socket)

    def handle_delivered_ack(self, client_socket, packet):
        delivered_by = self.require_login(client_socket)
        if not delivered_by:
            return

        message_id = packet.get("message_id", "").strip()
        if not message_id:
            return

        message = self.message_store.mark_delivered(message_id, delivered_by)
        if not message:
            return

        sender_username = message["sender"]
        status_packet = create_packet(
            packet_type="message_status",
            sender="server",
            extra={
                "message_id": message_id,
                "status": "delivered",
                "delivered_to": message["delivered_to"],
                "scope": message["scope"],
                "target": message.get("target"),
                "room": message.get("room")
            }
        )
        self.send_to_username(sender_username, status_packet)

    def handle_profile_picture_update(self, client_socket, packet):
        username = self.require_login(client_socket)
        if not username:
            return

        profile_picture = packet.get("profile_picture", "").strip()
        if not profile_picture:
            self.send_error(client_socket, "Profile picture path cannot be empty.")
            return

        self.database.update_profile_picture(username, profile_picture)
        with self.lock:
            if username in self.connected_profiles:
                self.connected_profiles[username]["profile_picture"] = profile_picture

        update_packet = create_packet(
            packet_type="profile_updated",
            sender="server",
            extra={
                "username": username,
                "profile_picture": profile_picture
            }
        )
        self.broadcast(update_packet)
        self.send_user_list()

    def handle_kick(self, client_socket, packet):
        admin_username = self.require_login(client_socket)
        if not admin_username:
            return
        target_username = packet.get("target", "").strip()
        success, message = self.admin_manager.kick_user(admin_username, target_username)
        self.send_packet(client_socket, create_packet("admin_response", sender="server", message=message, extra={"success": success}))

    def handle_ban(self, client_socket, packet):
        admin_username = self.require_login(client_socket)
        if not admin_username:
            return
        target_username = packet.get("target", "").strip()
        reason = packet.get("message", "").strip() or "No reason provided"
        success, message = self.admin_manager.ban_user(admin_username, target_username, reason)
        self.send_packet(client_socket, create_packet("admin_response", sender="server", message=message, extra={"success": success}))

    def send_login_failed(self, client_socket, message):
        self.send_packet(client_socket, create_packet("login_failed", sender="server", message=message))

    def send_error(self, client_socket, message):
        self.send_packet(client_socket, create_packet("error", sender="server", message=message))

    def send_packet(self, client_socket, packet):
        try:
            client_socket.sendall(encode_packet(packet))
        except Exception:
            pass

    def send_to_username(self, username, packet):
        with self.lock:
            sock = self.clients.get(username)
        if sock:
            self.send_packet(sock, packet)

    def send_status_to_sender(self, username, message_id, status, scope, target=None, room=None):
        packet = create_packet(
            packet_type="message_status",
            sender="server",
            extra={
                "message_id": message_id,
                "status": status,
                "scope": scope,
                "target": target,
                "room": room
            }
        )
        self.send_to_username(username, packet)

    def remove_client(self, client_socket):
        with self.lock:
            username = self.client_usernames.pop(client_socket, None)
            if username in self.clients:
                del self.clients[username]
            if username in self.connected_profiles:
                del self.connected_profiles[username]

        try:
            client_socket.close()
        except Exception:
            pass

        if username:
            self.room_manager.remove_user_from_all_rooms(username)
            self.broadcast(create_packet("leave_notice", sender="server", message=f"{username} left the chat."))
            self.send_user_list()
            self.send_room_list()

    def broadcast(self, packet, exclude_socket=None):
        encoded = encode_packet(packet)
        with self.lock:
            recipients = list(self.clients.values())

        dead_sockets = []
        for sock in recipients:
            if sock == exclude_socket:
                continue
            try:
                sock.sendall(encoded)
            except Exception:
                dead_sockets.append(sock)

        for sock in dead_sockets:
            self.remove_client(sock)

    def broadcast_to_room(self, room_name, packet, exclude_username=None):
        encoded = encode_packet(packet)
        room_users = self.room_manager.get_users_in_room(room_name)
        dead_sockets = []

        with self.lock:
            for username in room_users:
                if exclude_username and username == exclude_username:
                    continue
                sock = self.clients.get(username)
                if not sock:
                    continue
                try:
                    sock.sendall(encoded)
                except Exception:
                    dead_sockets.append(sock)

        for sock in dead_sockets:
            self.remove_client(sock)

    def send_user_list(self):
        with self.lock:
            users = [
                {
                    "username": username,
                    "online": True,
                    "is_admin": bool(profile.get("is_admin")),
                    "profile_picture": profile.get("profile_picture", "default_avatar.png")
                }
                for username, profile in self.connected_profiles.items()
            ]

        self.broadcast(create_packet("user_list", sender="server", extra={"users": users}))

    def send_room_list(self):
        rooms = self.room_manager.get_all_rooms()
        self.broadcast(create_packet("room_list", sender="server", extra={"rooms": rooms}))


    def handle_delete_message(self, client_socket, packet):
        username = self.require_login(client_socket)
        if not username:
            return

        message_id = packet.get("message_id")

        message = self.message_store.get_message(message_id)
        if not message:
            return

        # Only sender can delete
        if message["sender"] != username:
            return

        # Broadcast delete to everyone
        delete_packet = create_packet(
            packet_type="delete_message",
            sender="server",
            extra={"message_id": message_id}
        )

        self.broadcast(delete_packet)