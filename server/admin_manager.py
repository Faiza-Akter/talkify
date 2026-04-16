# server/admin_manager.py

class AdminManager:
    def __init__(self, server, database):
        self.server = server
        self.db = database

    def kick_user(self, admin_username, target_username):
        if not self.db.is_admin(admin_username):
            return False, "You are not an admin."

        if admin_username == target_username:
            return False, "You cannot kick yourself."

        if target_username not in self.server.clients:
            return False, f"User '{target_username}' is not online."

        target_socket = self.server.clients[target_username]
        self.server.remove_client(target_socket)

        return True, f"{target_username} has been kicked."

    def ban_user(self, admin_username, target_username, reason="No reason provided"):
        if not self.db.is_admin(admin_username):
            return False, "You are not an admin."

        if admin_username == target_username:
            return False, "You cannot ban yourself."

        if self.db.is_user_banned(target_username):
            return False, f"User '{target_username}' is already banned."

        # Save ban in database first
        self.db.ban_user(target_username, admin_username, reason)

        # If user is online, disconnect them
        if target_username in self.server.clients:
            target_socket = self.server.clients[target_username]
            self.server.remove_client(target_socket)
            return True, f"{target_username} has been banned and disconnected."

        return True, f"{target_username} has been banned."