from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math
import random
from time import sleep as _default_sleep


VALID_TIMING_DISTRIBUTIONS = {"log_normal"}


@dataclass(frozen=True)
class TimingChannelConfig:
    sigma: float
    min_factor: float
    max_factor: float
    min_seconds: float = 0.0


@dataclass(frozen=True)
class TimingConfig:
    enabled: bool
    distribution: str
    delay: TimingChannelConfig
    hold: TimingChannelConfig
    typing: TimingChannelConfig


NormalSampler = Callable[[float, float], float]
SleepFn = Callable[[float], None]


class TimingSampler:
    def __init__(
        self,
        config: TimingConfig,
        *,
        normal_sampler: NormalSampler | None = None,
    ) -> None:
        self._config = config
        self._normal_sampler = normal_sampler if normal_sampler is not None else random.normalvariate

    def sample_delay(self, seconds: float) -> float:
        return self._sample(seconds, self._config.delay)

    def sample_hold(self, seconds: float) -> float:
        return self._sample(seconds, self._config.hold)

    def sample_typing_delay(self, seconds: float) -> float:
        return self._sample(seconds, self._config.typing)

    def make_sleep_sleeper(self, sleep_fn: SleepFn | None = None) -> SleepFn:
        sleeper = sleep_fn if sleep_fn is not None else _default_sleep

        def sampled_sleep(seconds: float) -> None:
            sleeper(self.sample_delay(seconds))

        return sampled_sleep

    def _sample(self, seconds: float, channel: TimingChannelConfig) -> float:
        bounded_seconds = max(0.0, seconds)
        if bounded_seconds <= 0 or not self._config.enabled:
            return bounded_seconds
        if self._config.distribution != "log_normal":
            raise ValueError(f"Unsupported timing distribution: {self._config.distribution}")

        sigma = max(0.0, channel.sigma)
        if sigma == 0:
            factor = 1.0
        else:
            # A clamped log-normal multiplier stays strictly positive and keeps a slight
            # long-tail bias that feels closer to human timing than uniform jitter.
            factor = math.exp(self._normal_sampler(-(sigma * sigma) / 2.0, sigma))
        factor = min(max(factor, channel.min_factor), channel.max_factor)
        return max(channel.min_seconds, bounded_seconds * factor)


def no_jitter_timing_config() -> TimingConfig:
    channel = TimingChannelConfig(sigma=0.0, min_factor=1.0, max_factor=1.0, min_seconds=0.0)
    return TimingConfig(
        enabled=False,
        distribution="log_normal",
        delay=channel,
        hold=channel,
        typing=channel,
    )


def no_jitter_timing_sampler() -> TimingSampler:
    return TimingSampler(no_jitter_timing_config())
