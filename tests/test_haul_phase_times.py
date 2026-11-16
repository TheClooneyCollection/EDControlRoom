from copy import deepcopy
import unittest

from edcr.haul_phase_times import PhaseTimes


class HaulPhaseTimesTests(unittest.TestCase):
    def test_both_directions_keep_current_leg_and_only_completed_stage_samples(self):
        timing = PhaseTimes()
        timing.transition('buy', 1, 0)
        self.assertEqual(timing.snapshot(5)['buy'], dict(current_s=5, min_s=None, avg_s=None, samples=0))
        timing.transition('undock', 1, 10)
        timing.transition('depart', 1, 30)
        timing.transition('transit', 2, 60)
        # Departure names the source station; transit names its destination, on the same leg.
        view = timing.snapshot(100)
        self.assertEqual(view['buy'], dict(current_s=10, min_s=10, avg_s=10, samples=1))
        self.assertEqual(view['undock']['current_s'], 20)
        self.assertEqual(view['depart']['current_s'], 30)
        self.assertEqual(view['transit']['current_s'], 40)
        self.assertIsNone(view['sell']['current_s'])
        timing.transition('sell', 2, 160)
        timing.transition('buy', 2, 170)
        view = timing.snapshot(175)
        self.assertEqual(view['buy'], dict(current_s=5, min_s=None, avg_s=None, samples=0))
        self.assertIsNone(view['transit']['current_s'])
        timing.transition('undock', 2, 200)
        timing.transition('transit', 1, 240)
        timing.transition('sell', 1, 340)
        timing.transition('buy', 1, 350)
        self.assertEqual(timing.snapshot(355)['buy'], dict(current_s=5, min_s=10, avg_s=10, samples=1))
        timing.transition('undock', 1, 370)
        self.assertEqual(timing.snapshot(370)['buy'], dict(current_s=20, min_s=10, avg_s=15, samples=2))
        self.assertIsNone(timing.snapshot(370)['sell']['current_s'])

    def test_repeat_updates_pause_clock_and_interruption_do_not_add_samples(self):
        timing = PhaseTimes()
        timing.transition('transit', 2, 10)
        timing.transition('transit', 2, 20)
        # The caller's session clock is frozen while paused.
        self.assertEqual(timing.snapshot(30)['transit']['current_s'], 20)
        self.assertEqual(timing.snapshot(30)['transit']['current_s'], 20)
        timing.transition(None, None, 30)
        self.assertEqual(timing.snapshot(1000)['transit']['current_s'], 20)
        timing.transition('transit', 2, 30)
        timing.transition('sell', 2, 50)
        self.assertEqual(timing.snapshot(50)['transit']['avg_s'], 40)
        timing.transition(None, None, 60)
        timing.transition('buy', 2, 60)
        # Interrupted sell was never observed to finish, so it is not a minimum/average sample.
        self.assertNotIn('2:sell', timing.samples)

    def test_new_session_and_checkpoint_never_count_partial_stage_as_complete(self):
        timing = PhaseTimes(route=('A', 'B'))
        timing.transition('buy', 1, 0)
        timing.transition('undock', 1, 10)
        timing.reset_session()
        self.assertEqual(timing.snapshot(0)['undock']['current_s'], 0)
        timing.transition('depart', 1, 5)
        self.assertEqual(timing.snapshot(5)['undock']['samples'], 0)
        timing.transition('transit', 2, 15)
        checkpoint = timing.checkpoint(35)
        frozen = PhaseTimes.restore(checkpoint)
        self.assertEqual(frozen.route, ('A', 'B'))
        self.assertEqual(frozen.snapshot(999)['transit']['current_s'], 20)
        self.assertEqual(frozen.snapshot(999)['depart']['min_s'], 10)
        frozen.transition('transit', 2, 35)
        frozen.transition('sell', 2, 45)
        self.assertEqual(frozen.snapshot(45)['transit']['samples'], 0)
        self.assertEqual(checkpoint, timing.checkpoint(35))

    def test_missing_or_invalid_saved_values_cannot_poison_web_timers(self):
        self.assertEqual(PhaseTimes.restore(None).snapshot(0), {})
        payload = dict(route=['A'], phase='buy', direction=2, elapsed_s=float('nan'),
            current={'sell': float('inf'), 'buy': -2}, samples={'2:buy': [1, 10, 10],
            '2:sell': [0, 0, 0], '1:buy': [2, 10, 9], '2:depart': [True, 1, 1]})
        timing = PhaseTimes.restore(payload)
        self.assertEqual(timing.snapshot(100)['buy'], dict(current_s=0, min_s=10, avg_s=10, samples=1))
        self.assertEqual(timing.samples, {'2:buy': [1, 10, 10]})
        copied = deepcopy(timing)
        copied.reset_session()
        self.assertEqual(timing.snapshot(100)['buy']['samples'], 1)
