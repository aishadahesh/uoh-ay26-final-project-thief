"""The selectable play modes and who controls each role in them.

Split out of `interactive_match.py` so the mode vocabulary can be imported
by the GUI's mode-selection screen without pulling in the whole match
engine. `interactive_match` re-exports these names, so existing imports
from there keep working.
"""

from __future__ import annotations

from enum import StrEnum

from police_thief.shared.constants import AgentRole

__all__ = ["GameMode", "MODE_LABELS", "PlayerType", "controller_for"]


class PlayerType(StrEnum):
    AGENT = "agent"
    HUMAN = "human"


class GameMode(StrEnum):
    """The four selectable modes, mirroring the reference "playable GUI"
    experience this was modeled on, translated to this project's cop/thief
    terminology."""

    AGENT_VS_AGENT = "agent_vs_agent"
    NETWORK_AGENT_VS_AGENT = "network_agent_vs_agent"
    HUMAN_COP_VS_AGENT = "human_cop_vs_agent"
    AGENT_VS_HUMAN_THIEF = "agent_vs_human_thief"
    HUMAN_VS_HUMAN = "human_vs_human"


MODE_LABELS: dict[GameMode, str] = {
    GameMode.AGENT_VS_AGENT: "Agent vs Agent",
    GameMode.NETWORK_AGENT_VS_AGENT: "Agent vs Agent (Two Computers)",
    GameMode.HUMAN_COP_VS_AGENT: "Human (Cop) vs Agent",
    GameMode.AGENT_VS_HUMAN_THIEF: "Agent vs Human (Thief)",
    GameMode.HUMAN_VS_HUMAN: "Human vs Human",
}

_MODE_CONTROL: dict[GameMode, dict[AgentRole, PlayerType]] = {
    GameMode.AGENT_VS_AGENT: {AgentRole.COP: PlayerType.AGENT, AgentRole.THIEF: PlayerType.AGENT},
    GameMode.NETWORK_AGENT_VS_AGENT: {
        AgentRole.COP: PlayerType.AGENT,
        AgentRole.THIEF: PlayerType.AGENT,
    },
    GameMode.HUMAN_COP_VS_AGENT: {
        AgentRole.COP: PlayerType.HUMAN,
        AgentRole.THIEF: PlayerType.AGENT,
    },
    GameMode.AGENT_VS_HUMAN_THIEF: {
        AgentRole.COP: PlayerType.AGENT,
        AgentRole.THIEF: PlayerType.HUMAN,
    },
    GameMode.HUMAN_VS_HUMAN: {AgentRole.COP: PlayerType.HUMAN, AgentRole.THIEF: PlayerType.HUMAN},
}


def controller_for(mode: GameMode, role: AgentRole) -> PlayerType:
    return _MODE_CONTROL[mode][role]
