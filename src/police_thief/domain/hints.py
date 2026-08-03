"""Natural-language verbal hints & bluff detection (Chapter 6, Sec. 6.4/4.3).

The verbal channel is the ONLY place a side may lie -- scent (Chapter 4) is
always truthful (Sec. 4.1.3). Word-limited free text, tagged with an
Intent flag (is this hint true or a deliberate lie), is generated here via
the zero-token `template` provider (Sec. 6.4.6, Table 21) -- teams may
legitimately play an entire series on this mode alone (Sec. 6.4.7). Real
LLM providers (ollama/claude_api/claude_cli) are not implemented: they
require live external services this project's test suite should not
depend on, and the rulebook presents them as options, not requirements.

detect_bluff() reproduces the worked example from Sec. 4.3.4: scent
cannot lie, so a hint's claimed direction can be cross-checked against
where the scent trail actually says the agent went.
"""

from __future__ import annotations

from dataclasses import dataclass

from police_thief.domain.board import Board, Move, MoveRejectedError, Position
from police_thief.domain.scent import ScentField

MAX_HINT_WORDS = 15  # docs/tasks.md App. F, Table 14: [hint word limit] -- this is
# the mandatory default (config/game.json's world.hint_max_words); enforce_word_limit/
# TemplateHintProvider both accept an optional override so a team that agrees on a
# different word limit via the shared config isn't stuck with this constant.

_DIRECTION_PHRASES: dict[Move, str] = {
    Move.NORTH: "I moved north.",
    Move.SOUTH: "I moved south.",
    Move.EAST: "I moved east.",
    Move.WEST: "I moved west.",
    Move.STAY: "I stayed put.",
}
_PHRASE_TO_MOVE = {phrase: move for move, phrase in _DIRECTION_PHRASES.items()}


class HintWordLimitError(ValueError):
    """Raised when a hint exceeds MAX_HINT_WORDS."""


def enforce_word_limit(text: str, max_words: int = MAX_HINT_WORDS) -> None:
    word_count = len(text.split())
    if word_count > max_words:
        raise HintWordLimitError(f"hint has {word_count} words, limit is {max_words}: {text!r}")


@dataclass(frozen=True)
class Hint:
    """A verbal claim plus its Intent flag: is it truthful, or a deliberate lie?"""

    text: str
    intent_truthful: bool


class TemplateHintProvider:
    """Zero-token, fully deterministic hint generation (Sec. 6.4.6's
    `template` mode -- the default, and the only provider implemented
    in this project).
    """

    def __init__(self, max_words: int = MAX_HINT_WORDS) -> None:
        """`max_words` should come from config/game.json's `world.hint_max_words`
        (App. F, Table 14) when a caller has it loaded; defaults to the
        mandatory baseline otherwise.
        """
        self.max_words = max_words

    def generate(self, true_move: Move, *, tell_truth: bool, false_move: Move = Move.STAY) -> Hint:
        """`false_move` lets the caller choose what lie to tell; defaults
        to claiming STAY, a plausible generic deflection.
        """
        claimed_move = true_move if tell_truth else false_move
        text = _DIRECTION_PHRASES[claimed_move]
        enforce_word_limit(text, self.max_words)
        return Hint(text=text, intent_truthful=tell_truth)


def parse_claimed_direction(hint: Hint) -> Move | None:
    """None if the text doesn't match any known template phrase."""
    return _PHRASE_TO_MOVE.get(hint.text)


def detect_bluff(
    hint: Hint, prev_position: Position, scent_field: ScentField, board: Board
) -> bool:
    """True if the hint's claimed direction contradicts the real scent trail.

    Sec. 4.3.5: scent cannot be forged, so a mismatch exposes a *verbal*
    lie, not a false trail. An unparseable hint or a claim with no scent
    evidence yet cannot be assessed and is not flagged (absence of proof
    is not proof of a lie).

    Scope limitation: this compares neighbor intensities in the scent
    field *as given* -- most reliable when called right after the turn's
    own emission, assessing that single most-recent move. Scent decays
    slowly by design (Sec. 4.2.4, rho=0.10), so several turns of
    accumulated history can persist simultaneously; over a long,
    curving path this can dilute or confuse a single-step comparison
    (verified empirically while building this function). A
    recency-weighted or emission-delta-based detector would be a
    natural refinement, out of scope for this chapter.
    """
    claimed_move = parse_claimed_direction(hint)
    if claimed_move is None:
        return False
    try:
        claimed_position = board.apply_move(prev_position, claimed_move)
    except MoveRejectedError:
        return True  # claiming a destination that isn't even legal is itself suspicious

    neighbors = board.neighbors(prev_position)
    if not neighbors:
        return False
    actual_best = max(neighbors, key=scent_field.intensity_at)
    actual_best_intensity = scent_field.intensity_at(actual_best)
    if actual_best_intensity <= 0:
        return False  # no scent evidence yet

    claimed_intensity = scent_field.intensity_at(claimed_position)
    return claimed_position != actual_best and claimed_intensity < actual_best_intensity * 0.5
