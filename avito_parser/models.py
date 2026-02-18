from pydantic import BaseModel


class AvitoItem(BaseModel):
    id: str
    title: str
    price: int
    url: str
    image_url: str | None = None
