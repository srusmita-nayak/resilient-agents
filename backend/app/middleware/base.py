from abc import ABC, abstractmethod
from typing import Callable, Dict, Any, List
from app.agents.base import Agent
from app.core.clock import DiscreteEventScheduler
from app.core.channel import VirtualChannel
from app.core.messages import Message

class BaseMiddleware(ABC):
    """Abstract middleware coordinator for an agent within the simulated network."""
    def __init__(
        self,
        agent: Agent,
        scheduler: DiscreteEventScheduler,
        channel: VirtualChannel,
        task_id: str,
        run_id: str,
        round_budget: int,
        on_event: Callable[[Dict[str, Any]], None],
    ):
        self.agent = agent
        self.scheduler = scheduler
        self.channel = channel
        self.task_id = task_id
        self.run_id = run_id
        self.round_budget = round_budget
        self.on_event = on_event
        self.current_round = 0
        self.is_finished = False

    @abstractmethod
    def start(self) -> None:
        """Called once at simulation start to initiate rounds."""
        pass

    @abstractmethod
    def handle_message(self, message: Message) -> None:
        """Invoked when the virtual channel delivers a message to this agent."""
        pass
