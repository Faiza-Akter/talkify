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

        self.clients = {}
        self.client_usernames = {}
        self.connected_profiles = {}

        self.lock = threading.Lock()
        self.room_manager = RoomManager()
        self.database = Database()
        self.admin_manager = AdminManager(self, self.database)
        self.message_store = MessageStore()

        # Runtime moderation restrictions.
        # A public kick blocks only Public Chat.
        # A room kick blocks only that room.
        self.public_restricted_users = set()
        self.room_restricted_users = {}

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
                    daemon=True,
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
                        self.handle_login(client_socket, client_address, packet)

                    elif packet_type == "public_message":
                        self.handle_public_message(client_socket, packet)

                    elif packet_type == "private_message":
                        self.handle_private_message(client_socket, packet)

                    elif packet_type == "room_message":
                        self.handle_room_message(client_socket, packet)

                    elif packet_type == "join_room":
                        self.handle_join_room(client_socket, packet)

                    elif packet_type == "create_room":
                        self.handle_create_room(client_socket, packet)

                    elif packet_type == "message_reaction":
                        self.handle_message_reaction(client_socket, packet)

                    elif packet_type == "typing":
                        self.handle_typing(client_socket, packet)

                    elif packet_type == "delivered_ack":
                        self.handle_delivered_ack(client_socket, packet)

                    elif packet_type == "update_profile_picture":
                        self.handle_profile_picture_update(client_socket, packet)

                    elif packet_type == "update_profile":
                        self.handle_profile_update(client_socket, packet)

                    elif packet_type == "kick":
                        self.handle_kick(client_socket, packet)

                    elif packet_type == "ban":
                        self.handle_ban(client_socket, packet)

                    elif packet_type == "delete_message":
                        self.handle_delete_message(client_socket, packet)

                    elif packet_type == "request_admin_data":
                        self.handle_request_admin_data(client_socket, packet)

                    else:
                        self.send_error(client_socket, f"Unknown packet type: {packet_type}")

        except ConnectionResetError:
            print(f"[DISCONNECTED] {client_address} forcibly closed the connection.")
        except Exception as error:
            print(f"[CLIENT ERROR] {client_address}: {error}")
        finally:
            self.remove_client(client_socket)

    def handle_login(self, client_socket, client_address, packet):
        if client_socket in self.client_usernames:
            self.send_error(client_socket, "You are already logged in.")
            return

        requested_username = packet.get("sender", "").strip()
        if not requested_username:
            self.send_login_failed(client_socket, "Username cannot be empty.")
            return

        try:
            if self.database.is_user_banned(requested_username):
                self.send_login_failed(client_socket, "You are banned from the server.")
                return

            self.database.ensure_user_exists(requested_username)
            profile = self.database.get_user_profile(requested_username) or {
                "username": requested_username,
                "is_admin": False,
                "profile_picture": "default_avatar.png",
            }

        except Exception as error:
            self.send_login_failed(client_socket, f"Database error: {error}")
            return

        with self.lock:
            if requested_username in self.clients:
                self.send_login_failed(client_socket, "Username already taken.")
                return

            self.clients[requested_username] = client_socket
            self.client_usernames[client_socket] = requested_username
            self.connected_profiles[requested_username] = profile

        self.room_manager.add_user_to_room(requested_username, DEFAULT_ROOM)

        success_packet = create_packet(
            packet_type="login_success",
            sender="server",
            message=f"Welcome, {requested_username}!",
            extra={
                "room": DEFAULT_ROOM,
                "is_admin": bool(profile.get("is_admin")),
                "profile_picture": profile.get("profile_picture", "default_avatar.png"),
            },
        )
        self.send_packet(client_socket, success_packet)

        print(f"[LOGIN] {requested_username} joined from {client_address}")

        self.broadcast(
            create_packet(
                packet_type="join_notice",
                sender="server",
                message=f"{requested_username} joined the chat.",
            ),
            exclude_socket=client_socket,
        )

        self.send_user_list()
        self.send_room_list()
        self.send_admin_data_to_admins()

    def require_login(self, client_socket):
        if client_socket not in self.client_usernames:
            self.send_error(client_socket, "You must log in first.")
            return None
        return self.client_usernames[client_socket]

    def is_connected_admin(self, username):
        profile = self.connected_profiles.get(username, {})
        return bool(profile.get("is_admin"))

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

        if username in self.public_restricted_users:
            self._send_public_restriction(username)
            return

        message = self.message_store.create_message(
            scope="public",
            sender=username,
            content=content,
            reply_to=reply_to,
            sender_profile_picture=self.get_profile_picture(username),
        )

        message_packet = create_packet(
            packet_type="public_message",
            sender=username,
            message=content,
            extra={
                "message_id": message["message_id"],
                "status": "sent",
                "reply_to": reply_to,
                "sender_profile_picture": message["sender_profile_picture"],
                "reactions": message.get("reactions", {}),
            },
        )

        self.broadcast(message_packet)
        self.send_status_to_sender(username, message["message_id"], "sent", "public")
        print(f"[PUBLIC] {username}: {content}")
        self.send_admin_data_to_admins()

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
            sender_profile_picture=self.get_profile_picture(username),
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
                "sender_profile_picture": message["sender_profile_picture"],
                "reactions": message.get("reactions", {}),
            },
        )

        self.send_packet(target_socket, msg_packet)
        if sender_socket and sender_socket != target_socket:
            self.send_packet(sender_socket, msg_packet)

        self.send_status_to_sender(
            username,
            message["message_id"],
            "sent",
            "private",
            target=target_username,
        )
        print(f"[PRIVATE] {username} -> {target_username}: {content}")
        self.send_admin_data_to_admins()

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

        if self._is_room_restricted(username, room_name):
            self._send_room_restriction(username, room_name)
            return

        if not self.room_manager.is_user_in_room(username, room_name):
            self._send_room_restriction(username, room_name)
            return

        message = self.message_store.create_message(
            scope="room",
            sender=username,
            room=room_name,
            content=content,
            reply_to=reply_to,
            sender_profile_picture=self.get_profile_picture(username),
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
                "sender_profile_picture": message["sender_profile_picture"],
                "reactions": message.get("reactions", {}),
            },
        )

        self.broadcast_to_room(room_name, room_packet)
        self.send_status_to_sender(
            username,
            message["message_id"],
            "sent",
            "room",
            room=room_name,
        )
        print(f"[ROOM:{room_name}] {username}: {content}")
        self.send_admin_data_to_admins()

    def handle_create_room(self, client_socket, packet):
        username = self.require_login(client_socket)
        if not username:
            return

        room_name = packet.get("room", "").strip()
        password = packet.get("password", "")
        members = packet.get("members", [])

        if not room_name:
            self.send_error(client_socket, "Room name cannot be empty.")
            return

        self.room_manager.create_room(room_name, username, password=password, members=members)

        joined_packet = create_packet(
            packet_type="room_joined",
            sender="server",
            room=room_name,
            message=f"Room '{room_name}' was created.",
        )
        self.send_packet(client_socket, joined_packet)
        self.send_room_list()
        self.send_admin_data_to_admins()

    def handle_join_room(self, client_socket, packet):
        username = self.require_login(client_socket)
        if not username:
            return

        room_name = packet.get("room", "").strip()
        password = packet.get("password", "")
        if not room_name:
            self.send_error(client_socket, "Room name cannot be empty.")
            return

        if self._is_room_restricted(username, room_name):
            self._send_room_restriction(username, room_name)
            return

        if not self.room_manager.can_join_room(room_name, password):
            self.send_error(client_socket, "Wrong room password.")
            return

        self.room_manager.add_user_to_room(username, room_name)

        joined_packet = create_packet(
            packet_type="room_joined",
            sender="server",
            room=room_name,
            message=f"{username} joined room '{room_name}'.",
        )
        self.send_packet(client_socket, joined_packet)
        self.send_room_list()
        self.send_admin_data_to_admins()

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
                "is_typing": is_typing,
            },
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
                "room": message.get("room"),
            },
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

        try:
            self.database.update_profile_picture(username, profile_picture)
        except Exception:
            pass

        with self.lock:
            if username in self.connected_profiles:
                self.connected_profiles[username]["profile_picture"] = profile_picture

        update_packet = create_packet(
            packet_type="profile_updated",
            sender="server",
            extra={
                "username": username,
                "profile_picture": profile_picture,
            },
        )
        self.broadcast(update_packet)
        self.send_user_list()

    def handle_profile_update(self, client_socket, packet):
        username = self.require_login(client_socket)
        if not username:
            return

        display_name = packet.get("display_name", "").strip().rstrip("\\")
        profile_picture = packet.get("profile_picture", "").strip()

        if not display_name:
            self.send_error(client_socket, "Display name cannot be empty.")
            return

        with self.lock:
            if username in self.connected_profiles:
                self.connected_profiles[username]["display_name"] = display_name

                if profile_picture:
                    self.connected_profiles[username]["profile_picture"] = profile_picture

        update_packet = create_packet(
            packet_type="profile_updated",
            sender="server",
            extra={
                "username": username,
                "display_name": display_name,
                "profile_picture": profile_picture,
            },
        )

        self.broadcast(update_packet)
        self.send_user_list()
        self.send_room_list()

    def handle_kick(self, client_socket, packet):
        admin_username = self.require_login(client_socket)
        if not admin_username:
            return

        target_username = packet.get("target", "").strip()
        target_mode = (packet.get("target_mode") or "public").strip()
        room_name = (packet.get("room") or "").strip()

        success, message = self.admin_manager.kick_user(admin_username, target_username)

        if success:
            self._apply_kick_restriction(admin_username, target_username, target_mode, room_name)

        self.send_packet(
            client_socket,
            create_packet(
                "admin_response",
                sender="server",
                message=message,
                extra={"success": success},
            ),
        )
        self.send_user_list()
        self.send_room_list()
        self.send_admin_data_to_admins()

    def handle_ban(self, client_socket, packet):
        admin_username = self.require_login(client_socket)
        if not admin_username:
            return

        target_username = packet.get("target", "").strip()
        target_mode = (packet.get("target_mode") or "public").strip()
        room_name = (packet.get("room") or "").strip()
        reason = packet.get("message", "").strip() or "No reason provided"

        success, message = self.admin_manager.ban_user(admin_username, target_username, reason)

        if success:
            self._apply_ban_restriction(admin_username, target_username, target_mode, room_name, reason)

        self.send_packet(
            client_socket,
            create_packet(
                "admin_response",
                sender="server",
                message=message,
                extra={"success": success},
            ),
        )
        self.send_user_list()
        self.send_room_list()
        self.send_admin_data_to_admins()

    def _is_room_restricted(self, username, room_name):
        return username in self.room_restricted_users.get(room_name.lower(), set())

    def _send_public_restriction(self, username):
        self.send_to_username(
            username,
            create_packet(
                packet_type="moderation_restriction",
                sender="Admin",
                target=username,
                message="You have been kicked from Public Chat and cannot send messages there anymore.",
                extra={
                    "target_mode": "public",
                    "action": "kicked",
                    "dialog_message": "You have been kicked from Public Chat and cannot send messages there anymore.",
                },
            ),
        )

    def _send_room_restriction(self, username, room_name):
        self.send_to_username(
            username,
            create_packet(
                packet_type="moderation_restriction",
                sender="Admin",
                target=username,
                room=room_name,
                message=f"You have been kicked from {room_name} and cannot send messages there anymore.",
                extra={
                    "target_mode": "room",
                    "action": "kicked",
                    "dialog_message": f"You have been kicked from {room_name} and cannot send messages there anymore.",
                },
            ),
        )

    def _disconnect_username_after_notice(self, username, delay=0.6):
        """Disconnect a user after queued moderation packets have time to arrive."""
        with self.lock:
            target_socket = self.clients.get(username)

        if not target_socket:
            return

        try:
            timer = threading.Timer(delay, lambda: self.remove_client(target_socket))
            timer.daemon = True
            timer.start()
        except Exception:
            self.remove_client(target_socket)

    def _apply_kick_restriction(self, admin_username, target_username, target_mode, room_name):
        if target_mode == "room" and room_name:
            self.room_manager.remove_user_from_room(target_username, room_name)
            self.room_restricted_users.setdefault(room_name.lower(), set()).add(target_username)

            notice_text = f"Admin kicked {target_username} from {room_name}."
            target_text = f"You have been kicked from {room_name} and cannot send messages there anymore."

            notice_packet = create_packet(
                packet_type="moderation_notice",
                sender="Admin",
                target=target_username,
                room=room_name,
                message=notice_text,
                extra={"target_mode": "room", "action": "kicked"},
            )
            restriction_packet = create_packet(
                packet_type="moderation_restriction",
                sender="Admin",
                target=target_username,
                room=room_name,
                message=notice_text,
                extra={
                    "target_mode": "room",
                    "action": "kicked",
                    "dialog_message": target_text,
                },
            )

            self.send_to_username(target_username, restriction_packet)
            self.broadcast_to_room(room_name, notice_packet)
            self.send_to_username(admin_username, notice_packet)
            return

        self.public_restricted_users.add(target_username)
        notice_text = f"Admin kicked {target_username} from Public Chat."
        target_text = "You have been kicked from Public Chat and cannot send messages there anymore."

        notice_packet = create_packet(
            packet_type="moderation_notice",
            sender="Admin",
            target=target_username,
            message=notice_text,
            extra={"target_mode": "public", "action": "kicked"},
        )
        restriction_packet = create_packet(
            packet_type="moderation_restriction",
            sender="Admin",
            target=target_username,
            message=notice_text,
            extra={
                "target_mode": "public",
                "action": "kicked",
                "dialog_message": target_text,
            },
        )

        with self.lock:
            target_socket = self.clients.get(target_username)

        self.send_to_username(target_username, restriction_packet)
        self.broadcast(notice_packet, exclude_socket=target_socket)
        self._disconnect_username_after_notice(target_username)

    def _apply_ban_restriction(self, admin_username, target_username, target_mode, room_name, reason):
        notice_room = room_name if target_mode == "room" else None
        scope_text = room_name if target_mode == "room" and room_name else "Talkify"
        notice_text = f"Admin banned {target_username} from {scope_text}."
        target_text = f"You have been banned from {scope_text}."

        if target_mode == "room" and room_name:
            self.room_manager.remove_user_from_room(target_username, room_name)
            self.room_restricted_users.setdefault(room_name.lower(), set()).add(target_username)
        else:
            self.public_restricted_users.add(target_username)

        restriction_packet = create_packet(
            packet_type="moderation_restriction",
            sender="Admin",
            target=target_username,
            room=notice_room,
            message=notice_text,
            extra={
                "target_mode": target_mode if target_mode == "room" else "public",
                "action": "banned",
                "dialog_message": target_text,
            },
        )
        notice_packet = create_packet(
            packet_type="moderation_notice",
            sender="Admin",
            target=target_username,
            room=notice_room,
            message=notice_text,
            extra={
                "target_mode": target_mode if target_mode == "room" else "public",
                "action": "banned",
            },
        )

        self.send_to_username(target_username, restriction_packet)

        if target_mode == "room" and room_name:
            self.broadcast_to_room(room_name, notice_packet)
            self.send_to_username(admin_username, notice_packet)
        else:
            with self.lock:
                target_socket = self.clients.get(target_username)
            self.broadcast(notice_packet, exclude_socket=target_socket)

        self._disconnect_username_after_notice(target_username)

    def handle_delete_message(self, client_socket, packet):
        username = self.require_login(client_socket)
        if not username:
            return

        message_id = packet.get("message_id", "")
        message = self.message_store.get_message(message_id)

        if not message:
            return

        if message["sender"] != username:
            return

        self.message_store.mark_deleted(message_id)

        delete_packet = create_packet(
            packet_type="delete_message",
            sender="server",
            room=message.get("room"),
            target=message.get("target"),
            extra={
                "message_id": message_id,
                "scope": message.get("scope"),
            },
        )

        self._broadcast_message_update(message, delete_packet)
        self.send_admin_data_to_admins()

    def handle_message_reaction(self, client_socket, packet):
        username = self.require_login(client_socket)
        if not username:
            return

        message_id = packet.get("message_id", "").strip()
        emoji = packet.get("emoji", "").strip()
        if not message_id or not emoji:
            return

        message = self.message_store.add_reaction(message_id, emoji)
        if not message:
            return

        reaction_packet = create_packet(
            packet_type="message_reaction",
            sender=username,
            room=message.get("room"),
            target=message.get("target"),
            extra={
                "message_id": message_id,
                "emoji": emoji,
                "count": message.get("reactions", {}).get(emoji, 1),
                "scope": message.get("scope"),
            },
        )
        self._broadcast_message_update(message, reaction_packet)

    def _broadcast_message_update(self, message, packet):
        scope = message.get("scope")
        if scope == "room" and message.get("room"):
            self.broadcast_to_room(message.get("room"), packet)
        elif scope == "private":
            self.send_to_username(message.get("sender"), packet)
            self.send_to_username(message.get("target"), packet)
        else:
            self.broadcast(packet)

    def handle_request_admin_data(self, client_socket, packet):
        username = self.require_login(client_socket)
        if not username:
            return

        if not self.is_connected_admin(username):
            self.send_error(client_socket, "You are not allowed to access admin data.")
            return

        try:
            banned_users = self.database.get_banned_users()
        except Exception:
            banned_users = []

        stats = {
            "online_users": len(self.clients),
            "active_rooms": len(self.room_manager.get_all_rooms()),
            "messages_today": (
                self.message_store.count_messages_today()
                if hasattr(self.message_store, "count_messages_today")
                else len(self.message_store.messages)
            ),
        }

        self.send_packet(
            client_socket,
            create_packet(
                packet_type="admin_data",
                sender="server",
                extra={
                    "banned_users": banned_users,
                    "stats": stats,
                },
            ),
        )

    def send_login_failed(self, client_socket, message):
        self.send_packet(
            client_socket,
            create_packet("login_failed", sender="server", message=message),
        )

    def send_error(self, client_socket, message):
        self.send_packet(
            client_socket,
            create_packet("error", sender="server", message=message),
        )

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
                "room": room,
            },
        )
        self.send_to_username(username, packet)

    def remove_client(self, client_socket):
        with self.lock:
            username = self.client_usernames.pop(client_socket, None)

            is_admin = False
            if username in self.connected_profiles:
                is_admin = bool(self.connected_profiles[username].get("is_admin"))

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
            self.broadcast(
                create_packet(
                    "leave_notice",
                    sender="server",
                    message=f"{username} left the chat.",
                )
            )
            self.send_user_list()
            self.send_room_list()
            self.send_admin_data_to_admins()

        if is_admin:
            print("[ADMIN LEFT] Resetting messages")
            self.message_store.reset_messages()
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
                    "profile_picture": profile.get("profile_picture", "default_avatar.png"),
                    "display_name": profile.get("display_name", username),
                }
                for username, profile in self.connected_profiles.items()
            ]

        self.broadcast(
            create_packet(
                "user_list",
                sender="server",
                extra={"users": users},
            )
        )

    def send_room_list(self):
        rooms = [
            {
                "name": room,
                "members": self.room_manager.get_users_in_room(room),
            }
            for room in self.room_manager.get_all_rooms()
        ]
        self.broadcast(
            create_packet(
                "room_list",
                sender="server",
                extra={"rooms": rooms},
            )
        )

    def send_admin_data_to_admins(self):
        with self.lock:
            admin_sockets = [
                sock
                for username, sock in self.clients.items()
                if bool(self.connected_profiles.get(username, {}).get("is_admin"))
            ]

        for sock in admin_sockets:
            self.handle_request_admin_data(sock, {})