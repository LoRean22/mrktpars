import pymysql

def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="mysql199300_",
        database="mrktpars",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )
