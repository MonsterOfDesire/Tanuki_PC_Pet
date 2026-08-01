from dataclasses import dataclass


FORM_BASE = "base"
FORM_TRANSFORMED = "transformed"

TRANSFORMATION_PHASE_IDLE = "idle"
TRANSFORMATION_PHASE_WHITENING = "whitening"
TRANSFORMATION_PHASE_REVEALING = "revealing"


@dataclass
class PetTransformationState:
    current_form: str = FORM_BASE
    target_form: str = ""
    phase: str = TRANSFORMATION_PHASE_IDLE
    phase_started_at: float = 0.0
    whiteness: float = 0.0
    source: str = ""
    auto_session: bool = False
    auto_world_mode: str = ""
    auto_next_attempt_at: float = 0.0
    auto_form_expires_at: float = 0.0
    auto_retry_at: float = 0.0
    manual_end_requested: bool = False

    @property
    def active(self) -> bool:
        return self.phase != TRANSFORMATION_PHASE_IDLE

    def begin(self, *, target_form: str, now: float, source: str = "") -> None:
        self.target_form = str(target_form or "")
        self.phase = TRANSFORMATION_PHASE_WHITENING
        self.phase_started_at = float(now)
        self.whiteness = 0.0
        self.source = str(source or "")

    def begin_reveal(self, *, now: float) -> None:
        self.phase = TRANSFORMATION_PHASE_REVEALING
        self.phase_started_at = float(now)
        self.whiteness = 1.0

    def finish(self) -> None:
        self.target_form = ""
        self.phase = TRANSFORMATION_PHASE_IDLE
        self.phase_started_at = 0.0
        self.whiteness = 0.0
        self.source = ""
