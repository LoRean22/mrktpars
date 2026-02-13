import asyncio
from loguru import logger

from core.executor import TaskExecutor
from core.models import SearchTask


class Scheduler:
    def __init__(self):
        self.tasks: list[SearchTask] = []
        self.executor = TaskExecutor()

    def add_task(self, task: SearchTask):
        self.tasks.append(task)
        logger.info(f"Добавлена задача [user={task.user_id}, task={task.task_id}]")

    async def start(self):
        logger.info("Планировщик запущен")

        try:
            while True:
                for task in self.tasks:
                    if task.is_ready():
                        logger.info(
                            f"Выполнение задачи [user={task.user_id}, task={task.task_id}]"
                        )
                        await self.executor.run(task)
                        task.mark_run()

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("🛑 Планировщик остановлен")
