# server/room_manager.py

from shared.config import DEFAULT_ROOM


class RoomManager:
    def __init__(self):
        """
        Stores room memberships and optional passwords:
        {
            "General": {"Faiza", "Ishfak"},
            "Study": {"Faiza"}
        }
        """
        self.rooms = {DEFAULT_ROOM: set()}
        self.room_passwords = {DEFAULT_ROOM: ""}
        self.room_creators = {}

    def create_room_if_not_exists(self, room_name, password="", creator=None):
        """Create room if it does not already exist."""
        if room_name not in self.rooms:
            self.rooms[room_name] = set()
            self.room_passwords[room_name] = password or ""
            if creator:
                self.room_creators[room_name] = creator

    def create_room(self, room_name, creator, password="", members=None):
        self.create_room_if_not_exists(room_name, password=password, creator=creator)
        self.rooms[room_name].add(creator)
        for member in members or []:
            if member:
                self.rooms[room_name].add(member)

    def can_join_room(self, room_name, password=""):
        if room_name not in self.rooms:
            return True
        expected = self.room_passwords.get(room_name, "")
        if not expected:
            return True
        return expected == (password or "")

    def add_user_to_room(self, username, room_name):
        """Add user to a room."""
        self.create_room_if_not_exists(room_name)
        self.rooms[room_name].add(username)

    def remove_user_from_room(self, username, room_name):
        """Remove user from a specific room."""
        if room_name in self.rooms:
            self.rooms[room_name].discard(username)

    def remove_user_from_all_rooms(self, username):
        empty_rooms = []

        for room, users in self.rooms.items():
            if username in users:
                users.remove(username)

            if not users and room != DEFAULT_ROOM:
                empty_rooms.append(room)

        for room in empty_rooms:
            del self.rooms[room]
            self.room_passwords.pop(room, None)
            self.room_creators.pop(room, None)

    def get_users_in_room(self, room_name):
        """Return all users in a room."""
        return list(self.rooms.get(room_name, set()))

    def get_all_rooms(self):
        """Return all room names."""
        return list(self.rooms.keys())

    def is_user_in_room(self, username, room_name):
        """Check whether user is in a room."""
        return username in self.rooms.get(room_name, set())
