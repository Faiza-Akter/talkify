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

    def get_banned_users(self):
        try:
            cursor = self.get_cursor()
            cursor.execute("""
                SELECT 
                    username,
                    MAX(reason) AS reason,
                    MAX(banned_by) AS banned_by,
                    MAX(banned_at) AS banned_at
                FROM banned_users
                GROUP BY LOWER(username)
                ORDER BY MAX(banned_at) DESC
            """)
            rows = cursor.fetchall()

            banned_users = []
            for row in rows:
                banned_at = row.get("banned_at")

                banned_users.append({
                    "username": row.get("username", ""),
                    "reason": row.get("reason", "No reason provided"),
                    "banned_by": row.get("banned_by", ""),
                    "banned_at": banned_at.strftime("%Y-%m-%d %I:%M %p") if banned_at else "",
                })

            return banned_users

        except Exception as e:
            print("[DB ERROR - get_banned_users]:", e)
            return []