import aiomysql
import os

async def get_pool():
    return await aiomysql.create_pool(
        host="localhost",
        user="mrktpars_user",
        password="StrongPassword123!",
        db="mrktpars",
        autocommit=True,
        minsize=1,
        maxsize=10
    )
