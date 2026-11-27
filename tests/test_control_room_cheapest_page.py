from pathlib import Path
import shutil
import subprocess
import unittest

from edcr.control_room.server.app import build_observer_server_app
from edcr.control_room.server.auth import SharedAccessTokenAuth
from edcr.control_room.server.broker import InMemoryObserverSessionBroker
from tests.shared_loop import TestClient
from tests.test_control_room_server import _base_data_read_model


class CheapestPageTests(unittest.TestCase):
    def test_open_page_and_load_its_assets_from_navigation(self):
        app = build_observer_server_app(
            data_provider=_base_data_read_model,
            command_handler=None,
            broker=InMemoryObserverSessionBroker(),
            auth=SharedAccessTokenAuth("secret-token"),
        )
        with TestClient(app) as client:
            page = client.get("/cheapest?node=peer")
            script = client.get("/assets/cheapest.js")
            nav = client.get("/assets/nav.js")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.headers["cache-control"], "no-store")
        self.assertIn('src="/assets/cheapest.js"', page.text)
        self.assertIn('id="cheapest-form"', page.text)
        self.assertEqual(script.status_code, 200)
        self.assertIn("text/javascript", script.headers["content-type"])
        self.assertEqual(script.headers["cache-control"], "no-store")
        self.assertIn('href: "/cheapest", label: "Cheapest"', nav.text)

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for the browser fixture")
    def test_search_defaults_filters_and_partial_failure_with_fixture(self):
        # Exercise the actual page script with a minimal DOM and a fixture fetch boundary.
        script = r'''
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const elements = new Map();
const get = (id) => {
  if (!elements.has(id)) elements.set(id, {value: "", checked: false, textContent: "", innerHTML: "", addEventListener(type, fn) {this[type] = fn;}});
  return elements.get(id);
};
let chosen = "saved-peer";
const requests = [];
const fixture = {
  name: "Tritium", commodity: "tritium",
  query: {reference_system: "Adach", radius_ly: 100, min_supply: 720, pad: "L", max_age_hours: 168, include_carriers: false, use_spansh: true},
  offers: [{buy_price: 10, supply: 1000, station_name: '<img src=x onerror="alert(1)">', system_name: "A&B", is_carrier: true, suspect_price: true, distance_ly: 0, dist_ls: null, max_pad: "", age_s: 90000, source: "hub"}],
  hidden: {carrier: 12, supply: 20, pad: 2, radius: 3, age: 4},
  spansh: {asked: true, count: 3366, error: ""}
};
let reply = fixture;
let ok = true;
const context = vm.createContext({URL, URLSearchParams, document: {getElementById: get},
  window: {location: {search: "?node=explicit-peer", origin: "http://fixture", host: "fixture"}, localStorage: {getItem() {return "";}, setItem() {}}, EDCRNode: {choose(id) {chosen = id;}, addTo(p) {p.set("node", chosen);}}},
  fetch: async (url) => {requests.push(url); return {ok, status: 502, json: async () => structuredClone(reply)};}
});
vm.runInContext(fs.readFileSync("web/cheapest.js", "utf8"), context);
const settle = () => new Promise(resolve => setImmediate(resolve));
(async () => {
  await settle();
  assert.deepEqual([...requests[0].searchParams.keys()].sort(), ["commodity", "node"]);
  assert.equal(requests[0].searchParams.get("node"), "explicit-peer");
  assert.equal(get("system").value, "Adach");
  assert.equal(get("min_supply").value, 720);
  assert.equal(get("spansh").checked, true);
  assert.match(get("results").innerHTML, /&lt;img/);
  assert.doesNotMatch(get("results").innerHTML, /<img/);
  assert.match(get("results").innerHTML, /A&amp;B/);
  assert.match(get("results").innerHTML, /old-age/);
  assert.match(get("results").innerHTML, /carrier-badge/);
  assert.match(get("results").innerHTML, /<s title="price looks fake">/);
  assert.match(get("hidden-counts").textContent, /12 carriers hidden/);
  for (const reason of ["supply", "pad", "radius", "age"]) assert.match(get("hidden-counts").textContent, new RegExp("hidden by " + reason));
  assert.match(get("spansh-status").textContent, /filtered server-side, 3.?366 matches/);
  // DOM inputs stringify assignments; the minimal fixture does so here before a submit.
  for (const element of elements.values()) element.value = String(element.value);
  get("radius_ly").value = "";
  get("system").value = "";
  get("carriers").checked = true;
  reply.spansh.error = "Spansh timed out <retry>";
  reply.query.reference_system = "";
  get("cheapest-form").submit({preventDefault() {}});
  await settle();
  assert.equal(requests[1].searchParams.get("radius_ly"), "");
  assert.equal(requests[1].searchParams.get("carriers"), "1");
  assert.equal(get("radius_ly").value, "");
  assert.doesNotMatch(get("results").innerHTML, /Distance \(ly\)/);
  assert.match(get("results").innerHTML, /carrier-badge/);
  assert.equal(get("spansh-status").textContent, "Spansh: Spansh timed out <retry>");
  ok = false;
  reply = {detail: "Peer offline"};
  get("cheapest-form").submit({preventDefault() {}});
  await settle();
  assert.equal(get("results").innerHTML, "");
  assert.match(get("results-status").textContent, /Peer offline/);
  assert.equal(get("search").disabled, false);
  ok = true;
  reply = {...fixture, offers: [], hidden: {}, spansh: {asked: false}};
  get("cheapest-form").submit({preventDefault() {}});
  await settle();
  assert.match(get("results-status").textContent, /No matching markets/);
  assert.equal(get("spansh-status").textContent, "Spansh: not requested.");
})().catch(error => {console.error(error); process.exitCode = 1;});
'''
        result = subprocess.run(
            [shutil.which("node"), "-e", script],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
