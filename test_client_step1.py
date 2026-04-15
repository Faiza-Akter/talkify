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
                print("\n[RECEIVED]", packet)

        except Exception as error:
            print("[RECEIVE ERROR]", error)
            break


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

    while True:
        try:
            message = input()
            if message.lower() == "/quit":
                break

            if not message.strip():
                continue

            packet = create_packet(
                packet_type="public_message",
                sender=username,
                message=message
            )
            client_socket.sendall(encode_packet(packet))

        except KeyboardInterrupt:
            print("\n[INFO] Client closed by user.")
            break
        except Exception as error:
            print("[SEND ERROR]", error)
            break

    client_socket.close()


if __name__ == "__main__":
    main()