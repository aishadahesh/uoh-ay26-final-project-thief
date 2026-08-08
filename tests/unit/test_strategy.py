"""Unit tests for BrainBase/ManhattanHeuristicBrain and config-driven loading."""

import pytest

from police_thief.domain.belief import BeliefMap
from police_thief.domain.board import Board, BoardConfig, Position
from police_thief.domain.heuristics import manhattan_distance
from police_thief.domain.scent import ScentConfig, ScentField
from police_thief.domain.strategy.brain_base import BrainBase
from police_thief.domain.strategy.manhattan_brain import ManhattanHeuristicBrain
from police_thief.shared.config import ConfigError, load_strategy_class
from police_thief.shared.constants import AgentRole


def test_brain_base_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BrainBase()  # type: ignore[abstract]


def test_brain_base_default_pick_move_is_none():
    class MinimalBrain(BrainBase):
        def _decide_move(self, board, own, belief):
            return None

    brain = MinimalBrain()
    assert brain._pick_move(None, None, None) is None


class DummyCustomBrain(BrainBase):
    """A minimal, distinct BrainBase subclass used only to prove
    load_strategy_class actually reads and imports the configured dotted
    path, rather than always falling back to the default.
    """

    def _decide_move(self, board, own, belief):
        return None


def _belief_peaked_at(board: Board, peak: Position) -> BeliefMap:
    scent = ScentField(grid_size=board.config.grid_size, config=ScentConfig())
    scent.emit(peak)
    belief = BeliefMap(board)
    belief.update_from_scent(scent)
    return belief


def test_cop_brain_moves_toward_the_belief_peak():
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    belief = _belief_peaked_at(board, Position(5, 5))
    brain = ManhattanHeuristicBrain(role=AgentRole.COP)
    move = brain._decide_move(board, Position(0, 0), belief)
    new_pos = board.apply_move(Position(0, 0), move)
    assert manhattan_distance(new_pos, Position(5, 5)) < manhattan_distance(
        Position(0, 0), Position(5, 5)
    )


def test_thief_brain_moves_away_from_the_belief_peak():
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    belief = _belief_peaked_at(board, Position(5, 5))
    brain = ManhattanHeuristicBrain(role=AgentRole.THIEF)
    move = brain._decide_move(board, Position(4, 4), belief)
    new_pos = board.apply_move(Position(4, 4), move)
    assert manhattan_distance(new_pos, Position(5, 5)) > manhattan_distance(
        Position(4, 4), Position(5, 5)
    )


def test_cop_brain_conserves_barriers_in_open_space():
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    belief = _belief_peaked_at(board, Position(5, 5))
    brain = ManhattanHeuristicBrain(role=AgentRole.COP)
    assert brain._pick_move(board, Position(0, 0), belief) is None


def test_cop_brain_uses_a_barrier_to_seal_a_real_chokepoint():
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    board.place_barrier(Position(0, 2), Position(0, 2))
    board.place_barrier(Position(2, 0), Position(2, 0))
    belief = _belief_peaked_at(board, Position(0, 0))
    brain = ManhattanHeuristicBrain(role=AgentRole.COP)
    assert brain._pick_move(board, Position(1, 1), belief) == Position(1, 1)


def test_cop_brain_declines_to_place_a_barrier_once_budget_exhausted():
    board = Board(BoardConfig(grid_size=7, max_barriers=0))
    belief = _belief_peaked_at(board, Position(5, 5))
    brain = ManhattanHeuristicBrain(role=AgentRole.COP)
    assert brain._pick_move(board, Position(0, 0), belief) is None


def test_cop_brain_never_uses_a_barrier_that_removes_its_last_exit():
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    board.apply_declared_barrier(Position(0, 4))
    board.apply_declared_barrier(Position(1, 3))
    belief = _belief_peaked_at(board, Position(0, 2))
    brain = ManhattanHeuristicBrain(role=AgentRole.COP)

    assert brain._pick_move(board, Position(0, 3), belief) is None


def test_thief_brain_never_places_a_barrier():
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    belief = _belief_peaked_at(board, Position(5, 5))
    brain = ManhattanHeuristicBrain(role=AgentRole.THIEF)
    assert brain._pick_move(board, Position(4, 4), belief) is None


def test_cop_brain_pick_move_handles_a_cell_with_no_orthogonal_neighbors():
    """Defensive-only branch: unreachable via the config loader (which
    enforces grid_size >= 7), but a 1x1 board constructed directly bypasses
    that floor -- proving _pick_move degrades to None rather than crashing.
    """
    board = Board(BoardConfig(grid_size=1, max_barriers=14))
    belief = _belief_peaked_at(board, Position(0, 0))
    brain = ManhattanHeuristicBrain(role=AgentRole.COP)
    assert brain._pick_move(board, Position(0, 0), belief) is None


def test_load_strategy_class_raises_on_missing_config_file(tmp_path):
    with pytest.raises(ConfigError, match="missing per-peer config file"):
        load_strategy_class(AgentRole.COP, tmp_path)


def test_load_strategy_class_defaults_to_manhattan_brain_when_unset(tmp_path):
    _write_toml(tmp_path, AgentRole.COP, "[network]\nmy_port=1\nopponent_url='x'\n")
    cls = load_strategy_class(AgentRole.COP, tmp_path)
    assert cls is ManhattanHeuristicBrain


def test_load_strategy_class_loads_a_custom_class_distinct_from_the_default(tmp_path):
    """Points at DummyCustomBrain (this test module), not ManhattanHeuristicBrain
    -- proving the config value is actually read, not just falling through to
    the same default by coincidence.
    """
    _write_toml(
        tmp_path,
        AgentRole.COP,
        "[strategy]\ncop_class = 'tests.unit.test_strategy:DummyCustomBrain'\n",
    )
    cls = load_strategy_class(AgentRole.COP, tmp_path)
    assert cls is DummyCustomBrain
    assert cls is not ManhattanHeuristicBrain


def test_load_strategy_class_never_reads_the_other_roles_key(tmp_path):
    """Only cop_class is read for role=COP, even if thief_class is also present."""
    _write_toml(
        tmp_path,
        AgentRole.COP,
        "[strategy]\nthief_class = 'nonexistent.module:Nope'\n",
    )
    cls = load_strategy_class(AgentRole.COP, tmp_path)
    assert cls is ManhattanHeuristicBrain  # falls back; thief_class is irrelevant to the cop


def test_load_strategy_class_rejects_malformed_dotted_path(tmp_path):
    _write_toml(tmp_path, AgentRole.COP, "[strategy]\ncop_class = 'not-a-valid-path'\n")
    with pytest.raises(ConfigError, match="module:Class"):
        load_strategy_class(AgentRole.COP, tmp_path)


def test_load_strategy_class_rejects_a_class_that_is_not_a_brain(tmp_path):
    _write_toml(
        tmp_path,
        AgentRole.COP,
        "[strategy]\ncop_class = 'police_thief.domain.board:Position'\n",
    )
    with pytest.raises(ConfigError, match="not a BrainBase subclass"):
        load_strategy_class(AgentRole.COP, tmp_path)


def _write_toml(tmp_path, role: AgentRole, content: str) -> None:
    role_dir = tmp_path / role.value
    role_dir.mkdir(parents=True, exist_ok=True)
    (role_dir / "game.toml").write_text(content, encoding="utf-8")


def test_thief_breaks_equal_distance_ties_toward_more_future_exits():
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    # From (0,1), WEST and EAST are equally distant from a threat at (1,1),
    # but WEST is a corner with fewer future exits.
    belief = _belief_peaked_at(board, Position(1, 1))
    brain = ManhattanHeuristicBrain(role=AgentRole.THIEF)
    assert brain._decide_move(board, Position(0, 1), belief).name == "EAST"
