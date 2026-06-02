
from app.schemas.common import APISchema


class RootResponse(APISchema):
    service: str
    version: str
