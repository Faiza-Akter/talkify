# server/admin_manager.py

class AdminManager:
    def __init__(self, server, database):
        self.server = server
        self.db = database

    def kick_user(self, admin_username, target_username):
        if not self.db.is_admin(admin_username):
            return False, "You are not an admin."

        if target_username not in self.server.clients:
            return False, "User not found."

        target_socket = self.server.clients[target_username]

        # Disconnect user
        self.server.remove_client(target_socket)

        return True, f"{target_username} has been kicked."

    def ban_user(self, admin_username, target_username):
        if not self.db.is_admin(admin_username):
            return False, "You are not an admin."

        if target_username not in self.server.clients:
            return False, "User not found."

        # Save to database
        self.db.ban_user(target_username, admin_username)

        target_socket = self.server.clients[target_username]

        # Disconnect user
        self.server.remove_client(target_socket)

        return True, f"{target_username} has been banned."