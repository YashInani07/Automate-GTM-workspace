import importlib
import inspect
import os
import logging
from typing import Dict, Type, List, Optional
from app.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

class ConnectorRegistry:
    def __init__(self):
        self._connectors: Dict[str, Type[BaseConnector]] = {}

    def register(self, connector_class: Type[BaseConnector]):
        # Instantiate to fetch the name
        instance = connector_class()
        name = instance.name
        self._connectors[name] = connector_class
        logger.info(f"Registered connector: {name}")

    def get_connector(self, name: str) -> Optional[BaseConnector]:
        connector_class = self._connectors.get(name)
        if connector_class:
            return connector_class()
        return None

    def list_connectors(self) -> List[str]:
        return list(self._connectors.keys())

    def discover_connectors(self):
        current_dir = os.path.dirname(__file__)
        for filename in os.listdir(current_dir):
            if filename.endswith(".py") and filename not in ("__init__.py", "base.py", "registry.py"):
                module_name = f"app.connectors.{filename[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                    for name, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj)
                            and issubclass(obj, BaseConnector)
                            and obj is not BaseConnector
                        ):
                            self.register(obj)
                except Exception as e:
                    logger.error(f"Failed to load connector module {module_name}: {e}")

# Global registry instance
registry = ConnectorRegistry()
registry.discover_connectors()
