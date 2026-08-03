"""Integration test: the real strategy pipeline under true partial observability.

Unlike domain/simulation.py's Chapter 3/4 placeholder policies (which
"cheat" by taking the opponent's raw position directly), this test drives
two ManhattanHeuristicBrain instances using ONLY each side's own belief
map -- itself fed only by that side's own reading of the opponent's scent
trail. Neither brain's _decide_move call ever receives the opponent's true
Position anywhere in this test -- that variable is only ever used by the
test harness itself to check for capture, exactly the way no external
judge exists in the real rulebook (docs/tasks.md Sec. 3.1) but a human
observer can still watch the board.
"""

from police_thief.domain.belief import BeliefMap
from police_thief.domain.board import Board, BoardConfig, Position
from police_thief.domain.capture import check_capture
from police_thief.domain.heuristics import manhattan_distance
from police_thief.domain.scent import ScentConfig, ScentField
from police_thief.domain.strategy.manhattan_brain import ManhattanHeuristicBrain
from police_thief.shared.constants import AgentRole

MAX_TURNS = 35


def _run_partial_observability_match(cop_start: Position, thief_start: Position):
    """Returns (captured: bool, turns: int, final_cop_belief_peak: Position,
    final_cop_pos: Position, final_thief_pos: Position).
    """
    board = Board(BoardConfig(grid_size=7, max_barriers=14))
    cop_pos, thief_pos = cop_start, thief_start
    cop_scent, thief_scent = ScentField(7, ScentConfig()), ScentField(7, ScentConfig())
    cop_belief, thief_belief = BeliefMap(board), BeliefMap(board)
    cop_brain = ManhattanHeuristicBrain(AgentRole.COP)
    thief_brain = ManhattanHeuristicBrain(AgentRole.THIEF)

    for turn in range(1, MAX_TURNS + 1):
        cop_belief.update_from_scent(thief_scent)
        cop_pos = board.apply_move(cop_pos, cop_brain._decide_move(board, cop_pos, cop_belief))
        cop_scent.decay()
        cop_scent.emit(cop_pos)
        if check_capture(cop_pos, thief_pos):
            return True, turn, cop_belief.arg_max(), cop_pos, thief_pos

        thief_belief.update_from_scent(cop_scent)
        thief_pos = board.apply_move(
            thief_pos, thief_brain._decide_move(board, thief_pos, thief_belief)
        )
        thief_scent.decay()
        thief_scent.emit(thief_pos)
        if check_capture(cop_pos, thief_pos):
            return True, turn, cop_belief.arg_max(), cop_pos, thief_pos

    return False, MAX_TURNS, cop_belief.arg_max(), cop_pos, thief_pos


def test_partial_observability_pipeline_runs_to_completion_with_no_crash():
    captured, turns, _, _, _ = _run_partial_observability_match(Position(0, 0), Position(6, 6))
    assert turns <= MAX_TURNS
    assert isinstance(captured, bool)


def test_cop_belief_converges_toward_the_true_thief_position_over_time():
    """The cop's belief peak should end up much closer to the thief's real
    final position than a uniform-random guess would be -- proving the
    scent-fed belief map, not luck, is doing the work.
    """
    captured, _, cop_belief_peak, _, thief_pos = _run_partial_observability_match(
        Position(0, 0), Position(6, 6)
    )
    distance = manhattan_distance(cop_belief_peak, thief_pos)
    assert distance <= 2  # tight convergence; captured runs land exactly on it


def test_cop_eventually_captures_a_naively_fleeing_thief_using_belief_alone():
    """Not guaranteed by architecture alone, but true for this heuristic on
    a 7x7 board within the mandatory max-moves budget -- a meaningful
    behavioral proof, not just a plumbing check.
    """
    captured, turns, _, cop_pos, thief_pos = _run_partial_observability_match(
        Position(0, 0), Position(6, 6)
    )
    assert captured is True
    assert cop_pos == thief_pos
    assert turns <= MAX_TURNS
