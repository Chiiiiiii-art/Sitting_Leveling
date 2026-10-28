# Sitting Leveling (我坐著升級)

A gamified sitting posture and micro-workout fitness tracker powered by Computer Vision and RPG mechanics.

Sitting Leveling turns sedentary workday moments into interactive RPG boss battles. Consumed calories from snacks are converted into the boss's armor shield, while quick micro-workouts (such as squats and neck resistance stretches) break down armor and deal direct boss damage.

---

## Features

- **Real-Time Pose Tracking**: Built-in computer vision pipeline leveraging MediaPipe Pose to track physical movements without wearable sensors.
- **Micro-Workout Detection**:
  - **Head Resistance Stretch (`HEAD`)**: 3-second neutral calibration followed by isometric left/right neck holds.
  - **Body Squat (`SQUAT`)**: Full knee angle computation tracking repetitions from descent (<100°) to upright return (>160°).
- **RPG Battle System**:
  - Boss HP dynamically maps to your target weight loss (1 kg fat ≈ 7,700 kcal).
  - Food intake (e.g. boba tea) adds armor shields to the boss.
  - Completed exercise repetitions deal damage and earn in-game coins.
- **Privacy First**: 100% local on-device video inference. No video streams or images leave your machine. Zero external API dependencies.

---

## Project Structure

```text
Sitting_Leveling/
├── main.py              # Tkinter desktop GUI and application loop
├── vision_engine.py     # MediaPipe pose estimation & exercise state machine
├── rpg_system.py        # Core RPG battle calculations & rewards
├── requirements.txt     # Python package dependencies
├── LICENSE              # MIT License
├── tests/
│   └── test_core.py     # Unit test suite for RPG mechanics & geometry
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.9+
- A working webcam

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/WhitetapeOwO/Sitting_Leveling.git
   cd Sitting_Leveling
   ```

2. (Optional) Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Linux / macOS:
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## Running the Application

Launch the desktop application:

```bash
python main.py
```

### Controls & Simulation
- **Webcam feed**: Displays real-time pose skeleton and exercise progress HUD.
- **模擬紀錄：珍珠奶茶**: Simulates logging high-calorie food (+500 kcal boss armor) and triggers a 5-rep squat quest.
- **模擬行程：連續三小時會議**: Simulates sedentary work alert and triggers a 3-rep head stretch quest.

---

## Running Tests

Run the test suite using Python's built-in `unittest` runner:

```bash
python -m unittest tests/test_core.py
```

---

## License

This project is open-source and licensed under the [MIT License](LICENSE).
