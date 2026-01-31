from abc import ABC, abstractmethod
from playwright.async_api import Page

class BaseHandler(ABC):
    @abstractmethod
    async def get_actions(self, page: Page):
        """Returns JSON of what the user can DO on this page"""
        pass

    @abstractmethod
    async def execute(self, page: Page, action_id: str, params: dict):
        """Executes an action and returns result"""
        pass