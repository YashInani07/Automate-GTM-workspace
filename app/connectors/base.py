from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseConnector(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Identification name of the connector."""
        pass

    @abstractmethod
    async def fetch(self, company_domain: str) -> Dict[str, Any]:
        """Fetches data for the given company domain and returns raw data dictionary."""
        pass
