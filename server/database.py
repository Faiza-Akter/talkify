import pymysql


class Database:
    def __init__(self):
        self.connection = pymysql.connect(
            host="localhost",
            user="root",
            password="",
            database="chat_app_db",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )

    def get_cursor(self):
        return self.connection.cursor()

    def ensure_user_exists(self, username):
        cursor = self.get_cursor()
        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        existing = cursor.fetchone()
        if existing:
            return

        cursor.execute(
            """
            INSERT INTO users (username, is_admin, profile_picture)
            VALUES (%s, %s, %s)
            """,
            (username, username.lower() == "admin", "default_avatar.png")
        )

    def is_user_banned(self, username):
        cursor = self.get_cursor()
        cursor.execute("SELECT id FROM banned_users WHERE username=%s", (username,))
        return cursor.fetchone() is not None

    def ban_user(self, username, banned_by, reason="No reason provided"):
        cursor = self.get_cursor()
        cursor.execute(
            """
            INSERT INTO banned_users (username, banned_by, reason)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                banned_by=VALUES(banned_by),
                reason=VALUES(reason)
            """,
            (username, banned_by, reason)
        )

    def is_admin(self, username):
        cursor = self.get_cursor()
        cursor.execute("SELECT is_admin FROM users WHERE username=%s", (username,))
        row = cursor.fetchone()
        return bool(row and row.get("is_admin"))

    def get_user_profile(self, username):
        cursor = self.get_cursor()
        cursor.execute(
            """
            SELECT username, is_admin, profile_picture
            FROM users
            WHERE username=%s
            """,
            (username,)
        )
        return cursor.fetchone()

    def update_profile_picture(self, username, profile_picture):
        cursor = self.get_cursor()
        cursor.execute(
            "UPDATE users SET profile_picture=%s WHERE username=%s",
            (profile_picture, username)
        )
