import asyncio
from loguru import logger

from config.logging import setup_logging
from core.scheduler import Scheduler
from core.models import SearchTask


async def main_async():
    logger.info("Запуск асинхронного ядра")

    scheduler = Scheduler()

    scheduler.add_task(
        SearchTask(
            task_id=1,
            user_id=1001,
            search_url="https://www.avito.ru/moskva?q=iphone",
            interval=10,
        )
    )

    try:
        await scheduler.start()
    except asyncio.CancelledError:
        logger.info("🛑 Асинхронное ядро остановлено")


def main():
    setup_logging()
    logger.info("Приложение запущено")

    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("🛑 Завершение по Ctrl+C")


if __name__ == "__main__":
    main()
