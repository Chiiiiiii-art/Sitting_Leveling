"""Desktop GUI application for Sitting Leveling."""

import sys
import tkinter as tk
from tkinter import messagebox
from typing import Optional

import cv2
from PIL import Image, ImageTk

from rpg_system import RPGSystem
from vision_engine import MissionType, VisionEngine, VisionEvent


class FitnessApp:
    """Main application controller binding Vision, RPG, and Tkinter UI."""

    FRAME_WIDTH = 640
    FRAME_HEIGHT = 480
    FRAME_DELAY_MS = 30
    DEFAULT_WEIGHT_LOSS_TARGET_KG = 1.0

    def __init__(self, root: tk.Tk) -> None:
        """Initialize user interface, vision engine, and RPG state."""
        self.root = root
        self.root.title("我坐著升級 Sitting Leveling MVP")

        self.vision = VisionEngine()
        self.rpg = RPGSystem(target_weight_loss_kg=self.DEFAULT_WEIGHT_LOSS_TARGET_KG)

        self.cap: Optional[cv2.VideoCapture] = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            # Handle unavailable webcam gracefully
            messagebox.showwarning(
                "Camera Warning",
                "Webcam (Device 0) could not be opened. Video tracking is disabled.",
            )
            self.cap = None
        else:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.FRAME_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.FRAME_HEIGHT)

        self._build_ui()
        self.update_frame()

    def _build_ui(self) -> None:
        """Construct the Tkinter layout and widgets."""
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(padx=10, pady=10)

        self.video_label = tk.Label(self.main_frame)
        self.video_label.grid(row=0, column=0, padx=10)

        self.panel_frame = tk.Frame(self.main_frame, width=300)
        self.panel_frame.grid(row=0, column=1, sticky="n", padx=10)

        self.task_label = tk.Label(
            self.panel_frame,
            text="當前狀態: 待機中",
            font=("Arial", 14),
            fg="green",
        )
        self.task_label.pack(pady=10, anchor="w")

        self.hp_label = tk.Label(self.panel_frame, text="", font=("Arial", 16))
        self.hp_label.pack(pady=5, anchor="w")

        self.armor_label = tk.Label(self.panel_frame, text="", font=("Arial", 16))
        self.armor_label.pack(pady=5, anchor="w")

        self.coin_label = tk.Label(self.panel_frame, text="", font=("Arial", 16))
        self.coin_label.pack(pady=5, anchor="w")

        self.msg_text = tk.Text(self.panel_frame, height=5, width=30, state=tk.DISABLED)
        self.msg_text.pack(pady=10)

        tk.Button(
            self.panel_frame,
            text="模擬紀錄：珍珠奶茶",
            command=self.mock_event_boba,
        ).pack(fill="x", pady=5)

        tk.Button(
            self.panel_frame,
            text="模擬行程：連續三小時會議",
            command=self.mock_event_meeting,
        ).pack(fill="x", pady=5)

        self.refresh_rpg_ui()

    def update_frame(self) -> None:
        """Poll webcam frame, run vision processing, and refresh GUI."""
        if self.cap is not None and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                processed_frame, event_data = self.vision.process_frame(frame)

                # Update active mission status banner
                if event_data.mission != MissionType.IDLE:
                    self.task_label.config(
                        text=f"任務執行中: {event_data.mission.value} ({event_data.progress})",
                        fg="red",
                    )
                else:
                    self.task_label.config(text="當前狀態: 待機中", fg="green")

                # Handle gameplay events triggered by vision engine
                if event_data.event == VisionEvent.ACTION_SUCCESS:
                    damage = self.rpg.process_action_success(base_calories_burned=10, coin_reward=5)
                    self.log_message(f"動作完成 1 次！造成 {damage} 點傷害。")
                    self.refresh_rpg_ui()
                elif event_data.event == VisionEvent.MISSION_CLEARED:
                    self.log_message("任務達成！警示解除，回歸待機狀態。")
                    self.vision.set_mission(MissionType.IDLE, 0)

                # Convert OpenCV BGR to Tkinter PhotoImage
                rgb_image = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_image)
                photo_image = ImageTk.PhotoImage(image=pil_image)
                self.video_label.imgtk = photo_image
                self.video_label.configure(image=photo_image)

        self.root.after(self.FRAME_DELAY_MS, self.update_frame)

    def refresh_rpg_ui(self) -> None:
        """Update RPG system metrics labels."""
        self.hp_label.config(text=f"魔王血量: {self.rpg.current_hp} / {self.rpg.max_hp}")
        self.armor_label.config(text=f"魔王護甲: {self.rpg.armor}")
        self.coin_label.config(text=f"帶薪金幣: {self.rpg.coins}")

    def log_message(self, msg: str) -> None:
        """Append message to GUI log text box."""
        self.msg_text.config(state=tk.NORMAL)
        self.msg_text.insert(tk.END, msg + "\n")
        self.msg_text.see(tk.END)
        self.msg_text.config(state=tk.DISABLED)

    def mock_event_boba(self) -> None:
        """Simulate food calorie intake event."""
        self.rpg.add_armor_from_food(500)
        self.refresh_rpg_ui()
        self.log_message("飲食紀錄：珍珠奶茶（+500 大卡）。\n魔王護甲增加 500 點。\n解鎖任務：深蹲 5 次。")
        self.vision.set_mission(MissionType.SQUAT, 5)

    def mock_event_meeting(self) -> None:
        """Simulate prolonged sitting schedule event."""
        self.log_message("行程提醒：接下來有連續會議。\n解鎖任務：頭部對抗伸展 3 次。")
        self.vision.set_mission(MissionType.HEAD, 3)

    def on_closing(self) -> None:
        """Clean up hardware and model resources before destroying window."""
        if self.cap is not None:
            self.cap.release()
        self.vision.close()
        self.root.destroy()


def main() -> None:
    """Application entry point."""
    root = tk.Tk()
    app = FitnessApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()