"""Computer vision engine for posture tracking and exercise detection."""

from dataclasses import dataclass
from enum import Enum
import math
import time
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

try:
    import mediapipe as mp
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
except (AttributeError, ImportError):
    try:
        # Fallback import for alternative mediapipe package layouts
        import mediapipe as mp
        from mediapipe.python.solutions import pose as mp_pose
        from mediapipe.python.solutions import drawing_utils as mp_drawing
    except (AttributeError, ImportError):
        mp = None
        mp_pose = None
        mp_drawing = None


class MissionType(str, Enum):
    """Supported fitness micro-missions."""
    IDLE = "IDLE"
    HEAD = "HEAD"
    SQUAT = "SQUAT"


class VisionEvent(str, Enum):
    """Events emitted by the posture recognition pipeline."""
    ACTION_SUCCESS = "ACTION_SUCCESS"
    MISSION_CLEARED = "MISSION_CLEARED"


@dataclass
class VisionResult:
    """Structured result returned for each processed video frame."""
    mission: MissionType
    status_text: str
    event: Optional[VisionEvent]
    progress: str

    def __getitem__(self, item: str) -> Any:
        """Provide dictionary-style compatibility."""
        lookup: Dict[str, Any] = {
            "mission": self.mission.value,
            "status_text": self.status_text,
            "event": self.event.value if self.event else None,
            "progress": self.progress,
        }
        return lookup[item]


def calculate_angle(a: Any, b: Any, c: Any) -> Optional[float]:
    """Calculate 2D angle ABC (at vertex B) in degrees from three landmarks.

    Args:
        a: First landmark with x, y coordinates.
        b: Vertex landmark with x, y coordinates.
        c: Third landmark with x, y coordinates.

    Returns:
        Angle in degrees in [0, 180], or None if vector magnitude is zero.
    """
    ba_x = a.x - b.x
    ba_y = a.y - b.y
    bc_x = c.x - b.x
    bc_y = c.y - b.y

    dot = ba_x * bc_x + ba_y * bc_y
    mag_ba = math.hypot(ba_x, ba_y)
    mag_bc = math.hypot(bc_x, bc_y)

    if mag_ba == 0.0 or mag_bc == 0.0:
        return None

    cosine = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cosine))


class VisionEngine:
    """Manages pose detection, baseline calibration, and repetition counters."""

    HEAD_SHIFT_THRESHOLD: float = 0.04
    CALIBRATION_DURATION_SEC: float = 3.0
    HEAD_HOLD_DURATION_SEC: float = 2.0
    SQUAT_DOWN_ANGLE: float = 100.0
    SQUAT_UP_ANGLE: float = 160.0
    VISIBILITY_THRESHOLD: float = 0.5
    MAX_FRAME_DT_SEC: float = 0.5

    def __init__(
        self,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.7,
    ) -> None:
        """Initialize MediaPipe Pose and tracker state.

        Raises:
            ImportError: If opencv-python or mediapipe are not installed.
        """
        if cv2 is None or np is None or mp_pose is None:
            raise ImportError(
                "opencv-python and mediapipe are required to use VisionEngine. "
                "Install them via 'pip install -r requirements.txt'."
            )

        self.pose = mp_pose.Pose(
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self.mp_draw = mp_drawing
        self.last_frame_time: float = time.time()

        # Dynamic mission configuration
        self.active_mission: MissionType = MissionType.IDLE
        self.mission_target_count: int = 0
        self.mission_current_count: int = 0

        # Head resistance mission state
        self.calibrated: bool = False
        self.calibration_frames: List[float] = []
        self.baseline_x: Optional[float] = None
        self.calibration_start_time: Optional[float] = None
        self.head_target: str = "LEFT"
        self.head_phase_sec: float = 0.0

        # Squat mission state
        self.squat_state: str = "up"

    def set_mission(self, mission_name: Union[str, MissionType], target_count: int) -> None:
        """Configure active mission and target repetition count.

        Args:
            mission_name: Name of mission (IDLE, HEAD, or SQUAT).
            target_count: Target repetitions needed to clear mission.
        """
        self.active_mission = MissionType(mission_name)
        self.mission_target_count = max(0, target_count)
        self.mission_current_count = 0

        # Reset task-specific trackers
        if self.active_mission == MissionType.HEAD:
            self.calibrated = False
            self.calibration_frames.clear()
            self.calibration_start_time = None
            self.head_phase_sec = 0.0
            self.head_target = "LEFT"
        elif self.active_mission == MissionType.SQUAT:
            self.squat_state = "up"

    def process_frame(self, frame: Any) -> Tuple[Any, VisionResult]:
        """Process a single camera frame and evaluate pose landmarks.

        Args:
            frame: Raw BGR input frame from camera.

        Returns:
            Tuple of (annotated BGR frame, VisionResult event metadata).
        """
        # Mirror image horizontally for natural selfie view
        frame = cv2.flip(frame, 1)
        progress_str = f"{self.mission_current_count}/{self.mission_target_count}"

        # Lightweight standby mode
        if self.active_mission == MissionType.IDLE:
            cv2.putText(
                frame,
                "Standby - Ready for tasks",
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2,
            )
            result = VisionResult(
                mission=MissionType.IDLE,
                status_text="Standby",
                event=None,
                progress="",
            )
            return frame, result

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        now = time.time()
        # ponytail: clamp dt to prevent massive jumps when UI freezes or drops frames
        dt = min(max(0.0, now - self.last_frame_time), self.MAX_FRAME_DT_SEC)
        self.last_frame_time = now

        current_status = "Scanning..."
        triggered_event: Optional[VisionEvent] = None

        if results.pose_landmarks:
            self.mp_draw.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            lm = results.pose_landmarks.landmark

            if self.active_mission == MissionType.HEAD:
                triggered_event, current_status = self._process_head_mission(lm, dt)
            elif self.active_mission == MissionType.SQUAT:
                triggered_event, current_status = self._process_squat_mission(lm)

            # Draw HUD status overlay
            cv2.putText(
                frame,
                f"[{self.active_mission.value}] {progress_str}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 165, 255),
                2,
            )
            cv2.putText(
                frame,
                current_status,
                (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2,
            )

        result = VisionResult(
            mission=self.active_mission,
            status_text=current_status,
            event=triggered_event,
            progress=progress_str,
        )
        return frame, result

    def _process_head_mission(self, landmarks: Any, dt: float) -> Tuple[Optional[VisionEvent], str]:
        """Detect isometric head resistance stretch movement."""
        nose = landmarks[mp_pose.PoseLandmark.NOSE]

        # Calibration phase: sample neutral head position for 3 seconds
        if not self.calibrated:
            if self.calibration_start_time is None:
                self.calibration_start_time = time.time()

            elapsed = time.time() - self.calibration_start_time
            if elapsed < self.CALIBRATION_DURATION_SEC:
                self.calibration_frames.append(nose.x)
                remaining = int(math.ceil(self.CALIBRATION_DURATION_SEC - elapsed))
                return None, f"Calibrating... {remaining}s"

            if self.calibration_frames:
                self.baseline_x = sum(self.calibration_frames) / len(self.calibration_frames)
            else:
                self.baseline_x = nose.x
            self.calibrated = True

        shift = nose.x - (self.baseline_x if self.baseline_x is not None else nose.x)
        is_correct = (
            (self.head_target == "LEFT" and shift < -self.HEAD_SHIFT_THRESHOLD)
            or (self.head_target == "RIGHT" and shift > self.HEAD_SHIFT_THRESHOLD)
        )

        if not is_correct:
            return None, f"Move Head {self.head_target}"

        self.head_phase_sec += dt
        status = f"MATCH! Holding {self.head_target}..."

        if self.head_phase_sec >= self.HEAD_HOLD_DURATION_SEC:
            self.mission_current_count += 1
            self.head_phase_sec = 0.0
            self.head_target = "RIGHT" if self.head_target == "LEFT" else "LEFT"

            if self.mission_current_count >= self.mission_target_count:
                return VisionEvent.MISSION_CLEARED, status
            return VisionEvent.ACTION_SUCCESS, status

        return None, status

    def _process_squat_mission(self, landmarks: Any) -> Tuple[Optional[VisionEvent], str]:
        """Detect full body squat repetitions via knee joint angle."""
        l_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        l_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE]
        l_ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE]

        if l_hip.visibility <= self.VISIBILITY_THRESHOLD or l_knee.visibility <= self.VISIBILITY_THRESHOLD:
            return None, "Please step back to show your full body"

        knee_angle = calculate_angle(l_hip, l_knee, l_ankle)
        if knee_angle is None:
            return None, "Scanning..."

        status = f"Squat Angle: {int(knee_angle)}"

        if knee_angle < self.SQUAT_DOWN_ANGLE and self.squat_state == "up":
            self.squat_state = "down"
        elif knee_angle > self.SQUAT_UP_ANGLE and self.squat_state == "down":
            self.squat_state = "up"
            self.mission_current_count += 1

            if self.mission_current_count >= self.mission_target_count:
                return VisionEvent.MISSION_CLEARED, status
            return VisionEvent.ACTION_SUCCESS, status

        return None, status

    def close(self) -> None:
        """Release underlying pose estimation resources."""
        if hasattr(self, "pose") and self.pose is not None:
            self.pose.close()