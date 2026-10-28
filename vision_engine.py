import cv2
import math
import time

try:
    import mediapipe as mp
    from mediapipe.python.solutions import pose as mp_pose
    from mediapipe.python.solutions import drawing_utils as mp_drawing
except (AttributeError, ImportError):
    import mediapipe as mp
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils

def calc_angle_mp(a, b, c):
    ax, ay = a.x, a.y
    bx, by = b.x, b.y
    cx, cy = c.x, c.y
    ba = (ax - bx, ay - by)
    bc = (cx - bx, cy - by)
    dot = ba[0]*bc[0] + ba[1]*bc[1]
    mag_ba = math.sqrt(ba[0]**2 + ba[1]**2)
    mag_bc = math.sqrt(bc[0]**2 + bc[1]**2)
    if mag_ba == 0 or mag_bc == 0: return None
    cos_angle = dot / (mag_ba * mag_bc)
    cos_angle = max(-1, min(1, cos_angle))
    return math.degrees(math.acos(cos_angle))

class VisionEngine:
    def __init__(self):
        # 初始化 MediaPipe
        self.pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)
        self.mp_draw = mp_drawing
        self.last_frame_time = time.time()
        
        # 動態任務變數
        self.active_mission = "IDLE"
        self.mission_target_count = 0
        self.mission_current_count = 0
        
        # 關卡：頭部變數
        self.calibrated = False
        self.calibration_frames = []
        self.baseline_x = None
        self.calibration_start_time = None
        self.HEAD_SHIFT_THRESHOLD = 0.04
        self.head_target = "LEFT"
        self.head_phase_sec = 0.0
        
        # 關卡：深蹲變數
        self.squat_state = "up"

    def set_mission(self, mission_name, target_count):
        """
        接收外部觸發，設定當前要執行的微運動任務
        """
        self.active_mission = mission_name
        self.mission_target_count = target_count
        self.mission_current_count = 0
        
        # 重置各任務專屬變數
        if mission_name == "HEAD":
            self.calibrated = False
            self.calibration_frames = []
            self.calibration_start_time = None
            self.head_phase_sec = 0.0
            self.head_target = "LEFT"
        elif mission_name == "SQUAT":
            self.squat_state = "up"

    def process_frame(self, frame):
        """
        接收單張 BGR 影像，進行姿勢判斷，並回傳處理後的影像與事件字典
        """
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        
        # 待機模式下，只顯示畫面，不進行重度運算
        if self.active_mission == "IDLE":
            cv2.putText(frame, "Standby - Ready for tasks", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            return frame, {"mission": "IDLE", "status_text": "待機中", "event": None, "progress": ""}

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        current_frame_time = time.time()
        dt = current_frame_time - self.last_frame_time
        self.last_frame_time = current_frame_time

        current_status = "Scanning..."
        triggered_event = None

        if results.pose_landmarks:
            self.mp_draw.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            lm = results.pose_landmarks.landmark
            nose = lm[mp_pose.PoseLandmark.NOSE]

            # -------------------------------------------------------------
            # 任務：頭部對抗 (HEAD)
            # -------------------------------------------------------------
            if self.active_mission == "HEAD":
                if not self.calibrated:
                    if self.calibration_start_time is None: 
                        self.calibration_start_time = time.time()
                    
                    elapsed = time.time() - self.calibration_start_time
                    if elapsed < 3.0:
                        self.calibration_frames.append(nose.x)
                        current_status = f"Calibrating... {3 - int(elapsed)}s"
                    else:
                        self.baseline_x = sum(self.calibration_frames) / len(self.calibration_frames)
                        self.calibrated = True
                else:
                    shift = nose.x - self.baseline_x
                    is_correct = False
                    
                    if self.head_target == "LEFT" and shift < -self.HEAD_SHIFT_THRESHOLD:
                        is_correct = True
                    elif self.head_target == "RIGHT" and shift > self.HEAD_SHIFT_THRESHOLD:
                        is_correct = True

                    if is_correct:
                        self.head_phase_sec += dt
                        current_status = f"MATCH! Holding {self.head_target}..."
                        if self.head_phase_sec > 2.0: # 維持兩秒算成功一次
                            self.mission_current_count += 1
                            self.head_phase_sec = 0.0
                            self.head_target = "RIGHT" if self.head_target == "LEFT" else "LEFT"
                            triggered_event = "ACTION_SUCCESS"
                            
                            if self.mission_current_count >= self.mission_target_count:
                                triggered_event = "MISSION_CLEARED"
                    else:
                        current_status = f"Move Head {self.head_target}"

            # -------------------------------------------------------------
            # 任務：深蹲 (SQUAT)
            # -------------------------------------------------------------
            elif self.active_mission == "SQUAT":
                l_hip = lm[mp_pose.PoseLandmark.LEFT_HIP]
                l_knee = lm[mp_pose.PoseLandmark.LEFT_KNEE]
                l_ankle = lm[mp_pose.PoseLandmark.LEFT_ANKLE]

                if l_hip.visibility > 0.5 and l_knee.visibility > 0.5:
                    knee_angle = calc_angle_mp(l_hip, l_knee, l_ankle)
                    if knee_angle is not None:
                        current_status = f"Squat Angle: {int(knee_angle)}"
                        
                        if knee_angle < 100 and self.squat_state == "up":
                            self.squat_state = "down"
                        elif knee_angle > 160 and self.squat_state == "down":
                            self.squat_state = "up"
                            self.mission_current_count += 1
                            triggered_event = "ACTION_SUCCESS"
                            
                            if self.mission_current_count >= self.mission_target_count:
                                triggered_event = "MISSION_CLEARED"
                else:
                    current_status = "Please step back to show your full body"

            # 繪製進度與狀態供除錯
            progress_str = f"{self.mission_current_count}/{self.mission_target_count}"
            cv2.putText(frame, f"[{self.active_mission}] {progress_str}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
            cv2.putText(frame, current_status, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        else:
            progress_str = f"{self.mission_current_count}/{self.mission_target_count}"

        return frame, {
            "mission": self.active_mission, 
            "status_text": current_status, 
            "event": triggered_event,
            "progress": progress_str
        }