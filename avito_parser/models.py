from dataclasses import dataclass
from pydantic import BaseModel

@dataclass
class AvitoItem:
    """
    Модель одного объявления Avito
    """
    id: str
    title: str
    price: int
    url: str


class AvitoItem(BaseModel):
    id: str
    title: str
    price: int
    url: str
    image_url: str | None = None
