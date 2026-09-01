"""Split-safe Web/App consumer boundary for simulated Masck One product state.

This module deliberately separates local UI intent from simulated mechanical and
simulated device events. It does not expose BLE, telemetry, sensing or hardware-command
semantics. The underlying :class:`SimulatedTransport` remains the canonical state-event
engine; this wrapper narrows how digital consumers are allowed to drive it.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json

from .mechanism_state import (
    MechanismState,
    SimulatedTransport,
    TransitionAction,
    derive_next_state,
)

CONSUMER_CONTRACT = "MASCK_ONE_PRODUCT_STATE_CONSUMER_V1"
HARDWARE_COMMAND_CAPABILITY = "NONE_SIMULATION_ONLY"
CONNECTIVITY_MODEL = "ABSENT_NOT_MODELED"


class ConsumerInputChannel(str, Enum):
    """Authority class for one simulated transition input."""

    UI_INTENT = "UI_INTENT"
    SIMULATED_MECHANICAL_EVENT = "SIMULATED_MECHANICAL_EVENT"
    SIMULATED_DEVICE_EVENT = "SIMULATED_DEVICE_EVENT"


@dataclass(frozen=True)
class TransitionSemantics:
    """Immutable digital-consumer semantics for one transition action."""

    action: TransitionAction
    channel: ConsumerInputChannel

    def __post_init__(self) -> None:
        if type(self.action) is not TransitionAction:
            raise TypeError("action must be exact TransitionAction")
        if type(self.channel) is not ConsumerInputChannel:
            raise TypeError("channel must be exact ConsumerInputChannel")

    @property
    def ui_control_exposed(self) -> bool:
        return self.channel is ConsumerInputChannel.UI_INTENT

    def manifest(self) -> dict[str, object]:
        return {
            "action": self.action.value,
            "channel": self.channel.value,
            "ui_control_exposed": self.ui_control_exposed,
            "hardware_command": False,
        }


# Keep this tuple in TransitionAction declaration order. Every action appears exactly once.
_ACTION_SEMANTICS = (
    TransitionSemantics(TransitionAction.ENGAGE_RETENTION, ConsumerInputChannel.SIMULATED_MECHANICAL_EVENT),
    TransitionSemantics(TransitionAction.RELEASE_RETENTION, ConsumerInputChannel.SIMULATED_MECHANICAL_EVENT),
    TransitionSemantics(TransitionAction.MECHANICAL_QUICK_RELEASE, ConsumerInputChannel.SIMULATED_MECHANICAL_EVENT),
    TransitionSemantics(TransitionAction.RESET_RELEASE, ConsumerInputChannel.SIMULATED_MECHANICAL_EVENT),
    TransitionSemantics(TransitionAction.START_CLEAN, ConsumerInputChannel.UI_INTENT),
    TransitionSemantics(TransitionAction.START_WARM, ConsumerInputChannel.UI_INTENT),
    TransitionSemantics(TransitionAction.STOP_CYCLE, ConsumerInputChannel.UI_INTENT),
    TransitionSemantics(TransitionAction.COMPLETE_CYCLE, ConsumerInputChannel.SIMULATED_DEVICE_EVENT),
    TransitionSemantics(TransitionAction.ENTER_SERVICE, ConsumerInputChannel.UI_INTENT),
    TransitionSemantics(TransitionAction.EXIT_SERVICE, ConsumerInputChannel.UI_INTENT),
    TransitionSemantics(TransitionAction.OPEN_SERVICE, ConsumerInputChannel.SIMULATED_MECHANICAL_EVENT),
    TransitionSemantics(TransitionAction.CLOSE_SERVICE, ConsumerInputChannel.SIMULATED_MECHANICAL_EVENT),
    TransitionSemantics(TransitionAction.LATCH_FAULT, ConsumerInputChannel.SIMULATED_DEVICE_EVENT),
    TransitionSemantics(TransitionAction.CLEAR_FAULT, ConsumerInputChannel.SIMULATED_DEVICE_EVENT),
)

if tuple(item.action for item in _ACTION_SEMANTICS) != tuple(TransitionAction):
    raise RuntimeError("transition consumer semantics must cover TransitionAction exactly once and in canonical order")


def transition_semantics(action: TransitionAction) -> TransitionSemantics:
    """Return immutable channel semantics for an exact transition action."""

    if type(action) is not TransitionAction:
        raise TypeError("action must be exact TransitionAction")
    for item in _ACTION_SEMANTICS:
        if item.action is action:
            return item
    raise RuntimeError(f"missing transition semantics for {action.value}")


def _is_legal(state: MechanismState, action: TransitionAction) -> bool:
    """Return legality without swallowing provenance or invariant failures."""

    state.validate_invariants()
    try:
        derive_next_state(
            state,
            action,
            current_mechanism_provenance_sha256=state.mechanism_provenance_sha256,
        )
    except ValueError as exc:
        if str(exc) == f"action {action.value} is illegal from current state":
            return False
        raise
    return True


def legal_actions_for_channel(
    state: MechanismState,
    channel: ConsumerInputChannel,
) -> tuple[TransitionAction, ...]:
    """Return canonical legal actions for one consumer input channel."""

    if type(state) is not MechanismState:
        raise TypeError("state must be exact MechanismState")
    if type(channel) is not ConsumerInputChannel:
        raise TypeError("channel must be exact ConsumerInputChannel")
    state.validate_invariants()
    return tuple(
        item.action
        for item in _ACTION_SEMANTICS
        if item.channel is channel and _is_legal(state, item.action)
    )


class ProductStateConsumer:
    """Narrow Web/App facade over canonical simulation-only mechanism state.

    UI code may submit only actions classified as ``UI_INTENT``. Mechanical release,
    retention, service-access motion and device-generated completion/fault events must
    enter through their explicit simulation-event methods. This distinction prevents a
    prototype UI from silently turning observed physical events into fictional commands.
    """

    __slots__ = ("_transport",)

    def __init__(
        self,
        initial_state: MechanismState,
        *,
        current_mechanism_provenance_sha256: str,
    ) -> None:
        self._transport = SimulatedTransport(
            initial_state,
            current_mechanism_provenance_sha256=current_mechanism_provenance_sha256,
        )
        self.validate_invariants()

    def validate_invariants(self) -> None:
        if type(self._transport) is not SimulatedTransport:
            raise TypeError("internal transport must be exact SimulatedTransport")
        self._transport.validate_invariants()

    @property
    def sequence(self) -> int:
        self.validate_invariants()
        return self._transport.sequence

    @property
    def last_event(self) -> str | None:
        self.validate_invariants()
        return self._transport.last_event

    def snapshot(self) -> MechanismState:
        self.validate_invariants()
        return self._transport.snapshot()

    def available_ui_intents(self) -> tuple[TransitionAction, ...]:
        return legal_actions_for_channel(self.snapshot(), ConsumerInputChannel.UI_INTENT)

    def available_simulated_mechanical_events(self) -> tuple[TransitionAction, ...]:
        return legal_actions_for_channel(
            self.snapshot(), ConsumerInputChannel.SIMULATED_MECHANICAL_EVENT
        )

    def available_simulated_device_events(self) -> tuple[TransitionAction, ...]:
        return legal_actions_for_channel(
            self.snapshot(), ConsumerInputChannel.SIMULATED_DEVICE_EVENT
        )

    def _dispatch_on_channel(
        self,
        action: TransitionAction,
        required_channel: ConsumerInputChannel,
    ) -> MechanismState:
        if type(action) is not TransitionAction:
            raise TypeError("action must be exact TransitionAction")
        if type(required_channel) is not ConsumerInputChannel:
            raise TypeError("required_channel must be exact ConsumerInputChannel")
        self.validate_invariants()
        semantics = transition_semantics(action)
        if semantics.channel is not required_channel:
            raise ValueError(
                f"action {action.value} belongs to {semantics.channel.value}, not {required_channel.value}"
            )
        # SimulatedTransport.dispatch is transactional for illegal transitions. Channel
        # mismatch is rejected above before any state or sequence mutation.
        return self._transport.dispatch(action)

    def submit_ui_intent(self, action: TransitionAction) -> MechanismState:
        """Apply a local UI intent to simulation only, never to hardware."""

        return self._dispatch_on_channel(action, ConsumerInputChannel.UI_INTENT)

    def observe_simulated_mechanical_event(self, action: TransitionAction) -> MechanismState:
        """Inject a simulated observation of a physical mechanism event."""

        return self._dispatch_on_channel(
            action, ConsumerInputChannel.SIMULATED_MECHANICAL_EVENT
        )

    def observe_simulated_device_event(self, action: TransitionAction) -> MechanismState:
        """Inject a simulated device/system event with no telemetry claim."""

        return self._dispatch_on_channel(action, ConsumerInputChannel.SIMULATED_DEVICE_EVENT)

    def _manifest_payload(self) -> dict[str, object]:
        self.validate_invariants()
        snapshot = self.snapshot()
        transport = self._transport.manifest()
        return {
            "schema": CONSUMER_CONTRACT,
            "transport_schema": transport["schema"],
            "state_contract": transport["state_contract"],
            "transition_contract": transport["transition_contract"],
            "hardware_command_capability": HARDWARE_COMMAND_CAPABILITY,
            "connectivity_model": CONNECTIVITY_MODEL,
            "telemetry_source": "NONE",
            "measured_hardware": False,
            "sequence": self.sequence,
            "last_event": self.last_event,
            "state": transport["state"],
            "available_ui_intents": [action.value for action in self.available_ui_intents()],
            "available_simulated_mechanical_events": [
                action.value for action in self.available_simulated_mechanical_events()
            ],
            "available_simulated_device_events": [
                action.value for action in self.available_simulated_device_events()
            ],
            "action_semantics": [item.manifest() for item in _ACTION_SEMANTICS],
            "state_provenance_sha256": snapshot.provenance_sha256,
            "source_transport_provenance_sha256": transport["transport_provenance_sha256"],
        }

    @property
    def provenance_sha256(self) -> str:
        payload = self._manifest_payload()
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
        return hashlib.sha256(encoded).hexdigest()

    def manifest(self) -> dict[str, object]:
        payload = self._manifest_payload()
        payload["consumer_provenance_sha256"] = self.provenance_sha256
        return payload
