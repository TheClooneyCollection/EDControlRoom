from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
from unittest import mock

from edap.binding_lookup import KEY_ALIASES, normalize_internal_key_name
from edap.config import ConfigError, InputConfig, WineHelperConfig, load_config, validate_wine_helper
from edap.platform.input.macos import MacOSInputController
from edap.platform.input.scancodes import resolve_scancode
from edap.platform.input.wine_helper import BurstAborted, FocusFailed, HelperError, build_wine_helper, check_crossover_match, load_or_create_token
from edap.timing import no_jitter_timing_sampler
from tests.fixtures.wine_helper import helper_client, unexpected


CONFIG = WineHelperConfig(wine_path='/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/wine', bottle='Test', launch='manual')
TOKEN = 'a' * 64


class Server:
    def __init__(self, replies=()):
        self.requests = []
        self.replies = list(replies)
        self.closed = False
        self.held = set()

    def write(self, line):
        self.requests.append(json.loads(line))

    def flush(self):
        pass

    def readline(self, limit):
        request = self.requests[-1]
        if self.replies:
            reply = self.replies.pop(0)
            if isinstance(reply, BaseException):
                raise reply
            if reply is not None:
                return reply if isinstance(reply, bytes) else json.dumps(reply).encode() + b'\n'
        op = request['op']
        reply = {'ok': True}
        if op == 'hello':
            reply.update(helper_version='0.1.0', protocol=1)
        elif op == 'target':
            reply.update(hwnd='0x2A', pid=312)
        elif op == 'focus':
            reply.update(step='already', fg_before='EliteDangerous64.exe')
        elif op == 'key':
            code = (request['scan'], request['ext'])
            if request['down']:
                self.held.add(code)
            else:
                self.held.discard(code)
        elif op == 'release_all':
            self.held.clear()
        elif op == 'status':
            reply.update(fg='EliteDangerous64.exe', target_alive=True, held=list(self.held))
        return json.dumps(reply).encode() + b'\n'

    def close(self):
        self.closed = True
        self.held.clear()


class Connections:
    def __init__(self, *streams):
        self.streams = list(streams)
        self.addresses = []

    def __call__(self, host, port, timeout):
        self.addresses.append((host, port, timeout))
        stream = self.streams.pop(0)
        if isinstance(stream, BaseException):
            raise stream
        return stream


def connected(server, *, config=CONFIG, **deps):
    defaults = dict(connect=Connections(server), read_token=lambda path: TOKEN)
    defaults.update(deps)
    client = helper_client(config, **defaults)
    client.start()
    return client


class HelperProtocolTests(unittest.TestCase):
    def test_galaxy_map_burst_uses_focus_and_physical_modifier_and_releases_both(self):
        server = Server()
        waits = []
        client = connected(server, sleeper=waits.append)
        client.tap_key('m', 'left_control', .2)
        self.assertEqual(server.requests, [
            {'op': 'hello', 'token': TOKEN, 'protocol': 1},
            {'op': 'target', 'process': 'EliteDangerous64.exe'}, {'op': 'release_all'},
            {'op': 'focus'},
            {'op': 'key', 'scan': 29, 'ext': False, 'down': True},
            {'op': 'key', 'scan': 50, 'ext': False, 'down': True},
            {'op': 'key', 'scan': 50, 'ext': False, 'down': False},
            {'op': 'key', 'scan': 29, 'ext': False, 'down': False},
        ])
        self.assertEqual(waits, [.2])
        self.assertEqual(client.status()['held'], [])
        self.assertIn('wine helper (EliteDangerous64.exe hwnd 0x2A, helper 0.1.0)', client.target.summary())

    def test_missing_target_aborts_before_any_key_and_disconnects(self):
        server = Server()
        client = connected(server)
        server.replies = [{'ok': False, 'error': 'no_target', 'detail': 'no_target'}]
        with self.assertRaisesRegex(HelperError, 'wine helper no_target: no_target'):
            client.tap_key('m', 'left_control', 0)
        self.assertFalse(any(r['op'] == 'key' for r in server.requests))
        self.assertTrue(server.closed)

    def test_long_lived_helper_retries_focus_lost_after_mac_app_switch(self):
        # A long-running server's helper focuses Elite once, then the Mac front app changes and
        # winemac moves the Win32 foreground away, so the next burst's first focus is refused.
        server = Server()
        waits = []
        client = connected(server, sleeper=waits.append)
        client.tap_key('m', 'left_control', 0)
        server.requests.clear()
        server.replies = [{'ok': False, 'error': 'focus_failed', 'detail': 'focus_failed'}]
        client.tap_key('m', 'left_control', 0)
        self.assertEqual([r['op'] for r in server.requests], ['focus', 'focus', 'key', 'key', 'key', 'key'])
        self.assertEqual(waits, [0.1])
        self.assertFalse(server.closed)

    def test_slow_focus_reconnects_and_retries_instead_of_aborting_the_burst(self):
        # The helper's child-process focus fallback can outlast request_timeout_s.
        first, second = Server(), Server()
        waits = []
        client = connected(first, connect=Connections(first, second), sleeper=waits.append)
        first.replies = [TimeoutError('timed out')]
        client.tap_key('m', None, 0)
        self.assertTrue(first.closed)
        self.assertEqual([r['op'] for r in second.requests], ['hello', 'target', 'release_all', 'focus', 'key', 'key'])
        self.assertEqual(waits, [0.1])

    def test_slow_key_ack_still_aborts_the_burst(self):
        first, second = Server(), Server()
        client = connected(first, connect=Connections(first, second))
        first.replies = [None, TimeoutError('timed out')]
        with self.assertRaisesRegex(BurstAborted, 'not replayed'):
            client.tap_key('m', None, 0)
        self.assertFalse(any(r['op'] == 'key' for r in second.requests))

    def test_persistent_focus_failure_sends_no_keys_and_keeps_the_connection(self):
        server = Server()
        waits = []
        client = connected(server, sleeper=waits.append)
        server.replies = [{'ok': False, 'error': 'focus_failed', 'detail': 'focus_failed'}] * 2
        with self.assertRaisesRegex(FocusFailed, "couldn't focus Elite inside the CrossOver bottle"):
            client.tap_key('m', 'left_control', 0)
        self.assertEqual([r['op'] for r in server.requests[3:]], ['focus'] * 2)
        self.assertEqual(waits, [0.1])
        self.assertFalse(server.closed)
        server.requests.clear()
        client.tap_key('m', 'left_control', 0)
        self.assertEqual(server.requests[0], {'op': 'focus'})
        self.assertEqual(server.held, set())

    def test_focus_lost_before_a_key_down_releases_and_reports_focus_failure(self):
        server = Server()
        client = connected(server)
        server.replies = [None, None, {'ok': False, 'error': 'focus_failed', 'detail': 'focus_failed'}]
        with self.assertRaises(FocusFailed):
            client.tap_key('m', 'left_control', 0)
        self.assertEqual([r['op'] for r in server.requests[3:]], ['focus', 'key', 'key', 'release_all'])
        self.assertEqual(server.held, set())

    def test_partial_modifier_burst_reconnects_releases_and_never_replays_key_down(self):
        first, second = Server(), Server()
        connections = Connections(first, second)
        client = connected(first, connect=connections)
        first.replies = [None, None, OSError('lost key ack')]
        with self.assertRaisesRegex(BurstAborted, 'not replayed'):
            client.tap_key('m', 'left_control', 0)
        self.assertEqual(second.requests[:3], [
            {'op': 'hello', 'token': TOKEN, 'protocol': 1},
            {'op': 'target', 'process': 'EliteDangerous64.exe'}, {'op': 'release_all'}])
        self.assertFalse(any(r['op'] == 'key' for r in second.requests))
        self.assertEqual(len(connections.addresses), 2)
        client.tap_key('m', None, 0)
        self.assertEqual(second.held, set())

    def test_failed_reconnect_attempts_only_once_and_no_fallback(self):
        first = Server()
        connections = Connections(first, ConnectionRefusedError())
        client = connected(first, connect=connections)
        first.replies = [OSError('closed')]
        with self.assertRaisesRegex(BurstAborted, 'reconnect failed'):
            client.press_key('m')
        self.assertEqual(len(connections.addresses), 2)
        self.assertTrue(first.closed)

    def test_interrupted_sleep_releases_held_modifier_and_key(self):
        server = Server()
        def interrupted(duration):
            raise KeyboardInterrupt()
        client = connected(server, sleeper=interrupted)
        with self.assertRaises(KeyboardInterrupt):
            client.tap_key('m', 'left_control', .2)
        self.assertEqual(server.held, set())
        self.assertEqual(server.requests[-1], {'op': 'release_all'})

    def test_release_failure_reconnects_to_empty_held_state(self):
        first, second = Server(), Server()
        client = connected(first, connect=Connections(first, second))
        first.replies = [None, None, None, OSError('key up ack lost')]
        with self.assertRaises(BurstAborted):
            client.tap_key('m', 'right_control', 0)
        self.assertEqual(second.held, set())
        self.assertTrue(first.closed)

    def test_alt_and_unknown_keys_fail_before_focus(self):
        for key, modifier in [('left_alt', None), ('right_alt', None), ('m', 'alt'), ('m', 'right_option'), ('unknown', None), ('m', 'unknown')]:
            with self.subTest(key=key, modifier=modifier):
                server = Server()
                client = connected(server)
                with self.assertRaises(ValueError):
                    client.tap_key(key, modifier, 0)
                self.assertEqual([r['op'] for r in server.requests], ['hello', 'target', 'release_all'])

    def test_press_and_release_support_extended_keys_and_manual_close_keeps_helper_running(self):
        server = Server()
        client = connected(server)
        client.press_key('up', 'right_control')
        self.assertEqual(server.held, {(0x48, True), (0x1D, True)})
        client.release_key('up', 'right_control')
        self.assertEqual(server.held, set())
        client.close()
        self.assertTrue(server.closed)
        self.assertNotIn('bye', [r['op'] for r in server.requests])

    def test_handshake_mismatch_does_not_launch_another_helper(self):
        for reply, expected in [
            ({'ok': False, 'error': 'bad_token', 'detail': 'token mismatch'}, 'bad_token'),
            ({'ok': True, 'protocol': 2}, 'protocol mismatch'),
            (b'not json\n', 'invalid reply'),
            ({'ok': 'true'}, 'invalid reply'),
            ({'ok': True, 'protocol': 1}, 'invalid hello'),
        ]:
            with self.subTest(reply=reply):
                server = Server([reply])
                client = helper_client(replace(CONFIG, launch='managed'), connect=Connections(server), read_token=lambda path: TOKEN)
                with self.assertRaisesRegex(HelperError, expected):
                    client.start()
                self.assertTrue(server.closed)

    def test_mac_routes_helper_semantics_and_never_hid_even_when_offline(self):
        server = Server()
        client = helper_client(CONFIG, connect=Connections(server, ConnectionRefusedError()), read_token=lambda path: TOKEN)
        controller = MacOSInputController(wine_helper=client, poster=unexpected, pid_poster=unexpected,
                                          timing_sampler=no_jitter_timing_sampler(), sleeper=unexpected)
        controller.set_wine_helper_target()
        controller.tap_key('m', 'left_control')
        self.assertEqual(controller.input_status()['wine_helper']['held'], [])
        self.assertEqual(controller.input_status()['wine_helper_config']['bottle'], 'Test')
        server.replies = [OSError('offline')]
        with self.assertRaises(BurstAborted):
            controller.tap_key('m')
        self.assertEqual(controller.current_target().mode, 'wine_helper')

    def test_selected_mode_does_not_connect_and_refuses_input_without_hid(self):
        controller = MacOSInputController(wine_helper=helper_client(CONFIG), poster=unexpected, pid_poster=unexpected,
                                          timing_sampler=no_jitter_timing_sampler(), sleeper=unexpected)
        controller.select_wine_helper_mode()
        self.assertEqual(controller.current_target().summary(),
                         'wine helper (EliteDangerous64.exe hwnd unresolved, helper disconnected)')
        self.assertEqual(controller.input_status()['wine_helper'], {'connected': False})
        with self.assertRaisesRegex(RuntimeError, 'client is closed'):
            controller.tap_key('m', 'left_control')
        controller.set_foreground_target()
        self.assertEqual(controller.current_target().mode, 'foreground')

    def test_factory_selects_configured_helper_without_launching_it(self):
        from edap.platform.input.factory import build_input_controller
        controller = build_input_controller('macos', input_config=InputConfig(target='wine_helper', wine_helper=CONFIG),
                                            timing_sampler=no_jitter_timing_sampler())
        self.assertEqual(controller.current_target().mode, 'wine_helper')
        self.assertFalse(controller._wine_helper.connected)

    def test_closed_client_cannot_reconnect_until_explicitly_selected(self):
        server, replacement = Server(), Server()
        client = connected(server, connect=Connections(server, replacement))
        client.close()
        with self.assertRaisesRegex(RuntimeError, 'client is closed'):
            client.press_key('m')
        self.assertEqual(replacement.requests, [])
        client.start()
        client.tap_key('m', None, 0)
        self.assertEqual(replacement.held, set())

    def test_explicit_switch_releases_helper_before_foreground_input(self):
        server = Server()
        client = connected(server)
        posted = []
        controller = MacOSInputController(wine_helper=client, poster=lambda *event: posted.append(event),
                                          timing_sampler=no_jitter_timing_sampler())
        controller.set_wine_helper_target()
        controller.press_key('m')
        controller.set_foreground_target()
        self.assertEqual(server.held, set())
        controller.tap_key('m')
        self.assertEqual(len(posted), 2)


class Process:
    def __init__(self, timeouts=0):
        self.actions = []
        self.timeouts = timeouts

    def wait(self, timeout):
        self.actions.append('wait')
        if self.timeouts:
            self.timeouts -= 1
            raise subprocess.TimeoutExpired('wine', timeout)

    def terminate(self):
        self.actions.append('terminate')

    def kill(self):
        self.actions.append('kill')


class HelperLifecycleTests(unittest.TestCase):
    def test_managed_launch_argv_retry_then_bye_and_process_reaping(self):
        server, process = Server(), Process(timeouts=1)
        launches, waits = [], []
        def launch(argv):
            launches.append(argv)
            return process
        client = helper_client(replace(CONFIG, launch='managed'),
                               connect=Connections(ConnectionRefusedError(), ConnectionRefusedError(), server),
                               read_token=lambda path: TOKEN, process_table=lambda: '', popen=launch,
                               sleeper=waits.append, clock=lambda: 0)
        client.start()
        self.assertEqual(launches, [[CONFIG.wine_path, '--bottle', 'Test', CONFIG.helper_path,
                                    '--port', '47811', '--token', TOKEN, '--log', r'C:\edap\helper.log', '--max-hold-s', '30.0']])
        self.assertEqual(waits, [.05])
        client.close()
        self.assertEqual(server.requests[-2:], [{'op': 'release_all'}, {'op': 'bye'}])
        self.assertEqual(process.actions, ['wait', 'terminate', 'wait'])

    def test_managed_helper_launches_outside_the_terminal_so_ctrl_c_cannot_reach_it(self):
        client = build_wine_helper(replace(CONFIG, launch='managed'))
        with mock.patch('edap.platform.input.wine_helper.subprocess.Popen') as popen:
            client._popen(['wine'])
        popen.assert_called_once_with(['wine'], stdin=subprocess.DEVNULL, start_new_session=True)

    def test_managed_restart_reuses_authenticated_helper_without_process_lookup_or_launch(self):
        server = Server()
        client = connected(server, config=replace(CONFIG, launch='managed'))
        client.close()
        self.assertEqual(server.requests[-1], {'op': 'bye'})

    def test_quit_after_a_helper_error_reconnects_to_stop_the_managed_helper(self):
        server, replacement = Server(), Server()
        client = connected(server, config=replace(CONFIG, launch='managed'), connect=Connections(server, replacement))
        server.replies = [{'ok': False, 'error': 'no_target', 'detail': 'no_target'}]
        with self.assertRaises(HelperError):
            client.tap_key('m', None, 0)
        client.close()
        self.assertEqual([r['op'] for r in replacement.requests], ['hello', 'target', 'release_all', 'release_all', 'bye'])

    def test_quit_with_the_helper_already_gone_still_closes(self):
        server = Server()
        client = connected(server, config=replace(CONFIG, launch='managed'),
                           connect=Connections(server, ConnectionRefusedError()))
        server.replies = [{'ok': False, 'error': 'no_target', 'detail': 'no_target'}]
        with self.assertRaises(HelperError):
            client.tap_key('m', None, 0)
        client.close()
        with self.assertRaisesRegex(RuntimeError, 'client is closed'):
            client.press_key('m')

    def test_unreachable_manual_helper_reports_endpoint_and_never_launches(self):
        client = helper_client(CONFIG, connect=Connections(ConnectionRefusedError()), read_token=lambda path: TOKEN)
        with self.assertRaisesRegex(RuntimeError, 'wine helper not reachable on 127.0.0.1:47811'):
            client.start()

    def test_running_other_crossover_app_is_refused_before_launch(self):
        table = ' 123 /Applications/CrossOver Preview.app/Contents/SharedSupport/CrossOver/bin/winewrapper.exe --bottle Test C:\\game\\EliteDangerous64.exe'
        client = helper_client(replace(CONFIG, launch='managed'), connect=Connections(ConnectionRefusedError()),
                               read_token=lambda path: TOKEN, process_table=lambda: table)
        with self.assertRaisesRegex(RuntimeError, 'CrossOver app mismatch'):
            client.start()
        check_crossover_match(CONFIG.wine_path, 'Other', table)
        check_crossover_match(CONFIG.wine_path, 'Test', table.replace('CrossOver Preview.app', 'CrossOver.app'))

    def test_startup_timeout_reaps_owned_process(self):
        process = Process(timeouts=2)
        times = iter([0, 11])
        client = helper_client(replace(CONFIG, launch='managed'), connect=Connections(ConnectionRefusedError(), ConnectionRefusedError()),
                               read_token=lambda path: TOKEN, process_table=lambda: '', popen=lambda argv: process, clock=lambda: next(times))
        with self.assertRaisesRegex(RuntimeError, 'not reachable'):
            client.start()
        self.assertEqual(process.actions, ['wait', 'terminate', 'wait', 'kill', 'wait'])


class HelperConfigTests(unittest.TestCase):
    def test_defaults_keep_foreground_and_required_launch_config_is_explicit(self):
        self.assertEqual(InputConfig().target, 'foreground')
        self.assertEqual(WineHelperConfig().helper_path, r'C:\edap\edap_input_helper.exe')
        for config, key in [(WineHelperConfig(), 'wine_path'), (WineHelperConfig(wine_path='wine'), 'bottle')]:
            with self.subTest(key=key), self.assertRaisesRegex(ConfigError, f'input.wine_helper.{key}'):
                validate_wine_helper(config, selected=True)

    def test_invalid_config_fields_are_rejected(self):
        for field, value in [('port', 0), ('port', 65536), ('launch', 'auto'), ('startup_timeout_s', 0),
                             ('request_timeout_s', float('nan')), ('max_hold_s', float('inf'))]:
            with self.subTest(field=field), self.assertRaises(ConfigError):
                validate_wine_helper(replace(CONFIG, **{field: value}), selected=True)

    def test_config_parses_windows_literal_path_and_token_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.toml'
            path.write_text("[input]\ntarget='wine_helper'\n[input.wine_helper]\nwine_path='/apps/wine'\nbottle='Test'\nhelper_path='C:\\edap\\custom.exe'\ntoken_file='private.token'\n", encoding='utf-8')
            config = load_config(path)
            self.assertEqual(config.input.wine_helper.helper_path, r'C:\edap\custom.exe')
            self.assertEqual(config.input.wine_helper.token_file, Path('private.token'))

    def test_watchdog_must_outlast_longest_market_buy_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.toml'
            path.write_text("[input.wine_helper]\nmax_hold_s = 20.0\n", encoding='utf-8')
            with self.assertRaisesRegex(ConfigError, 'max_hold_s` must be greater than `controls.market.buy_max_hold_seconds'):
                load_config(path)

    def test_shared_table_covers_normalized_aliases_and_extended_distinction(self):
        for token in KEY_ALIASES:
            resolve_scancode(normalize_internal_key_name('Key_' + token))
        self.assertEqual(resolve_scancode('right_control'), (29, True))
        self.assertEqual(resolve_scancode('left_control'), (29, False))
        self.assertEqual(resolve_scancode('numpad_enter'), (28, True))

    @unittest.skipUnless(hasattr(__import__('os'), 'O_NOFOLLOW'), 'POSIX token permissions')
    def test_token_is_persistent_private_and_rejects_unsafe_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'helper.token'
            token = load_or_create_token(path)
            self.assertEqual(len(token), 64)
            self.assertEqual(load_or_create_token(path), token)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            path.chmod(0o644)
            with self.assertRaisesRegex(RuntimeError, 'owner-only'):
                load_or_create_token(path)
            path.chmod(0o600)
            path.write_text('invalid', encoding='ascii')
            with self.assertRaisesRegex(RuntimeError, '64-character'):
                load_or_create_token(path)
