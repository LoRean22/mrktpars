from pydantic import BaseModel


class AvitoItem(BaseModel):
    id: str
    title: str
    price: int
    url: str
    image_url: str | None = None

    seller_name: str | None = None
    seller_type: str | None = None
    seller_since: str | None = None