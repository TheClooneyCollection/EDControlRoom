from __future__ import annotations

import unittest

from edap.timing import TimingChannelConfig, TimingConfig, TimingSampler


def _config(*, enabled: bool = True) -> TimingConfig:
    channel = TimingChannelConfig(sigma=0.2, min_factor=0.8, max_factor=1.3, min_seconds=0.02)
    return TimingConfig(
        enabled=enabled,
        distribution="log_normal",
        delay=channel,
        hold=channel,
        typing=channel,
    )


class TimingSamplerTests(unittest.TestCase):
    def test_disabled_sampler_returns_original_values(self) -> None:
        sampler = TimingSampler(_config(enabled=False))

        self.assertEqual(sampler.sample_delay(0.5), 0.5)
        self.assertEqual(sampler.sample_hold(0.1), 0.1)
        self.assertEqual(sampler.sample_typing_delay(0.05), 0.05)

    def test_sampler_clamps_lognormal_multiplier(self) -> None:
        sampler = TimingSampler(_config(), normal_sampler=lambda mu, sigma: 10.0)

        self.assertEqual(sampler.sample_delay(1.0), 1.3)

    def test_sampler_respects_minimum_seconds(self) -> None:
        sampler = TimingSampler(_config(), normal_sampler=lambda mu, sigma: -10.0)

        self.assertEqual(sampler.sample_hold(0.01), 0.02)

    def test_sleep_sleeper_uses_sampled_delay(self) -> None:
        calls: list[float] = []
        sampler = TimingSampler(_config(), normal_sampler=lambda mu, sigma: 0.0)

        sampler.make_sleep_sleeper(calls.append)(0.5)

        self.assertEqual(calls, [0.5])
