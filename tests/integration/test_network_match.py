"""Two independent peers negotiating, playing, and auditing in memory."""

import json
import queue
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

from police_thief.services.mcp_server import PeerInboxes
from police_thief.services.network_match import NetworkMatchSeriesRunner, NetworkMatchSettings
from police_thief.shared.constants import AgentRole


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


def test_two_peers_play_six_game_series_with_role_alternation(tmp_path):
    project_root = Path(__file__).parents[2]
    common = {
        "local_port": 8801,
        "game_id": "NETWORK-TEST",
        "sub_game_number": 1,
        "shared_config": project_root / "config" / "game.json",
        "shared_key": b"integration-secret",
    }
    cop_inboxes, thief_inboxes = PeerInboxes(), PeerInboxes()
    cop = NetworkMatchSeriesRunner(
        NetworkMatchSettings(
            role=AgentRole.COP,
            opponent_url="https://thief.example/mcp",
            public_url="https://cop.example/mcp",
            output_dir=tmp_path / "cop",
            team_name="alpha",
            members=("Ada", "Grace"),
            opponent_team_name="beta",
            opponent_members=("Linus", "Margaret"),
            own_cop_repo="https://example.test/a-cop",
            own_thief_repo="https://example.test/a-thief",
            opponent_cop_repo="https://example.test/b-cop",
            opponent_thief_repo="https://example.test/b-thief",
            **common,
        ),
        cop_inboxes,
        transport=MemoryTransport(cop_inboxes, thief_inboxes),
    )
    thief = NetworkMatchSeriesRunner(
        NetworkMatchSettings(
            role=AgentRole.THIEF,
            opponent_url="https://cop.example/mcp",
            public_url="https://thief.example/mcp",
            output_dir=tmp_path / "thief",
            team_name="beta",
            members=("Linus", "Margaret"),
            opponent_team_name="alpha",
            opponent_members=("Ada", "Grace"),
            own_cop_repo="https://example.test/b-cop",
            own_thief_repo="https://example.test/b-thief",
            opponent_cop_repo="https://example.test/a-cop",
            opponent_thief_repo="https://example.test/a-thief",
            **common,
        ),
        thief_inboxes,
        transport=MemoryTransport(thief_inboxes, cop_inboxes),
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        paths = list(executor.map(lambda runner: runner.run(Event()), (cop, thief)))

    results = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    assert all(result["mutual_sign_off"] for result in results)
    assert all(result["num_games"] == 6 for result in results)
    assert results[0]["sub_games"] == results[1]["sub_games"]
    assert results[0]["team_scores"] == results[1]["team_scores"]
    assert [game["roles"]["alpha"] for game in results[0]["sub_games"]] == [
        "cop",
        "thief",
        "cop",
        "thief",
        "cop",
        "thief",
    ]
    for number in range(1, 7):
        assert (tmp_path / "cop" / f"log_NETWORK-TEST_g{number:02d}.json").is_file()
        assert (tmp_path / "thief" / f"result_NETWORK-TEST_g{number:02d}.json").is_file()
    assert (tmp_path / "cop" / "declaration_NETWORK-TEST.json").is_file()

    trajectories = set()
    for number in range(1, 7):
        records = json.loads(
            (tmp_path / "cop" / f"log_NETWORK-TEST_g{number:02d}.json").read_text(
                encoding="utf-8"
            )
        )
        moves = [
            record["payload"]
            for record in records
            if record.get("payload", {}).get("move")
        ]
        trajectories.add(
            tuple((move["role"], move["move"], tuple(move["position"])) for move in moves)
        )
        latest: dict[str, tuple[int, int]] = {}
        collision_index = None
        for index, move in enumerate(moves):
            latest[move["role"]] = tuple(move["position"])
            if latest.get("police") == latest.get("thief"):
                collision_index = index
        # A collision is terminal only when it remains the final audited
        # state. Earlier crossings can be hidden by commit-reveal, and a
        # capture can also be established by the separate boxed-in rule.
        if latest.get("police") == latest.get("thief"):
            assert collision_index == len(moves) - 1, "no move may occur after capture"
    assert len(trajectories) >= 2, "sub-games must not replay one identical trajectory"
