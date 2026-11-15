from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from edcr.control_room.server.peer_recommendations import PeerRecommendations
from edcr.hub.voice import HubVoice
from edcr.route_recommend import RouteRecommendSettings
from tests.test_route_recommend import recommendations, row


def rendered(message, **values):
    return f"{values['count']} better {values['routes_word']}. Best: {values['from_station']}"


class PeerRecommendationOwnershipTests(unittest.TestCase):
    def test_default_owns_list_dismissals_and_per_node_repeat_gap_without_any_peer_frame(self):
        now, spoken, updates = [0], [], []
        state = PeerRecommendations(settings=RouteRecommendSettings(), time_fn=lambda: now[0], send=self.fail,
            render=rendered, callout=lambda node, text: spoken.append((node, text)), name=str)
        remove = state.listen('forge', lambda: updates.append(state.current('forge')))
        result = recommendations([row('C')])
        state.deliver('forge', result)
        state.deliver('other', result)
        self.assertEqual([node for node, text in spoken], ['forge', 'other'])
        self.assertTrue(spoken[0][1].startswith('forge: '))
        state.deliver('forge', recommendations([row('D', 200e6)]))
        self.assertEqual(len(spoken), 2)
        now[0] = 300
        state.deliver('forge', recommendations([row('D', 200e6)]))
        now[0] = 600
        state.deliver('forge', recommendations([row('D', 220e6)]))
        self.assertEqual(len(spoken), 3)
        state.deliver('forge', recommendations([row('D', 230e6)]))
        self.assertEqual(len(spoken), 4)
        key = state.current('forge')['routes'][0]['key']
        self.assertTrue(state.dismiss('forge', key))
        self.assertEqual((updates[-1]['routes'], updates[-1]['dismissed']), ([], 1))
        self.assertFalse(state.dismiss('forge', 'not a key'))
        self.assertEqual(len(state.current('other')['routes']), 1)
        state.selection('forge', row('new')['trade_route'])
        self.assertIsNone(state.current('forge'))
        state.deliver('forge', result)
        self.assertEqual(state.current('forge')['dismissed'], 0)
        remove()
        count = len(updates)
        state.deliver('forge', result)
        self.assertEqual(len(updates), count)

    def test_opt_in_sends_original_frame_and_keeps_state_and_voice_on_peer(self):
        frames = []
        def send(node, frame):
            frames.append((node, frame))
            return node != 'offline'
        state = PeerRecommendations(settings=replace(RouteRecommendSettings(), deliver_to_peers=True),
            time_fn=lambda: 0, send=send, render=self.fail, callout=self.fail, name=self.fail)
        result = recommendations([row()])
        self.assertTrue(state.deliver('forge', result))
        self.assertFalse(state.deliver('offline', result))
        self.assertEqual(frames[0], ('forge', {'type': 'route_recommendation', 'recommendations': result.to_payload()}))
        self.assertIsNone(state.current('forge'))
        self.assertFalse(state.owns)

    def test_hub_voice_selection_speakers_browser_mute_and_disabled_message_apply(self):
        speakers, browser, mutes = [], [], []
        now = [0]
        with TemporaryDirectory() as folder:
            voice = HubVoice(local_node_id='hub', settings_file=Path(folder)/'voice.json',
                speak=speakers.append, synthesize=None, names=str, set_muted=lambda node, mute: mutes.append((node, mute)),
                run_in_background=lambda run: run(), log=lambda line: None)
            disabled = [False]
            state = PeerRecommendations(settings=RouteRecommendSettings(), time_fn=lambda: now[0], send=self.fail,
                render=lambda message, **values: None if disabled[0] else rendered(message, **values),
                callout=voice.callout, name=str)
            state.deliver('forge', recommendations([row()]))
            self.assertEqual(speakers, [])
            voice.update({'node_id': 'forge', 'speakers': True, 'mute': True})
            remove = voice.add_listener(browser.append)
            now[0] = 300
            state.deliver('forge', recommendations([row('C')]))
            self.assertEqual(len(speakers), 1)
            self.assertEqual(browser[-1]['text'], speakers[0])
            self.assertIn(('forge', True), mutes)
            voice.update({'speakers': False})
            now[0] = 600
            state.deliver('forge', recommendations([row('D')]))
            self.assertEqual(len(speakers), 1)
            self.assertEqual(browser[-1]['text'], 'forge: One better route. Best: D')
            disabled[0] = True
            now[0] = 900
            count = len(browser)
            state.deliver('forge', recommendations([row('E')]))
            self.assertEqual(len(browser), count)
            remove()
