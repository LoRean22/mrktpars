import aiohttp
from loguru import logger

http_session: aiohttp.ClientSession | None = None


async def init_http_session():
    global http_session

    timeout = aiohttp.ClientTimeout(total=20)

    connector = aiohttp.TCPConnector(
        limit=100,
        ttl_dns_cache=300,
        ssl=False
    )

    http_session = aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
        cookie_jar=aiohttp.CookieJar()
    )

    logger.info("HTTP session initialized")


async def close_http_session():
    global http_session

    if http_session:
        await http_session.close()
        logger.info("HTTP session closed")
