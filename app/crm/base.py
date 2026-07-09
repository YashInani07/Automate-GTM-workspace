from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseCRM(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Identification name of the CRM provider."""
        pass

    @abstractmethod
    async def sync_company(
        self,
        company_data: dict,
        analysis_data: dict,
        email_data: dict
    ) -> Dict[str, Any]:
        """Syncs the GTM profile, summary, and generated email to the CRM."""
        pass
