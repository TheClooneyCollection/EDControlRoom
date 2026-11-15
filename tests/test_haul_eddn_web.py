"""Drive the shipped haul script through a plain DOM and HTTP/socket boundaries."""
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node is required for web behavior checks")
class HaulEddnWebTests(unittest.TestCase):
    def test_search_and_recommendations_keep_route_choice_with_the_operator(self):
        result = subprocess.run(
            [shutil.which("node"), "-e", WEB_FLOW],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


WEB_FLOW = r'''
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('web/haul-v1.html', 'utf8');
function element() {
  return {value: '', textContent: '', innerHTML: '', dataset: {}, options: [], handlers: {},
    classList: {toggle() {}}, setAttribute() {}, focus() {}, select() {},
    addEventListener(type, handler) { this.handlers[type] = handler; },
    querySelectorAll() { return []; }, querySelector() { return null; },
    add(option) { this.options.push(option); }};
}
const elements = Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(m => [m[1], element()]));
const button = element();
elements['node-picker'] = element();
elements['node-picker'].dataset.state = 'ok';
elements['hub-chip'].hidden = true;
const observers = [], intervals = [];
class Observer {
  constructor(callback) { this.callback = callback; observers.push(this); }
  observe() {}
}
let now = 1800000000000;
class Clock extends Date { static now() { return now; } }

const get = id => { assert.ok(elements[id], `missing HTML element ${id}`); return elements[id]; };
const document = {getElementById: get, activeElement: null,
  querySelector(selector) {
    if (selector === '#search-form .btn.primary') return button;
    if (selector === '.history-details') return null;
    throw Error(`unexpected selector ${selector}`);
  }, querySelectorAll() { return []; }, execCommand(action) { assert.equal(action, 'copy'); return true; }};
const sent = [], requests = [];
let socket, commandFailure = '', onCommand = () => {};
class Socket {
  static OPEN = 1;
  constructor() { socket = this; this.readyState = 1; this.handlers = {}; }
  addEventListener(type, handler) { this.handlers[type] = handler; }
  send(raw) {
    const message = JSON.parse(raw); sent.push(message);
    queueMicrotask(() => {
      if (!commandFailure) onCommand(message);
      this.message(commandFailure ? 'response.error' : 'response.success',
        commandFailure ? {error_message: commandFailure} : {}, message.message_id);
    });
  }
  message(message_type, payload, correlation_message_id) {
    this.handlers.message({data: JSON.stringify({message_type, payload, correlation_message_id})});
  }
}
const window = {location: new URL('http://test/haul?access_token=test&node=forge'),
  EDCR_WEB_CONFIG: {webDefaults: {maxRouteDistanceLy: '999', maxPriceAgeHours: '48', recommendMaxRouteLy: 140}},
  localStorage: {getItem() { return null; }},
  EDCRNode: {id: () => 'forge', addTo: params => params.set('node', 'forge')},
  setTimeout: () => 1, setInterval: callback => intervals.push(callback), clearTimeout() {}, clearInterval() {}, dispatchEvent() {},
  history: {replaceState() { throw Error('unexpected navigation'); }}};
const trade = {from_station: 'Alpha Port', from_system: 'Alpha', to_station: 'Beta Port', to_system: 'Beta',
  source_buy_commodity: 'Gold', target_buy_commodity: 'Silver',
  profit_per_trip: '10,000,000 Cr', profit_per_hour: '60,000,000 Cr', route_distance: '25 Ly'};
const row = {station_1: {station: 'Alpha Port', system: 'Alpha', dist_ls: 200, ly_from_system: 15},
  station_2: {station: 'Beta Port', system: 'Beta', dist_ls: 300, ly_from_system: 40},
  outbound: {name: 'Gold', supply: 1000, demand: 2000, buy_price: 100, sell_price: 200},
  inbound: {name: 'Silver'}, trade_route: trade, distance_ly: 25, jumps: 2,
  profit_per_trip: 10000000, profit_per_hour: 60000000, trip_s: 600};
const normal = {routes: [row, {...row, trade_route: null, outbound: {...row.outbound, name: 'unknown-key'}}],
  markets_considered: 7, markets_left_out: {coordinates: 3, age: 2, pad: 0, other_reason: 1},
  query: {filters: {max_age_s: 172800}}, hub: 'hub'};
let reply = normal, failure = '', blocked;
async function fetch(url, options) {
  if (url.pathname === '/api/haul-stats') return {ok: true, json: async () => ({runs: {}})};
  assert.equal(url.pathname, '/api/eddn-routes', 'EDDN results must not request /api/haul-trips');
  requests.push({url, options});
  if (blocked) await blocked;
  if (failure === 'offline') throw Error('offline');
  return {ok: !failure, status: 503, json: async () => failure ? {detail: failure} : reply};
}
vm.runInNewContext(fs.readFileSync('web/haul-ui.js', 'utf8'),
  {window, document, URL, URLSearchParams, WebSocket: Socket, fetch,
   navigator: {}, MutationObserver: Observer, Date: Clock, CustomEvent: function() {}, Option: function(text, value) { this.value = value; }, console});
const click = id => get(id).handlers.click({});
const select = index => get('route-rows').handlers.click({target: {closest: () => ({dataset: {index}})}});
const search = () => get('search-form').handlers.submit({preventDefault() {}});
(async () => {
  socket.message('event.connection_ready', {client_role: 'active_operator'});
  assert.equal(get('route-distance').value, '140');
  assert.equal(get('route-distance').placeholder, '140');
  assert.equal(get('capacity').value, '');
  assert.match(get('max-age').placeholder, /48/);
  await search();
  const query = requests[0].url.searchParams;
  assert.equal(query.get('view'), 'global'); assert.equal(query.get('ship_range'), '1');
  assert.equal(query.get('node'), 'forge'); assert.equal(query.get('access_token'), 'test');
  assert.equal(query.get('max_route_ly'), '140');
  for (const key of ['capacity', 'system', 'surface', 'min_supply', 'max_age_hours', 'max_station_distance_ls'])
    assert.equal(query.get(key), '', `${key} delegates blank defaults`);
  assert.equal(query.has('laden_jump_range_ly'), false);
  assert.equal(sent.length, 0, 'search must never select automatically');
  assert.equal(get('start-haul').disabled, true);
  assert.match(get('route-rows').innerHTML, /commodity name unknown/);
  assert.match(get('route-rows').innerHTML, /EDCR: 60.0m Cr\/h 10 m\/trip/);
  assert.match(get('route-rows').innerHTML, /15 Ly away/);
  assert.match(get('result-count').textContent, /3 left out: missing coordinates/);
  assert.match(get('result-count').textContent, /2 left out: older than 48 h/);
  assert.match(get('result-count').textContent, /1 left out: other_reason/);
  select('2'); assert.equal(sent.length, 0, 'unknown names cannot select');
  select('1');
  assert.equal(sent[0].message_type, 'command.select_trade_route');
  assert.equal(sent[0].payload.route.source_buy_commodity, 'Gold');
  assert.equal(get('travel-system').value, 'Alpha');
  await click('copy-route');
  const copied = JSON.parse(get('route-transfer-text').value);
  assert.equal(copied.from_station, 'Alpha Port'); assert.equal(copied.route_distance, '25 Ly');
  assert.equal(get('start-haul').disabled, false);
  get('origin').value = 'Sol'; get('capacity').value = '720';
  get('route-distance').value = ''; get('station-distance').value = '1000';
  get('surface-stations').value = 'yes_with_odyssey'; get('max-age').value = '24';
  get('min-supply').value = '800';
  reply = {...normal, routes: []};
  await search();
  const custom = requests.at(-1).url.searchParams;
  for (const [key, value] of Object.entries({system: 'Sol', capacity: '720', max_route_ly: '140',
    surface: 'yes_with_odyssey', max_age_hours: '24', min_supply: '800', max_station_distance_ls: '1000'}))
    assert.equal(custom.get(key), value);
  assert.equal(sent.length, 1); assert.match(get('route-rows').innerHTML, /No EDDN routes found/);
  await click('copy-route'); assert.equal(JSON.parse(get('route-transfer-text').value).from_station, 'Alpha Port');
  assert.equal(get('start-haul').disabled, false, 'selected route survives empty search');
  for (const error of ['offline', 'store unavailable']) {
    failure = error; await search();
    assert.match(get('route-rows').innerHTML, new RegExp(`Search failed: ${error}`));
    assert.equal(button.disabled, false);
    assert.equal(sent.length, 1, 'errors do not change selection');
  }
  failure = ''; reply = normal;
  let release; blocked = new Promise(resolve => { release = resolve; });
  const pending = search();
  assert.equal(button.disabled, true); assert.equal(get('route-rows').inert, true);
  release(); await pending; blocked = null;
  assert.equal(button.disabled, false); assert.equal(get('route-rows').inert, false);
  assert.match(get('route-rows').innerHTML, /commodity name unknown/);
  // The selected route's hydrate must retain the EDDN estimate and avoid another trip request.
  socket.message('control_room.hydrate', {selected_trade_route: trade, ship: {}, haul_session: {}});
  await Promise.resolve();
  await click('copy-route'); assert.equal(JSON.parse(get('route-transfer-text').value).from_station, 'Alpha Port');
  assert.equal(sent.length, 1);
  // Existing actions still use the explicitly selected route, only at the fake socket boundary.
  click('set-destination'); click('start-travel'); click('start-haul'); click('track-haul');
  assert.equal(sent.at(-4).message_type, 'command.dispatch_destination');
  assert.equal(sent.at(-4).payload.destination, 'Alpha');
  assert.equal(sent.at(-3).message_type, 'command.dispatch_travel');
  assert.equal(sent.at(-3).payload.station, 'Alpha Port');
  assert.equal(sent.at(-2).message_type, 'command.dispatch_haul_loop');
  assert.equal(sent.at(-2).payload.trade_route.source_buy_commodity, 'Gold');
  assert.equal(sent.at(-1).payload.params.mode, 'track');
  assert.equal(get('origin').value, 'Sol', 'hydrate preserves edited fields');
  assert.equal(get('capacity').value, '720');
  click('reset-search'); assert.equal(get('origin').value, ''); assert.equal(get('route-distance').value, '140');

  const recommendation = {...row, key: 'key<one>', station_1: {...row.station_1, age_s: 60},
    station_2: {...row.station_2, age_s: 120}};
  const betterTrade = {...trade, from_station: 'Gamma <Port>', from_system: 'Gamma'};
  const second = {...recommendation, key: 'second', trade_route: betterTrade,
    station_1: {...recommendation.station_1, station: 'Gamma <Port>', system: 'Gamma'},
    profit_per_hour: 80000000};
  const recs = {routes: [recommendation, second], below_threshold: 15, name_unknown: 2, dismissed: 1,
    baseline_cr_h: 40000000, baseline_source: 'search', baseline_missing: [],
    generated_at: now / 1000 - 180, searched_limit: 200};
  const hydrate = recommendations => socket.message('control_room.hydrate', {
    selected_trade_route: trade, route_recommendations: recommendations, ship: {}, haul_session: {}});
  const act = (action, key) => get('recommendation-rows').handlers.click({target: {
    closest: () => ({dataset: {recommendAction: action, recommendKey: key}})}});
  hydrate(null); assert.equal(get('route-recommendations').hidden, true);
  const beforeRecommendations = sent.length;
  hydrate(recs);
  assert.equal(get('route-recommendations').hidden, false);
  assert.equal(sent.length, beforeRecommendations, 'new recommendations never select or start');
  assert.match(get('recommendation-rows').innerHTML, /Gamma &lt;Port&gt;/);
  assert.match(get('recommendation-rows').innerHTML, /Gold \/ Silver/);
  assert.match(get('recommendation-rows').innerHTML, /EDCR: 60.0m Cr\/h · \+50% \/ \+20.0 m\/h/);
  assert.match(get('recommendation-rows').innerHTML, /2 jumps · 25 Ly/);
  assert.match(get('recommendation-rows').innerHTML, /Alpha Port 4 min ago; Beta Port 5 min ago/);
  assert.match(get('recommendation-rows').innerHTML, /data-recommend-key="key&lt;one&gt;"/);
  assert.match(get('recommendations-footer').textContent, /15 below threshold of the top 200, 2 names unknown, 1 dismissed/);
  assert.match(get('recommendations-footer').textContent, /EDDN, checked 3 min ago/);
  now += 60000; intervals.forEach(callback => callback());
  assert.match(get('recommendations-footer').textContent, /checked 4 min ago/);
  hydrate({...recs, baseline_cr_h: null, baseline_missing: ['station coordinates', 'selected route prices']});
  assert.match(get('recommendations-baseline').textContent, /Selected route not priced: station coordinates, selected route prices/);
  assert.doesNotMatch(get('recommendation-rows').innerHTML, /\+50%/);
  hydrate({...recs, baseline_cr_h: 0});
  assert.match(get('recommendation-rows').innerHTML, /baseline 0 Cr\/h/);
  assert.doesNotMatch(get('recommendation-rows').innerHTML, /Infinity/);
  hydrate({...recs, routes: [], dismissed: 3});
  assert.equal(get('route-recommendations').hidden, false);
  assert.match(get('recommendations-empty').textContent, /No better route \(15 below threshold\)/);
  assert.match(get('recommendations-footer').textContent, /3 dismissed/);
  hydrate({...recs, routes: [], dismissed: 0});
  assert.equal(get('route-recommendations').hidden, false, 'checked empty differs from never checked');

  hydrate(recs);
  get('node-picker').dataset.state = 'down'; observers.forEach(observer => observer.callback());
  assert.match(get('recommendations-connection').textContent, /Hub unreachable/);
  assert.match(get('recommendation-rows').innerHTML, /Gamma &lt;Port&gt;/);
  assert.match(get('recommendation-rows').innerHTML, / disabled/);
  await act('select', 'second'); assert.equal(sent.length, beforeRecommendations);
  get('node-picker').dataset.state = 'ok'; observers.forEach(observer => observer.callback());
  assert.equal(get('recommendations-connection').textContent, '');
  // Peer-local pages receive link state from the existing hub chip instead of the node picker.
  get('hub-chip').hidden = false; get('hub-chip').dataset.state = 'down';
  observers.forEach(observer => observer.callback());
  assert.match(get('recommendations-connection').textContent, /Hub unreachable/);
  get('hub-chip').dataset.state = 'ok'; observers.forEach(observer => observer.callback());
  assert.equal(get('recommendations-connection').textContent, '');
  socket.readyState = 3; intervals.forEach(callback => callback());
  assert.match(get('recommendations-connection').textContent, /Hub unreachable/);
  socket.readyState = 1;
  socket.message('event.connection_ready', {client_role: 'observer'});
  await act('dismiss', 'second'); assert.equal(sent.length, beforeRecommendations);
  socket.message('event.connection_ready', {client_role: 'active_operator'});

  commandFailure = 'Node unreachable';
  await act('dismiss', 'second');
  assert.match(get('recommendations-message').textContent, /Node unreachable/);
  assert.match(get('recommendation-rows').innerHTML, /Gamma &lt;Port&gt;/);
  commandFailure = '';
  onCommand = message => {
    if (message.message_type === 'command.dismiss_route_recommendation')
      hydrate({...recs, routes: [recommendation], dismissed: 2});
  };
  await act('dismiss', 'second');
  assert.equal(sent.at(-1).message_type, 'command.dismiss_route_recommendation');
  assert.equal(sent.at(-1).payload.key, 'second');
  assert.doesNotMatch(get('recommendation-rows').innerHTML, /Gamma &lt;Port&gt;/);
  assert.match(get('recommendations-footer').textContent, /2 dismissed/);

  hydrate(recs);
  commandFailure = 'Selection refused';
  await act('select', 'second');
  assert.match(get('recommendations-message').textContent, /Selection refused/);
  assert.match(get('selected-title').textContent, /Alpha Port/);
  commandFailure = '';
  onCommand = message => {
    if (message.message_type === 'command.select_trade_route') socket.message('control_room.hydrate', {
      selected_trade_route: betterTrade, route_recommendations: null, ship: {}, haul_session: {}});
  };
  const beforeSelect = sent.length;
  await act('select', 'second');
  assert.equal(sent.length, beforeSelect + 1, 'Select sends no travel or start command');
  assert.equal(sent.at(-1).message_type, 'command.select_trade_route');
  assert.deepEqual(sent.at(-1).payload.route, betterTrade);
  assert.equal(get('travel-system').value, 'Gamma');
  assert.equal(get('travel-station').value, 'Gamma <Port>');
  assert.match(get('selected-title').textContent, /Gamma/);
  assert.equal(get('route-recommendations').hidden, true, 'selection clears stale recommendations');
  await click('copy-route'); assert.equal(JSON.parse(get('route-transfer-text').value).from_system, 'Gamma');

})().catch(error => { console.error(error); process.exitCode = 1; });
'''
