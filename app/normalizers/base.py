from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseNormalizer(ABC):
    @abstractmethod
    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes the raw input to the standard GTM schema.
        
        Returned schema:
        {
            "company": str,
            "industry": str,
            "description": str,
            "products": List[str],
            "recent_news": List[str],
            "social_links": List[str],
            "careers": List[str],
            "contact_information": {
                "emails": List[str],
                "phones": List[str]
            }
        }
        """
        pass
