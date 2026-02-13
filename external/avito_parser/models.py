from dataclasses import dataclass


@dataclass
class AvitoItem:
    """
    Модель одного объявления Avito
    """
    id: str
    title: str
    price: int
    url: str
