"""Module that contains data structures/models"""

from dataclasses import dataclass


@dataclass
class AudioConfig:
    voice: str = "onyx"
    channels: int = 1
    sample_width: int = 2
    sample_rate: int = 24000
