# server/server_main.py

import socket
import threading

from shared.config import HOST, PORT, BUFFER_SIZE, ENCODING, DEFAULT_ROOM
from shared.protocol import create_packet, encode_packet, decode_packets
from server.room_manager import RoomManager


class ChatServer:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.is_running = False

        # username -> client socket
        self.clients = {}

        # client socket -> username
        self.client_usernames = {}

        self.lock = threading.Lock()
        self.room_manager = RoomManager()

    def start(self):
        """Start the TCP chat server."""
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
        """Stop the server and close all sockets."""
        self.is_running = False

        with self.lock:
            sockets_to_close = list(self.client_usernames.keys())
            self.clients.clear()
            self.client_usernames.clear()

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
        """
        Handle one connected client.

        Step 2 supports:
        - login
        - public chat
        - private chat
        - room joining
        - room messaging
        - join/leave notifications
        - user list
        - room list
        """
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
                            error_packet = create_packet(
                                packet_type="error",
                                sender="server",
                                message="You are already logged in."
                            )
                            client_socket.sendall(encode_packet(error_packet))
                            continue

                        requested_username = packet.get("sender", "").strip()

                        if not requested_username:
                            error_packet = create_packet(
                                packet_type="login_failed",
                                sender="server",
                                message="Username cannot be empty."
                            )
                            client_socket.sendall(encode_packet(error_packet))
                            continue

                        with self.lock:
                            if requested_username in self.clients:
                                error_packet = create_packet(
                                    packet_type="login_failed",
                                    sender="server",
                                    message="Username already taken."
                                )
                                client_socket.sendall(encode_packet(error_packet))
                                continue

                            self.clients[requested_username] = client_socket
                            self.client_usernames[client_socket] = requested_username

                        username = requested_username

                        # Automatically join default room
                        self.room_manager.add_user_to_room(username, DEFAULT_ROOM)

                        success_packet = create_packet(
                            packet_type="login_success",
                            sender="server",
                            message=f"Welcome, {username}!",
                            extra={"room": DEFAULT_ROOM}
                        )
                        client_socket.sendall(encode_packet(success_packet))

                        print(f"[LOGIN] {username} joined from {client_address}")

                        join_packet = create_packet(
                            packet_type="join_notice",
                            sender="server",
                            message=f"{username} joined the chat."
                        )
                        self.broadcast(join_packet, exclude_socket=client_socket)

                        self.send_user_list()
                        self.send_room_list()

                    elif packet_type == "public_message":
                        if client_socket not in self.client_usernames:
                            self.send_error(client_socket, "You must log in before sending messages.")
                            continue

                        username = self.client_usernames[client_socket]
                        msg = packet.get("message", "").strip()

                        if not msg:
                            continue

                        public_packet = create_packet(
                            packet_type="public_message",
                            sender=username,
                            message=msg
                        )

                        print(f"[PUBLIC] {username}: {msg}")
                        self.broadcast(public_packet)

                    elif packet_type == "private_message":
                        if client_socket not in self.client_usernames:
                            self.send_error(client_socket, "You must log in before sending private messages.")
                            continue

                        username = self.client_usernames[client_socket]
                        target_username = packet.get("target", "").strip()
                        msg = packet.get("message", "").strip()

                        if not target_username or not msg:
                            self.send_error(client_socket, "Private message target and message are required.")
                            continue

                        self.send_private_message(username, target_username, msg)

                    elif packet_type == "join_room":
                        if client_socket not in self.client_usernames:
                            self.send_error(client_socket, "You must log in before joining a room.")
                            continue

                        username = self.client_usernames[client_socket]
                        room_name = packet.get("room", "").strip()

                        if not room_name:
                            self.send_error(client_socket, "Room name cannot be empty.")
                            continue

                        self.room_manager.add_user_to_room(username, room_name)

                        joined_packet = create_packet(
                            packet_type="room_joined",
                            sender="server",
                            room=room_name,
                            message=f"{username} joined room '{room_name}'."
                        )
                        client_socket.sendall(encode_packet(joined_packet))

                        print(f"[ROOM JOIN] {username} joined room: {room_name}")

                        self.send_room_list()

                    elif packet_type == "room_message":
                        if client_socket not in self.client_usernames:
                            self.send_error(client_socket, "You must log in before sending room messages.")
                            continue

                        username = self.client_usernames[client_socket]
                        room_name = packet.get("room", "").strip()
                        msg = packet.get("message", "").strip()

                        if not room_name or not msg:
                            self.send_error(client_socket, "Room name and message are required.")
                            continue

                        if not self.room_manager.is_user_in_room(username, room_name):
                            self.send_error(client_socket, f"You are not a member of room '{room_name}'.")
                            continue

                        room_packet = create_packet(
                            packet_type="room_message",
                            sender=username,
                            room=room_name,
                            message=msg
                        )

                        print(f"[ROOM:{room_name}] {username}: {msg}")
                        self.broadcast_to_room(room_name, room_packet)

                    else:
                        self.send_error(client_socket, f"Unknown packet type: {packet_type}")

        except ConnectionResetError:
            print(f"[DISCONNECTED] {client_address} forcibly closed the connection.")
        except Exception as error:
            print(f"[CLIENT ERROR] {client_address}: {error}")
        finally:
            self.remove_client(client_socket)

    def send_error(self, client_socket, message):
        """Send error packet to a client."""
        error_packet = create_packet(
            packet_type="error",
            sender="server",
            message=message
        )
        try:
            client_socket.sendall(encode_packet(error_packet))
        except Exception:
            pass

    def send_private_message(self, sender_username, target_username, msg):
        """Send private message from one user to another."""
        with self.lock:
            target_socket = self.clients.get(target_username)
            sender_socket = self.clients.get(sender_username)

        if not target_socket:
            if sender_socket:
                self.send_error(sender_socket, f"User '{target_username}' is not online.")
            return

        private_packet = create_packet(
            packet_type="private_message",
            sender=sender_username,
            target=target_username,
            message=msg
        )

        try:
            target_socket.sendall(encode_packet(private_packet))
            if sender_socket and sender_socket != target_socket:
                sender_socket.sendall(encode_packet(private_packet))
            print(f"[PRIVATE] {sender_username} -> {target_username}: {msg}")
        except Exception:
            self.remove_client(target_socket)

    def remove_client(self, client_socket):
        """Remove disconnected client from server lists."""
        with self.lock:
            username = self.client_usernames.pop(client_socket, None)
            if username in self.clients:
                del self.clients[username]

        try:
            client_socket.close()
        except Exception:
            pass

        if username:
            self.room_manager.remove_user_from_all_rooms(username)

            print(f"[LEFT] {username} disconnected.")

            leave_packet = create_packet(
                packet_type="leave_notice",
                sender="server",
                message=f"{username} left the chat."
            )
            self.broadcast(leave_packet)
            self.send_user_list()
            self.send_room_list()

    def broadcast(self, packet, exclude_socket=None):
        """Send packet to all connected clients."""
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

    def broadcast_to_room(self, room_name, packet):
        """Send a packet only to users inside a specific room."""
        encoded = encode_packet(packet)
        room_users = self.room_manager.get_users_in_room(room_name)

        dead_sockets = []

        with self.lock:
            for username in room_users:
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
        """Send updated user list to all clients."""
        with self.lock:
            usernames = list(self.clients.keys())

        packet = create_packet(
            packet_type="user_list",
            sender="server",
            extra={"users": usernames}
        )
        self.broadcast(packet)

    def send_room_list(self):
        """Send updated room list to all clients."""
        rooms = self.room_manager.get_all_rooms()

        packet = create_packet(
            packet_type="room_list",
            sender="server",
            extra={"rooms": rooms}
        )
        self.broadcast(packet)