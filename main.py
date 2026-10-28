import cv2
import tkinter as tk
from PIL import Image, ImageTk
from vision_engine import VisionEngine
from rpg_system import RPGSystem

class FitnessApp:
    def __init__(self, root):
        self.root = root
        self.root.title("我坐著升級 Sitting Leveling MVP")
        
        self.vision = VisionEngine()
        self.rpg = RPGSystem(target_weight_loss_kg=1.0)
        
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.build_ui()
        self.update_frame()

    def build_ui(self):
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(padx=10, pady=10)
        
        self.video_label = tk.Label(self.main_frame)
        self.video_label.grid(row=0, column=0, padx=10)
        
        self.panel_frame = tk.Frame(self.main_frame, width=300)
        self.panel_frame.grid(row=0, column=1, sticky="n", padx=10)
        
        # 任務狀態提示
        self.task_label = tk.Label(self.panel_frame, text="當前狀態: 待機中", font=("Arial", 14), fg="green")
        self.task_label.pack(pady=10, anchor="w")
        
        self.hp_label = tk.Label(self.panel_frame, text="", font=("Arial", 16))
        self.hp_label.pack(pady=5, anchor="w")
        
        self.armor_label = tk.Label(self.panel_frame, text="", font=("Arial", 16))
        self.armor_label.pack(pady=5, anchor="w")
        
        self.coin_label = tk.Label(self.panel_frame, text="", font=("Arial", 16))
        self.coin_label.pack(pady=5, anchor="w")
        
        self.msg_text = tk.Text(self.panel_frame, height=5, width=30, state=tk.DISABLED)
        self.msg_text.pack(pady=10)
        
        tk.Button(self.panel_frame, text="模擬紀錄：珍珠奶茶", command=self.mock_event_boba).pack(fill="x", pady=5)
        tk.Button(self.panel_frame, text="模擬行程：連續三小時會議", command=self.mock_event_meeting).pack(fill="x", pady=5)
        
        self.refresh_rpg_ui()

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            processed_frame, event_data = self.vision.process_frame(frame)
            
            # 更新介面上的任務狀態
            if event_data["mission"] != "IDLE":
                self.task_label.config(text=f"任務執行中: {event_data['mission']} ({event_data['progress']})", fg="red")
            else:
                self.task_label.config(text="當前狀態: 待機中", fg="green")
            
            # 處理回傳事件
            if event_data["event"] == "ACTION_SUCCESS":
                damage = self.rpg.process_action_success(base_calories_burned=10, coin_reward=5)
                self.log_message(f"動作完成 1 次！造成 {damage} 點傷害。")
                self.refresh_rpg_ui()
            elif event_data["event"] == "MISSION_CLEARED":
                self.log_message(f"任務達成！警示解除，回歸待機狀態。")
                self.vision.set_mission("IDLE", 0)
            
            img = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
            
        self.root.after(30, self.update_frame)

    def refresh_rpg_ui(self):
        self.hp_label.config(text=f"魔王血量: {self.rpg.current_hp} / {self.rpg.max_hp}")
        self.armor_label.config(text=f"魔王護甲: {self.rpg.armor}")
        self.coin_label.config(text=f"帶薪金幣: {self.rpg.coins}")

    def log_message(self, msg):
        self.msg_text.config(state=tk.NORMAL)
        self.msg_text.insert(tk.END, msg + "\n")
        self.msg_text.see(tk.END)
        self.msg_text.config(state=tk.DISABLED)

    def mock_event_boba(self):
        self.rpg.add_armor_from_food(500)
        self.refresh_rpg_ui()
        self.log_message("飲食紀錄：珍珠奶茶（+500 大卡）。\n魔王護甲增加 500 點。\n解鎖任務：深蹲 5 次。")
        self.vision.set_mission("SQUAT", 5) # 指派 5 次深蹲任務

    def mock_event_meeting(self):
        self.log_message("行程提醒：接下來有連續會議。\n解鎖任務：頭部對抗伸展 3 次。")
        self.vision.set_mission("HEAD", 3) # 指派 3 次頭部伸展任務

    def on_closing(self):
        self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = FitnessApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()