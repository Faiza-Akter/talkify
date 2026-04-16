# server/database.py

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

    def is_user_banned(self, username):
        cursor = self.get_cursor()
        query = "SELECT * FROM banned_users WHERE username=%s"
        cursor.execute(query, (username,))
        return cursor.fetchone() is not None

    def ban_user(self, username, banned_by, reason="No reason provided"):
        cursor = self.get_cursor()
        query = """
        INSERT INTO banned_users (username, banned_by, reason)
        VALUES (%s, %s, %s)
        """
        cursor.execute(query, (username, banned_by, reason))

    def is_admin(self, username):
        cursor = self.get_cursor()
        query = "SELECT * FROM users WHERE username=%s AND is_admin=TRUE"
        cursor.execute(query, (username,))
        return cursor.fetchone() is not None