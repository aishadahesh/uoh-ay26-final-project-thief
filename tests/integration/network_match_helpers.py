"""Shared doubles for the cross-peer integration tests: an in-memory
transport and a two-team config builder.

Extracted when `test_network_match.py` was split."""

import json
import queue

from police_thief.services.mcp_server import PeerInboxes


class MemoryTransport:
    def __init__(self, own: PeerInboxes, peer: PeerInboxes) -> None:
        self.own = own
        self.peer = peer

    def exchange_agreement(self, message, timeout):
        self.peer.agreements.put(message)
        return self.own.agreements.get(timeout=timeout)

    def send_turn(self, message, _timeout):
        self.peer.turns.put(message)

    def receive_turn(self, timeout):
        return self.own.turns.get(timeout=timeout)

    def exchange_audit(self, payload, timeout):
        self.peer.audits.put(payload)
        return self.own.audits.get(timeout=timeout)

    def send_control(self, message, timeout=2.0):
        self.peer.controls.put(message)

    def poll_control(self):
        try:
            return self.own.controls.get_nowait()
        except queue.Empty:
            return None


def _team_config(tmp_path, source, name, group_id, members, repos, num_games=6):
    target = tmp_path / name / "game.json"
    target.parent.mkdir(parents=True)
    game = json.loads(source.read_text(encoding="utf-8"))
    game["network_and_league"]["num_games"] = num_games
    target.write_text(json.dumps(game), encoding="utf-8")
    timeout = game["network_and_league"]["response_timeout_sec"]
    target.with_suffix(".toml").write_text(
        f'version = "1.00"\n[game]\ngroup_name = "{name}"\n'
        f'group_id = "{group_id}"\nsub_game_number = 1\n'
        f'members = {json.dumps(list(members))}\nrepos = {json.dumps(repos)}\n'
        f'[network]\nmy_port = 8801\nopponent_url = "https://peer.example/mcp"\n'
        f'turn_timeout_seconds = {timeout}\n',
        encoding="utf-8",
    )
    text = target.with_suffix(".toml").read_text(encoding="utf-8")
    text = text.replace('"cop":', 'cop =').replace('"thief":', 'thief =')
    target.with_suffix(".toml").write_text(text, encoding="utf-8")
    return target
