from types import SimpleNamespace

from police_thief.domain.board import Move, Position
from police_thief.services.gemini_agent import GeminiAgentAdvisor, TacticalContext
from police_thief.shared.constants import AgentRole


class _FakeModels:
    def __init__(self, text: str = "EAST|Closing on the strongest scent signal.", error=None, usage=None):
        self.text = text
        self.error = error
        self.usage = usage
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.text, usage_metadata=self.usage)


def _context() -> TacticalContext:
    return TacticalContext(
        role=AgentRole.COP,
        own_position=Position(0, 0),
        belief_peak=Position(0, 6),
        legal_moves=(Move.SOUTH, Move.EAST, Move.STAY),
        turn_number=1,
        max_turns=35,
        remaining_barriers=14,
    )


def test_gemini_selects_a_supplied_legal_move_and_returns_its_reason():
    models = _FakeModels()
    advisor = GeminiAgentAdvisor(
        client=SimpleNamespace(models=models),
        model="test-model",
        timeout_seconds=3,
    )
    decision = advisor.choose_move(_context(), Move.STAY)
    assert decision.move is Move.EAST
    assert decision.rationale == "Closing on the strongest scent signal."
    assert decision.used_fallback is False
    assert models.calls[0]["model"] == "test-model"
    assert models.calls[0]["config"]["max_output_tokens"] == 128
    assert models.calls[0]["config"]["http_options"]["timeout"] == 10000


def test_gemini_records_provider_token_usage():
    usage = SimpleNamespace(prompt_token_count=41, candidates_token_count=7)
    advisor = GeminiAgentAdvisor(
        client=SimpleNamespace(models=_FakeModels(usage=usage)), model="test-model"
    )
    advisor.choose_move(_context(), Move.STAY)
    assert advisor.usage_snapshot() == (41, 7)


def test_gemini_accepts_move_codes_and_move_prefixes():
    models = _FakeModels("MOVE: E|Shortest legal code.")
    advisor = GeminiAgentAdvisor(client=SimpleNamespace(models=models))
    decision = advisor.choose_move(_context(), Move.STAY)
    assert decision.move is Move.EAST
    assert decision.rationale == "Shortest legal code."
    assert decision.used_fallback is False


def test_invalid_gemini_move_uses_the_validated_heuristic_fallback():
    models = _FakeModels("TELEPORT|Surprise!")
    advisor = GeminiAgentAdvisor(client=SimpleNamespace(models=models))
    decision = advisor.choose_move(_context(), Move.SOUTH)
    assert decision.move is Move.SOUTH
    assert decision.used_fallback is True


def test_provider_failure_uses_fallback_without_crashing_the_match():
    models = _FakeModels(error=TimeoutError("offline"))
    advisor = GeminiAgentAdvisor(client=SimpleNamespace(models=models))
    decision = advisor.choose_move(_context(), Move.STAY)
    assert decision.move is Move.STAY
    assert decision.used_fallback is True
    assert "TimeoutError" in decision.rationale
    assert "offline" in decision.rationale
    assert "after 1 Gemini attempt(s)" in decision.rationale


def test_fallback_models_are_opt_in():
    models = _FakeModels(error=TimeoutError("offline"))
    advisor = GeminiAgentAdvisor(
        client=SimpleNamespace(models=models),
        model="test-model",
        allow_fallback_models=True,
    )
    decision = advisor.choose_move(_context(), Move.STAY)
    assert decision.move is Move.STAY
    assert decision.used_fallback is True
    assert "after 3 Gemini attempt(s)" in decision.rationale
    assert [call["model"] for call in models.calls] == [
        "test-model",
        "gemini-flash-latest",
        "gemini-2.5-flash",
    ]


def test_provider_error_redacts_api_keys(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "super-secret-key")
    message = GeminiAgentAdvisor._safe_error(RuntimeError("bad super-secret-key"))
    assert "super-secret-key" not in message
    assert "<redacted>" in message


def test_prompt_contains_local_belief_but_not_an_opponent_true_position():
    prompt = GeminiAgentAdvisor._prompt(_context())
    assert "BELIEVED_OPPONENT=(0,6)" in prompt
    assert "ALLOWED_ACTIONS=SOUTH [S]; EAST [E]; STAY [STAY]" in prompt
    assert "true position" not in prompt.lower()


class _SequenceModels:
    def __init__(self, texts):
        self.texts = iter(texts)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text=next(self.texts))


def test_invalid_action_is_reprompted_and_corrected_before_fallback():
    models = _SequenceModels(["NORTH|off board", '{"action":"EAST","reason":"legal repair"}'])
    advisor = GeminiAgentAdvisor(client=SimpleNamespace(models=models))
    decision = advisor.choose_move(_context(), Move.STAY)
    assert decision.move is Move.EAST
    assert decision.used_fallback is False
    assert decision.attempts == 2
    assert "NORTH" in decision.rejected[0]
    assert "previous response was rejected" in models.calls[1]["contents"].lower()


def test_json_and_common_direction_alias_are_strictly_mapped_to_legal_move():
    models = _FakeModels('{"action":"RIGHT","reason":"open escape"}')
    advisor = GeminiAgentAdvisor(client=SimpleNamespace(models=models))
    decision = advisor.choose_move(_context(), Move.STAY)
    assert decision.move is Move.EAST
    assert decision.used_fallback is False


def test_illegal_caller_fallback_is_repaired_to_a_legal_action():
    models = _FakeModels("TELEPORT")
    advisor = GeminiAgentAdvisor(client=SimpleNamespace(models=models))
    decision = advisor.choose_move(_context(), Move.NORTH)
    assert decision.move in _context().legal_moves
    assert decision.move is Move.STAY
    assert decision.used_fallback is True
