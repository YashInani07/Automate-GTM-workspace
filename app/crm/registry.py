import importlib
import inspect
import os
import logging
from typing import Dict, Type, List, Optional
from app.crm.base import BaseCRM

logger = logging.getLogger(__name__)

class CRMRegistry:
    def __init__(self):
        self._crms: Dict[str, Type[BaseCRM]] = {}

    def register(self, crm_class: Type[BaseCRM]):
        instance = crm_class()
        name = instance.name
        self._crms[name] = crm_class
        logger.info(f"Registered CRM provider: {name}")

    def get_crm(self, name: str) -> Optional[BaseCRM]:
        crm_class = self._crms.get(name)
        if crm_class:
            return crm_class()
        return None

    def list_crms(self) -> List[str]:
        return list(self._crms.keys())

    def discover_crms(self):
        current_dir = os.path.dirname(__file__)
        for filename in os.listdir(current_dir):
            if filename.endswith(".py") and filename not in ("__init__.py", "base.py", "registry.py"):
                module_name = f"app.crm.{filename[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                    for name, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj)
                            and issubclass(obj, BaseCRM)
                            and obj is not BaseCRM
                        ):
                            self.register(obj)
                except Exception as e:
                    logger.error(f"Failed to load CRM module {module_name}: {e}")

crm_registry = CRMRegistry()
crm_registry.discover_crms()
