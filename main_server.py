# main_server.py

from server.server_main import ChatServer

if __name__ == "__main__":
    server = ChatServer()
    server.start()