from app.normalizers.base import BaseNormalizer
from app.normalizers.website import WebsiteNormalizer
from app.normalizers.jina import JinaNormalizer

_normalizers = {
    "website": WebsiteNormalizer(),
    "jina": JinaNormalizer()
}

def get_normalizer(connector_name: str) -> BaseNormalizer:
    return _normalizers.get(connector_name, WebsiteNormalizer())

__all__ = [
    "BaseNormalizer",
    "WebsiteNormalizer",
    "JinaNormalizer",
    "get_normalizer",
]
