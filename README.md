# 🤟 SignBridge — Bi-Directional Sign Language Communicator

SignBridge is an end-to-end, bi-directional accessibility suite designed for **deaf, mute, and hearing individuals** to converse effortlessly. It features real-time hand gesture recognition, fingerspelled letter-to-word construction, AI grammar synthesis, voice input, 3D skeleton animation playback, passwordless Clerk Email OTP authentication, Stripe subscriptions, and MongoDB cloud/local persistence.

---

## 🌟 Key Features

### 1. 🖐️ Sign to Speech (Deaf/Mute $\rightarrow$ Hearing Partner)
- **Real-Time Webcam Recognition**: MediaPipe Hands extracts 21 3D landmarks per hand (126-D normalized feature vectors).
- **Letter-to-Word Constructor**:
  - Live visual letter buffer chips gathered during fingerspelling.
  - **Levenshtein Spell Autocorrection**: Automatically fixes recognition errors (`THAMKS` $\to$ `THANKS`, `HELO` $\to$ `HELLO`, `WATR` $\to$ `WATER`).
  - **Prefix Autocomplete**: Interactive suggestion chips for instant word completion.
- **✨ AI Grammar Synthesis**: Converts disjointed sign glosses (`ME WANT WATER`, `YOU NAME WHAT`) into polite, grammatically fluent English (`"I would like some water, please."`, `"What is your name?"`).
- **Auto-Speak & Spoken Output**: Text-to-speech output so hearing partners can listen aloud.

### 2. 🗣️ Voice & Text to Sign (Hearing Partner $\rightarrow$ Deaf/Mute)
- **Browser Voice Input**: Web Speech API listens to the hearing user's voice and converts speech to text in real time.
- **Sign Language Skeleton Renderer**: Converts spoken or typed text into simplified sign gloss sequences and animates stick-figure hand skeletons on an interactive HTML5 canvas.
- **Fingerspelling Fallback**: Missing vocabulary words are automatically fingerspelled letter-by-letter.
- **Playback Controls**: Play, pause, replay, and adjust animation speed (0.5x, 1.0x, 1.5x).

### 3. 🔐 Clerk Email OTP Authentication
- **Passwordless Sign-In**: Users enter their email and verify with a 6-digit one-time passcode (OTP).
- **Profile Synchronization**: Synchronizes user preferences, preferred sign system (ASL / ISL), and speech rates into MongoDB.
- **Resilient Fallback**: Supports live Clerk JS SDK as well as a local development simulation mode.

### 4. 💳 Stripe Payment Gateway
- **Subscription Tiers**:
  - **Free Explorer**: Core webcam recognition, 3D text-to-sign animations, basic history.
  - **Pro Communicator ($9.99/mo)**: Unlimited AI grammar synthesis, cloud sync, full dataset exports.
  - **Enterprise & School ($29.99/mo)**: Custom model training, classroom multi-user support, dedicated API access.
- **Stripe Checkout Sessions**: Direct integration with Stripe Checkout and automated webhook event handling.

### 5. 🗄️ MongoDB Database Layer with Offline Resilience
- Stores user accounts, gesture landmark datasets, Stripe transaction logs, and conversation transcripts.
- **Resilient In-Memory Mode**: If MongoDB is not running locally, the application automatically switches to an in-memory database so recognition, translation, and UI features continue running smoothly.

---

## 📁 Project Architecture

```
handgesture-research/
├── backend/                      # Modular Python Backend
│   ├── config.py                 # Central config, .env loader & path management
│   ├── db.py                     # MongoDB DatabaseManager with resilient in-memory fallback
│   ├── app.py                    # Flask application factory & blueprint registration
│   ├── models/
│   │   ├── user_model.py         # Clerk user profiles & preferences
│   │   ├── gesture_model.py      # 126-D landmark dataset records & CSV import/export
│   │   ├── payment_model.py      # Stripe checkout sessions & transactions
│   │   └── history_model.py      # Conversation and translation logs
│   ├── routes/
│   │   ├── auth_routes.py        # /api/auth/* (config, sync, profile, preferences)
│   │   ├── payment_routes.py     # /api/payment/* (plans, create-checkout-session, webhook)
│   │   ├── gesture_routes.py     # /api/gestures/* (word-construct, stats, import/export)
│   │   └── translate_routes.py   # /api/* (predict, text-to-sign, gloss-to-sentence, history)
│   └── utils/
│       ├── clerk_auth.py         # Clerk JWT validation decorator (@require_auth, @optional_auth)
│       ├── word_engine.py        # Word construction, Levenshtein corrector & grammar engine
│       └── helpers.py            # BSON/ObjectId serialization & api_response envelope
├── web/                          # Modern Glassmorphic Frontend
│   ├── index.html                # Bi-directional dual-mode UI + Auth & Stripe Modals
│   ├── style.css                 # Glassmorphic responsive styling & animations
│   └── app.js                    # Camera capture, word builder, Clerk auth & Stripe handling
├── data/                         # Active gesture datasets and CSV files
│   ├── gestures_letters_self.csv            # 31,200+ samples -> Used for Sign-to-Text (Classifier)
│   ├── gestures_letters_SignAlphaSet_1.csv  # 25,890+ samples -> Used for Text-to-Sign (3D Animation)
│   └── gestures.csv                         # Core conversational words and phrase signs
├── model/                        # Trained machine learning model & labels
│   ├── sign_classifier.joblib    # RandomForestClassifier model
│   └── labels.joblib             # Sign label dictionary
├── server.py                     # Root entrypoint launching the Flask application
├── requirements.txt              # Pinned Python package dependencies
└── .env                          # Local environment variables & API keys
```

---

## ⚙️ Setup & Installation

### 1. Clone & Navigate to Folder
```bash
git clone <repository_url>
cd handgesture-research
```

### 2. Create & Activate Virtual Environment
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (`.env`)
Create a `.env` file in the root directory (or edit the existing one):
```env
PORT=5000
DEBUG=True
MONGO_URI=mongodb://localhost:27017/signbridge_db
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PRICE_PRO_MONTHLY=price_...
```

---

## 🚀 Running the Application

### Start the Unified Web Server:
```bash
python server.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your web browser.

---

## 🕹️ Interactive Usage Guide

### 1. Sign to Speech (Deaf/Mute User)
1. Toggle **"Camera: ON"** and activate **"⚡ Live Tracking: ON"**.
2. **Fingerspell letters**: Form signs like `T` $\to$ `H` $\to$ `A` $\to$ `M` $\to$ `K` $\to$ `S`.
3. Watch the **Letter-to-Word Constructor** display your letter chips, auto-correct `THAMKS` $\to$ `THANKS`, and provide autocomplete suggestions.
4. Click **"➕ Commit Word"** or tap any suggestion chip to add the word to your sentence.
5. Click **"✨ AI Polish Grammar"** to refine sign glosses into natural English (`ME WANT WATER` $\to$ *"I would like some water, please."*).
6. Click **"🔊 Speak Aloud"** to hear the sentence spoken.

### 2. Voice/Text to Sign (Hearing Partner)
1. Switch to the **"🗣️ Voice/Text to Sign"** tab.
2. Click **"🎤 Voice Input"** or type a sentence in the message box.
3. Click **"✨ Render Sign Language Animation"**.
4. The animated skeleton will render each sign gloss and fingerspell unfamiliar words.

### 3. User Accounts & Stripe Subscriptions
1. Click **"👤 Sign In (OTP)"** to log in with passwordless email verification.
2. Click **"⭐ Upgrade to Pro"** to view subscription tiers and checkout via Stripe.

---

## 📡 REST API Reference

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/health` | `GET` | Health status, database state, and model readiness |
| `/api/labels` | `GET` | List of all trained sign gesture labels |
| `/api/predict` | `POST` | Predict sign gesture from base64/form-data webcam frame |
| `/api/text-to-sign` | `POST` | Generate 3D landmark animation sequence from English text |
| `/api/gloss-to-sentence` | `POST` | AI grammar synthesis from sign glosses to fluent English |
| `/api/gestures/word-construct` | `POST` | Letter buffer autocorrect & prefix autocomplete |
| `/api/auth/config` | `GET` | Fetch Clerk and Stripe publishable configuration keys |
| `/api/auth/sync` | `POST` | Synchronize Clerk user profile into MongoDB |
| `/api/payment/plans` | `GET` | Retrieve available subscription pricing plans |
| `/api/payment/create-checkout-session` | `POST` | Create a Stripe Checkout session |
| `/api/payment/webhook` | `POST` | Handle asynchronous Stripe payment events |

---

## 💻 Desktop CLI & Research Utilities

- **Train/Retrain Gesture Model**: `python train_model.py`
- **Collect Custom Sign Gestures**: `python collect_data.py --label MY_SIGN --samples 300`
- **Desktop Real-Time Webcam Translator**: `python realtime_translate.py`
- **Generate Sign Video File**: `python text_to_sign.py --sentence "Hello thank you" --output out.mp4`
- **Dataset Landmark Normalizer**: `python normalization.py --input data/gestures.csv`
- **Quick Model Diagnostic**: `python quick_test.py`

---

## 📄 Research & Academic Citation

SignBridge includes full academic documentation and an IEEE conference paper:
- `SignBridge_IEEE_Conference_Paper.docx` (Word format)
- `SignBridge_IEEE_Conference_Paper.pdf` (PDF format)

---

## 📜 License

Developed for sign language accessibility and human-computer interaction (HCI) research.
