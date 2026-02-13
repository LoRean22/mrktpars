import pymysql
from pymysql.cursors import DictCursor


def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="mysql199300_",
        database="mrktpars",
        cursorclass=DictCursor,
        autocommit=True,
        charset="utf8mb4"
    )
