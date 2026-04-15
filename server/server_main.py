# server/server_main.py

import socket
import threading

from shared.config import HOST, PORT, BUFFER_SIZE, ENCODING
from shared.protocol import create_packet, encode_packet, decode_packets


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

    def start(self):
        """Start the TCP chat server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Allows quick restart without waiting for port release
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
                # Happens when server socket is closed during shutdown
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
        Handle a single connected client.

        Step 1 supports:
        - login
        - public chat
        - join/leave notifications
        - connected user list
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
                        # Prevent same socket from logging in again
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

                        success_packet = create_packet(
                            packet_type="login_success",
                            sender="server",
                            message=f"Welcome, {username}!"
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

                    elif packet_type == "public_message":
                        # User must log in first
                        if client_socket not in self.client_usernames:
                            error_packet = create_packet(
                                packet_type="error",
                                sender="server",
                                message="You must log in before sending messages."
                            )
                            client_socket.sendall(encode_packet(error_packet))
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

                    else:
                        unknown_packet = create_packet(
                            packet_type="error",
                            sender="server",
                            message=f"Unknown packet type: {packet_type}"
                        )
                        client_socket.sendall(encode_packet(unknown_packet))

        except ConnectionResetError:
            print(f"[DISCONNECTED] {client_address} forcibly closed the connection.")
        except Exception as error:
            print(f"[CLIENT ERROR] {client_address}: {error}")
        finally:
            self.remove_client(client_socket)

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
            print(f"[LEFT] {username} disconnected.")

            leave_packet = create_packet(
                packet_type="leave_notice",
                sender="server",
                message=f"{username} left the chat."
            )
            self.broadcast(leave_packet)
            self.send_user_list()

    def broadcast(self, packet, exclude_socket=None):
        """Send a packet to all connected clients."""
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

    def send_user_list(self):
        """Send updated user list to all connected clients."""
        with self.lock:
            usernames = list(self.clients.keys())

        packet = create_packet(
            packet_type="user_list",
            sender="server",
            extra={"users": usernames}
        )
        self.broadcast(packet)