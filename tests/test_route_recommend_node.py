from dataclasses import replace
from types import SimpleNamespace
import unittest

from edcr.config import TTSConfig
from edcr.control_room.app import ControlRoomApp
from edcr.control_room.server.app import _handle_session_message, _server_hydrate_data
from edcr.control_room.server.broker import InMemoryObserverSessionBroker
from edcr.control_room.server.commands import trade_route_from_payload
from edcr.control_room.server.state import ControlRoomServerState
from edcr.route_recommend import RouteRecommendSettings
from edcr.route_recommend_node import RecommendationAnnouncer, RecommendationReceiver
from edcr.tts import AnnouncementId, NullSpeechBackend, TTSAnnouncer
from tests.test_control_room_server import _base_data_read_model, _CommandHandlerRecorder
from tests.test_route_recommend import row, recommendations


class RecommendationNodeTests(unittest.TestCase):
    def test_new_best_is_spoken_once_then_gap_and_improvement_apply(self):
        now = [0.0]
        spoken = []
        announce = RecommendationAnnouncer(settings=RouteRecommendSettings(), time_fn=lambda: now[0],
                                            announce=lambda message, **values: spoken.append((message, values)))
        def check(name, rate):
            announce.consider(recommendations([row(name, rate)]).to_payload())
        check("A", 100e6)
        check("A", 100e6)
        now[0] = 299
        check("C", 200e6)
        self.assertEqual(len(spoken), 1)
        now[0] = 300
        check("C", 200e6)
        now[0] = 600
        check("C", 220e6)
        self.assertEqual(len(spoken), 2)
        check("C", 230e6)
        self.assertEqual(len(spoken), 3)
        self.assertEqual(spoken[0][0], AnnouncementId.ROUTE_RECOMMENDED)
        self.assertEqual((spoken[0][1]["count"], spoken[0][1]["routes_word"], spoken[0][1]["more"]), ("One", "route", ""))

    def test_delivery_and_dismiss_leave_selection_and_running_route_untouched(self):
        state = ControlRoomServerState()
        selected = trade_route_from_payload(row()["trade_route"])
        state.set_selected_trade_route(selected)
        state.set_running_trade_route(selected)
        spoken, published = [], []
        receiver = RecommendationReceiver(store=state.set_route_recommendations, current=state.route_recommendations,
            publish=lambda: published.append(state.route_recommendations()),
            announcer=RecommendationAnnouncer(settings=RouteRecommendSettings(), time_fn=lambda: 0,
                announce=lambda message, **values: spoken.append(values)))
        recs = recommendations([row(), row("C", 130e6)], selected=row()["trade_route"])
        receiver.receive(recs)
        key = recs.routes[0]["key"]
        self.assertEqual(spoken[0]["gain_short"], "30 million credits")
        self.assertEqual(spoken[0]["more"], " more")
        self.assertTrue(state.dismiss_route_recommendation(key))
        receiver.receive(recs)
        self.assertEqual((len(spoken), published[-1]["routes"], published[-1]["dismissed"]), (1, [], 1))
        self.assertEqual(state.selected_trade_route(), selected)
        self.assertEqual(state.running_trade_route(), selected)
        state.set_selected_trade_route(selected)
        self.assertEqual(state.route_recommendations()["dismissed"], 1)
        state.set_selected_trade_route(trade_route_from_payload(row("D")["trade_route"]))
        self.assertIsNone(state.route_recommendations())
        receiver.receive(recs)
        self.assertEqual(state.route_recommendations()["dismissed"], 0)

    def test_disabled_recommendation_is_not_published_or_spoken(self):
        tts = TTSAnnouncer(TTSConfig(disabled_messages=("route_recommended",),
                                   phrases={"route_recommended": "New route"}), backend=NullSpeechBackend(), platform_name="darwin")
        self.addCleanup(tts.close)
        published = []
        host = SimpleNamespace(_haul_stats=SimpleNamespace(current_run=None), _tts=tts,
                               _publish_announcement=lambda *args: published.append(args))
        ControlRoomApp._announce_tts(host, AnnouncementId.ROUTE_RECOMMENDED)
        self.assertEqual(published, [])

    def test_server_select_and_dismiss_update_next_hydrate_without_starting(self):
        broker = InMemoryObserverSessionBroker()
        observer = broker.register_observer("web-haul")
        commands = _CommandHandlerRecorder()
        recs = recommendations([row("C", 130e6)])
        broker.server_state.set_route_recommendations(recs)
        def command(kind, payload):
            return _handle_session_message({"message_type": "command." + kind, "message_id": "m1", "payload": payload},
                session_id=observer.session_id, client_role="active_operator", command_handler=commands,
                broker=broker, data_provider=_base_data_read_model)
        self.assertEqual(_server_hydrate_data(_base_data_read_model(), broker=broker).route_recommendations["routes"], recs.routes)
        self.assertEqual(command("dismiss_route_recommendation", {"key": recs.routes[0]["key"]})["message_type"], "response.success")
        payload = observer.queue.get_nowait()["payload"]["route_recommendations"]
        self.assertEqual((payload["routes"], payload["dismissed"]), ([], 1))
        self.assertEqual(command("dismiss_route_recommendation", {"key": "missing"})["message_type"], "response.error")
        self.assertEqual(command("select_trade_route", {"route": recs.routes[0]["trade_route"]})["message_type"], "response.success")
        payload = observer.queue.get_nowait()["payload"]
        self.assertEqual(payload["selected_trade_route"]["from_station"], "C")
        self.assertIsNone(payload["route_recommendations"])
        self.assertIsNone(commands.persisted_running_trade_route)
