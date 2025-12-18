from abc import ABC, abstractmethod
from typing import Any, Dict
import ffmpeg

class ProcessingContext:
    def __init__(self, input_path: str, temp_dir: str, config: Dict[str, Any]):
        self.input_path = input_path
        self.temp_dir = temp_dir
        self.config = config
        self.metadata: Dict[str, Any] = {}

class BaseStep(ABC):
    @abstractmethod
    def apply(self, ctx: ProcessingContext, stream: Any) -> Any:
        """
        Applies a transformation to the ffmpeg stream.
        :param ctx: Processing context
        :param stream: ffmpeg-python stream object
        :return: Modified stream object
        """
        pass
