import socket
import threading

from shared.config import HOST, PORT, BUFFER_SIZE, ENCODING
from shared.protocol import create_packet, encode_packet, decode_packets


def receive_messages(sock):
    buffer = ""

    while True:
        try:
            data = sock.recv(BUFFER_SIZE)
            if not data:
                print("[INFO] Disconnected from server.")
                break

            buffer += data.decode(ENCODING)
            packets, buffer = decode_packets(buffer)

            for packet in packets:
                packet_type = packet.get("type")

                if packet_type == "public_message":
                    print(f"\n[PUBLIC] {packet.get('sender')}: {packet.get('message')}")

                elif packet_type == "private_message":
                    print(
                        f"\n[PRIVATE] {packet.get('sender')} -> "
                        f"{packet.get('target')}: {packet.get('message')}"
                    )

                elif packet_type == "room_message":
                    print(
                        f"\n[ROOM: {packet.get('room')}] "
                        f"{packet.get('sender')}: {packet.get('message')}"
                    )

                elif packet_type == "join_notice":
                    print(f"\n[NOTICE] {packet.get('message')}")

                elif packet_type == "leave_notice":
                    print(f"\n[NOTICE] {packet.get('message')}")

                elif packet_type == "user_list":
                    print(f"\n[USERS] {packet.get('users', [])}")

                elif packet_type == "room_list":
                    print(f"\n[ROOMS] {packet.get('rooms', [])}")

                elif packet_type == "room_joined":
                    print(f"\n[ROOM JOINED] {packet.get('message')}")

                elif packet_type == "login_success":
                    print(f"\n[SUCCESS] {packet.get('message')}")

                elif packet_type == "login_failed":
                    print(f"\n[LOGIN FAILED] {packet.get('message')}")

                elif packet_type == "error":
                    print(f"\n[ERROR] {packet.get('message')}")

                elif packet_type == "admin_response":
                    print(f"\n[ADMIN] {packet.get('message')}")

                else:
                    print(f"\n[RECEIVED] {packet}")

        except Exception as error:
            print(f"[RECEIVE ERROR] {error}")
            break


def show_help():
    print("\nAvailable commands:")
    print("  /all your message here")
    print("  /pm username your private message")
    print("  /join roomname")
    print("  /room roomname your room message")
    print("  /quit")
    print("  /kick username")
    print("  /ban username")
    print()


def main():
    username = input("Enter username: ").strip()

    if not username:
        print("Username cannot be empty.")
        return

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))

    login_packet = create_packet(
        packet_type="login",
        sender=username
    )
    client_socket.sendall(encode_packet(login_packet))

    threading.Thread(target=receive_messages, args=(client_socket,), daemon=True).start()

    show_help()

    while True:
        try:
            user_input = input("> ").strip()

            if not user_input:
                continue

            if user_input.lower() == "/quit":
                break

            elif user_input.startswith("/all "):
                message = user_input[5:].strip()

                packet = create_packet(
                    packet_type="public_message",
                    sender=username,
                    message=message
                )
                client_socket.sendall(encode_packet(packet))

            elif user_input.startswith("/pm "):
                parts = user_input.split(" ", 2)
                if len(parts) < 3:
                    print("Usage: /pm username message")
                    continue

                target_username = parts[1].strip()
                message = parts[2].strip()

                packet = create_packet(
                    packet_type="private_message",
                    sender=username,
                    target=target_username,
                    message=message
                )
                client_socket.sendall(encode_packet(packet))

            elif user_input.startswith("/join "):
                parts = user_input.split(" ", 1)
                room_name = parts[1].strip()

                packet = create_packet(
                    packet_type="join_room",
                    sender=username,
                    room=room_name
                )
                client_socket.sendall(encode_packet(packet))

            elif user_input.startswith("/room "):
                parts = user_input.split(" ", 2)
                if len(parts) < 3:
                    print("Usage: /room roomname message")
                    continue

                room_name = parts[1].strip()
                message = parts[2].strip()

                packet = create_packet(
                    packet_type="room_message",
                    sender=username,
                    room=room_name,
                    message=message
                )
                client_socket.sendall(encode_packet(packet))

            elif user_input.startswith("/kick "):
                target = user_input.split(" ", 1)[1]

                packet = create_packet(
                    packet_type="kick",
                    sender=username,
                    target=target
                )
                client_socket.sendall(encode_packet(packet))

            elif user_input.startswith("/ban "):
                target = user_input.split(" ", 1)[1]

                packet = create_packet(
                    packet_type="ban",
                    sender=username,
                    target=target
                )
                client_socket.sendall(encode_packet(packet))

            
            else:
                print("Unknown command.")
                show_help()

        except KeyboardInterrupt:
            print("\n[INFO] Client closed by user.")
            break
        except Exception as error:
            print(f"[SEND ERROR] {error}")
            break

    client_socket.close()


if __name__ == "__main__":
    main()