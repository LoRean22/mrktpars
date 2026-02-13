import asyncio
import random
from loguru import logger

from core.adapters.avito import AvitoAdapter
from core.models import SearchTask
from core.db.items import save_item


class TaskExecutor:
    def __init__(self):
        self.avito = AvitoAdapter()

    async def run(self, task: SearchTask):
        logger.info(f"Выполнение задачи [user={task.user_id}, task={task.task_id}]")

        results = await self.avito.parse(task.search_url)

        new_count = 0

        for item in results:
            is_new = save_item(
                task_id=task.task_id,
                user_id=task.user_id,
                title=item.title,
                price=item.price,
                url=item.url
            )

            if is_new:
                new_count += 1
                logger.info(
                    f"🆕 НОВОЕ | {item.title} | {item.price} ₽ | {item.url}"
                )

        logger.info(
            f"Задача {task.task_id}: новых объявлений — {new_count}"
        )

        # антибан-пауза
        delay = random.randint(20, 30)
        logger.info(f"⏳ Пауза {delay} секунд")
        await asyncio.sleep(delay)
