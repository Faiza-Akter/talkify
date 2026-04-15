# server/database.py

import pymysql


class Database:
    def __init__(self):
        """
        Initialize database connection.
        """
        self.connection = pymysql.connect(
            host="localhost",
            user="root",
            password="",  # change if your XAMPP has a password
            database="chat_app_db",  # your database name
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )

    def get_connection(self):
        return self.connection

    def get_cursor(self):
        return self.connection.cursor()

    def close(self):
        if self.connection:
            self.connection.close()