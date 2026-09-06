# SignBridge — Bi-Directional Sign Language Communicator

A real-time, bi-directional accessibility application designed for **deaf, mute, and hearing individuals** to converse effortlessly using hand sign recognition, voice input, text-to-speech, and animated sign language generation.

---

## 🌟 Key Features

1. **🖐️ Sign to Speech (Deaf/Mute $\rightarrow$ Hearing Partner)**
   - **Real-Time Webcam Recognition**: MediaPipe Hands extracts 21 3D landmarks per hand with strict Left/Right slot normalization.
   - **Live Prediction & Auto-Speak**: Instant machine learning classification with automated text-to-speech output so hearing partners can listen.
   - **Frame Capture & Image Upload**: Capture camera snapshots or upload photo files for offline sign prediction.

2. **🗣️ Voice & Text to Sign (Hearing Partner $\rightarrow$ Deaf/Mute)**
   - **Browser Voice Input**: Web Speech API listens to the hearing user's voice and converts speech to text in real time.
   - **Sign Language Skeleton Renderer**: Converts spoken or typed text into simplified sign gloss sequences and animates stick-figure hand skeletons on an interactive HTML5 canvas.
   - **Fingerspelling Fallback**: Missing vocabulary words are automatically fingerspelled letter-by-letter.
   - **Playback Controls**: Play, pause, replay, and adjust animation speed (0.5x, 1.0x, 1.5x).

3. **📚 Rich Day-to-Day Vocabulary (23+ Signs Trained)**
   - **Greetings & Manners**: `HELLO`, `GOODBYE`, `THANKS`, `PLEASE`, `SORRY`, `WELCOME`
   - **Questions & Responses**: `YES`, `NO`, `GOOD`, `BAD`, `HELP`, `NEED`, `WHAT`, `WHERE`
   - **Needs & Feelings**: `WATER`, `FOOD`, `HAPPY`, `SAD`, `LOVE`
   - **Daily Entities & Time**: `NAME`, `FRIEND`, `WORK`, `TIME`

4. **✨ Modern Glassmorphic Web Portal**
   - High contrast dark/light mode UI built with Vanilla CSS variables and accessible controls.

---

## 📁 Project Structure

```
handgesture-research/
├── server.py                  # Flask Web Server & REST API (/api/predict, /api/text-to-sign)
├── utils.py                   # Anatomical landmark normalization & strict Left/Right slot feature extraction
├── collect_data.py            # Record webcam training samples for custom gestures
├── train_model.py             # Train RandomForestClassifier on gesture dataset
├── realtime_translate.py      # Desktop real-time webcam sign language translator
├── record_sign_clip.py        # Record motion clips for sign language generation
├── text_to_sign.py            # Text-to-gloss & landmark sequence generator with fingerspelling fallback
├── verify_generation.py       # Automated round-trip verification of generated sign clips
├── synthetic_data_generator.py # Physical hand pose generator for 23+ daily gestures
├── troubleshoot.py            # Comprehensive system diagnostic script
├── quick_test.py              # Quick model prediction verification tool
├── camera_diagnostic.py       # Scan and test available camera devices
├── requirements.txt           # Pinned dependency requirements
├── web/                       # Web Application Frontend
│   ├── index.html             # Bi-directional dual-mode UI
│   ├── style.css              # Glassmorphic responsive styling
│   └── app.js                 # Web Speech API, camera capture & skeleton canvas renderer
├── data/                      # Dataset CSV files (gestures.csv)
└── model/                     # Trained machine learning model & labels joblib files
```

---

## ⚙️ Setup & Installation

1. **Clone the Repository & Navigate to Folder**:
   ```bash
   git clone <repository_url>
   cd handgesture-research
   ```

2. **Create & Activate Virtual Environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install Pinned Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   > **Note:** Stick to `mediapipe==0.10.14` as pinned in `requirements.txt` to preserve `mp.solutions` API compatibility.

---

## 🚀 Running the Web Application

Launch the web server:
```bash
python server.py
```
Open your browser at **`http://127.0.0.1:5000`**.

* **Tab 1 — Sign to Speech**:
  1. Click **"🎥 Start Camera"**.
  2. Click **"📸 Capture Frame"** or toggle **"⚡ Live Auto-Recognize: ON"**.
  3. The recognized sign is added to your sentence and can be spoken out loud via **"🔊 Speak Aloud"**.
* **Tab 2 — Voice/Text to Sign**:
  1. Click **"🎤 Voice Input"** to speak, or type a sentence into the text box.
  2. Click **"✨ Render Sign Language Animation"**.
  3. Watch the stick-figure hand skeleton perform the sign language animation on screen.

---

## 💻 Running Desktop CLI Tools

### 1. System Diagnostic & Quick Test
```bash
python troubleshoot.py
python quick_test.py
```

### 2. Desktop Real-Time Webcam App
```bash
python realtime_translate.py
```
* **Controls**:
  * `SPACE` $\rightarrow$ Add space
  * `b` $\rightarrow$ Backspace
  * `c` $\rightarrow$ Clear sentence
  * `v` $\rightarrow$ Speak sentence aloud
  * `a` $\rightarrow$ Toggle auto-speak
  * `q` $\rightarrow$ Quit

### 3. Generate Sign Video from Text
```bash
python text_to_sign.py --sentence "Hello thank you" --output sign_output.mp4
```

### 4. Verify Generated Signs
```bash
python verify_generation.py --output sign_output.mp4
```

### 5. Collect Custom Gesture Data & Retrain Model
```bash
python collect_data.py --label MY_CUSTOM_SIGN --samples 300
python train_model.py
```

---

## 🛠️ Troubleshooting

* **Camera Not Detected**:
  Run `python camera_diagnostic.py` to scan for available webcam index numbers (`--camera 0`, `--camera 1`, etc.). Close Zoom, Teams, or Skype if they are locking the camera.
* **Microphone Access in Web Browser**:
  Ensure you open the app on `http://127.0.0.1:5000` or `http://localhost:5000`. Allow microphone permissions when prompted by your browser.
* **Windows Console Encoding**:
  All CLI scripts reconfigure stdout to UTF-8 (`sys.stdout.reconfigure(encoding='utf-8')`) to prevent `UnicodeEncodeError` on Windows `cp1252` terminals.

---

## 📄 License

Developed for sign language accessibility and bi-directional communication research.
