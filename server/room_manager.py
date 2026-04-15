# server/room_manager.py

from shared.config import DEFAULT_ROOM


class RoomManager:
    def __init__(self):
        """
        Stores room memberships:
        {
            "General": {"Faiza", "Ishfak"},
            "Study": {"Faiza"}
        }
        """
        self.rooms = {
            DEFAULT_ROOM: set()
        }

    def create_room_if_not_exists(self, room_name):
        """Create room if it does not already exist."""
        if room_name not in self.rooms:
            self.rooms[room_name] = set()

    def add_user_to_room(self, username, room_name):
        """Add user to a room."""
        self.create_room_if_not_exists(room_name)
        self.rooms[room_name].add(username)

    def remove_user_from_room(self, username, room_name):
        """Remove user from a specific room."""
        if room_name in self.rooms:
            self.rooms[room_name].discard(username)

    def remove_user_from_all_rooms(self, username):
        """Remove user from every room."""
        for room_users in self.rooms.values():
            room_users.discard(username)

    def get_users_in_room(self, room_name):
        """Return all users in a room."""
        return list(self.rooms.get(room_name, set()))

    def get_all_rooms(self):
        """Return all room names."""
        return list(self.rooms.keys())

    def is_user_in_room(self, username, room_name):
        """Check whether user is in a room."""
        return username in self.rooms.get(room_name, set())