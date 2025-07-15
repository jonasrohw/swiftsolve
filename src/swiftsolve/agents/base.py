# agents/base.py
import abc
from utils.logger import get_logger

class Agent(abc.ABC):
    def __init__(self, name: str):
        self.name = name
        self.log = get_logger(name)

    @abc.abstractmethod
    def run(self, *args, **kwargs):
        """Execute agent logic."""