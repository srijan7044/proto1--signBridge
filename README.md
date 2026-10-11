# 🤟 SignBridge — Bi-Directional Sign Language Communicator

SignBridge is an end-to-end, bi-directional accessibility suite designed for **deaf, mute, and hearing individuals** to converse effortlessly. It features real-time hand gesture recognition, fingerspelled letter-to-word construction, AI grammar synthesis, voice input, 3D skeleton animation playback, passwordless Clerk Email OTP authentication, Stripe subscriptions with usage tracking, multilingual support, custom model training with admin review, and MongoDB cloud/local persistence.

---

## 🌟 Key Features

### 1. 🖐️ Sign to Speech (Deaf/Mute → Hearing Partner)
- **Real-Time Webcam Recognition**: MediaPipe Hands extracts 21 3D landmarks per hand (126-D normalized feature vectors).
- **Letter-to-Word Constructor**:
  - Live visual letter buffer chips gathered during fingerspelling.
  - **Levenshtein Spell Autocorrection**: Automatically fixes recognition errors (`THAMKS` → `THANKS`, `HELO` → `HELLO`, `WATR` → `WATER`).
  - **Prefix Autocomplete**: Interactive suggestion chips for instant word completion.
- **✨ AI Grammar Synthesis**: Converts disjointed sign glosses (`ME WANT WATER`, `YOU NAME WHAT`) into polite, grammatically fluent English (`"I would like some water, please."`, `"What is your name?"`).
- **Auto-Speak & Spoken Output**: Text-to-speech output so hearing partners can listen aloud.

### 2. 🗣️ Voice & Text to Sign (Hearing Partner → Deaf/Mute)
- **Browser Voice Input**: Web Speech API listens to the hearing user's voice and converts speech to text in real time.
- **Sign Language Skeleton Renderer**: Converts spoken or typed text into simplified sign gloss sequences and animates stick-figure hand skeletons on an interactive HTML5 canvas.
- **Fingerspelling Fallback**: Missing vocabulary words are automatically fingerspelled letter-by-letter.
- **Playback Controls**: Play, pause, replay, and adjust animation speed (0.5x, 1.0x, 1.5x).

### 3. 🔐 Clerk Email OTP Authentication
- **Passwordless Sign-In**: Users enter their email and verify with a 6-digit one-time passcode (OTP).
- **Profile Synchronization**: Synchronizes user preferences, preferred sign system (ASL / ISL), and speech rates into MongoDB.
- **Resilient Fallback**: Supports live Clerk JS SDK as well as a local development simulation mode.

### 4. 💳 Stripe Payment Gateway & Subscription System
- **Subscription Tiers**:
  - **Free Tier — $0/mo**: 4 productive hours/month, English (ASL) only, core features
  - **Premium — $29.48/mo**: Unlimited productive usage, 12+ Indian languages (ISL), AI Assistant (coming soon), regional language access
  - **Lifetime — $2,000 one-time**: Lifetime unlimited access, all regional languages, AI Assistant, no recurring charges
  - **Custom Model Training — $15 one-time**: Request custom sign language model for your language
- **Productive Usage Tracking**: Server-side heartbeat-based tracking (30s intervals), 4-hour monthly allowance for Free users with automatic reset
- **INR Pricing Display**: Real-time USD→INR conversion with configurable exchange rate
- **Stripe Checkout Sessions**: Direct integration with ad-hoc price creation, managed_payments disabled for test accounts
- **Complete Webhook Handling**: `checkout.session.completed`, `customer.subscription.*`, `invoice.payment_*` events
- **Subscription Lifecycle**: Automatic downgrade on cancellation, renewal handling, failed payment retry logic

### 5. 🌍 Multilingual Support & Language Registry
- **19+ Supported Languages**: English, Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Odia, Assamese, Spanish, French, German, Chinese, Japanese, Korean, Arabic, Portuguese
- **Language Feature Matrix**: Per-language support for sign recognition, text-to-sign, speech-to-text, gloss-to-sentence, fingerspelling
- **Entitlement-Based Access**: Free users get English only; Premium/Lifetime unlock regional languages
- **Language Selector UI**: Modal with native names, flags, variant info, lock indicators for unauthorized languages
- **Admin Language Management**: Activate/deactivate languages, modify metadata, add custom trained languages

### 6. 🎯 Custom Model Training (Admin-Reviewed)
- **Request Submission**: Language name, ISO code, country, variant, use case description, dataset info
- **Payment Integration**: $15 Stripe Checkout for training request
- **Admin Review Workflow**: DRAFT → PAYMENT_PENDING → PAID_PENDING_REVIEW → UNDER_REVIEW → TRAINING → VALIDATING → APPROVED/REJECTED
- **State Machine Validation**: Enforced valid transitions only
- **Model Activation**: Approved models automatically granted to requesting user
- **Validation Metrics Storage**: Training/validation metrics, model metadata, admin notes

### 7. 🛡️ Admin Dashboard & Management
- **System Statistics**: User counts by plan, training request pipeline, monthly revenue
- **User Management**: Paginated list, search, filter by plan, view usage stats
- **Admin Role Management**: Master admin (offsray7044@gmail.com) can grant/revoke admin roles
- **Training Request Management**: View details, approve/reject, request info, final approve with model path
- **Language Registry Management**: Edit language configs, activate/deactivate, add custom languages
- **Payment Monitoring**: Subscription and training payment history
- **Audit Logs**: All admin actions logged with timestamp, actor, target, details

### 8. 📊 Usage Dashboard & Limits
- **Real-Time Progress Bar**: Visual usage tracking for Free users
- **Profile Usage Summary**: Mini usage indicator in user menu
- **Limit Reached Modal**: Clear upgrade options when allowance exhausted
- **Graceful Degradation**: Users retain account access, only productive features blocked

### 9. 🗄️ MongoDB Database Layer with Offline Resilience
- Stores user accounts, gesture landmark datasets, Stripe transaction logs, conversation transcripts, usage sessions, monthly summaries, language registry, training requests, admin action logs
- **Resilient In-Memory Mode**: If MongoDB is not running locally, the application automatically switches to an in-memory database so recognition, translation, and UI features continue running smoothly.

---

## 📁 Project Architecture

```
handgesture-research/
├── backend/                      # Modular Python Backend (Flask)
│   ├── config.py                 # Central config, .env loader & path management
│   ├── db.py                     # MongoDB DatabaseManager with resilient in-memory fallback
│   ├── app.py                    # Flask application factory & blueprint registration
│   ├── models/
│   │   ├── user_model.py         # Clerk user profiles, preferences, subscriptions, admin roles
│   │   ├── gesture_model.py      # 126-D landmark dataset records & CSV import/export
│   │   ├── payment_model.py      # Stripe checkout sessions & transactions
│   │   ├── history_model.py      # Conversation and translation logs
│   │   ├── usage_model.py        # Usage sessions, monthly summaries, entitlements
│   │   ├── language_model.py     # Language registry, access control
│   │   ├── custom_training_model.py  # Training requests, payments, user custom models
│   │   └── admin_model.py        # Admin stats, action logs, authorization
│   ├── routes/
│   │   ├── auth_routes.py        # /api/auth/* (config, sync, profile, preferences)
│   │   ├── payment_routes.py     # /api/payment/* (plans, checkout, verify, webhook, debug)
│   │   ├── gesture_routes.py     # /api/gestures/* (word-construct, stats, import/export)
│   │   ├── translate_routes.py   # /api/* (predict, text-to-sign, gloss-to-sentence, history)
│   │   ├── usage_routes.py       # /api/usage/* (start, heartbeat, stop, current, summary, history)
│   │   ├── language_routes.py    # /api/language/* (list, get, switch, current)
│   │   ├── custom_training_routes.py  # /api/custom-training/* (request, checkout, verify)
│   │   └── admin_routes.py       # /api/admin/* (dashboard, users, requests, languages, payments)
│   └── utils/
│       ├── clerk_auth.py         # Clerk JWT validation decorator (@require_auth, @optional_auth)
│       ├── word_engine.py        # Word construction, Levenshtein corrector & grammar engine
│       └── helpers.py            # BSON/ObjectId serialization & api_response envelope
├── web/                          # Modern Glassmorphic Frontend (Vanilla JS + CSS Modules)
│   ├── index.html                # Landing page with dual-mode UI
│   ├── app.html                  # Main application dashboard
│   ├── pricing.html              # Subscription pricing page
│   ├── style.css                 # Core glassmorphic responsive styling & animations
│   ├── components.css            # Shared UI component styles
│   ├── sign-to-speech.css        # Sign-to-Speech tab styles
│   ├── voice-to-sign.css         # Voice-to-Sign tab styles
│   ├── auth.css                  # Clerk auth modal & OTP styles
│   ├── pricing.css               # Pricing page styles
│   ├── landing.css               # Landing page styles
│   └── js/
│       ├── state.js              # Global reactive state & DOM registry
│       ├── camera.js             # MediaPipe Hands webcam capture & landmark extraction
│       ├── recognition.js        # Sign-to-Text inference & letter buffer management
│       ├── word-builder.js       # Levenshtein autocorrect & prefix autocomplete
│       ├── animation.js          # 3D skeleton animation renderer (canvas)
│       ├── theme.js              # Light/Dark/OS theme persistence & sync
│       ├── auth.js               # Clerk Email OTP authentication flow
│       ├── payments.js           # Stripe Checkout integration (redirectToCheckout + verify)
│       ├── pricing-page.js       # Pricing page UI & plan selection
│       ├── usage.js              # Productive usage tracking & dashboard
│       ├── language.js           # Language selector with entitlement checks
│       ├── custom-training.js    # Custom training request workflow
│       ├── admin.js              # Admin dashboard functionality
│       └── main.js               # App initialization & module orchestration
├── data/                         # Active gesture datasets and CSV files
│   ├── gestures_letters_self.csv             # 31,200+ samples -> Used for Sign-to-Text (Classifier)
│   ├── gestures_letters_SignAlphaSet_1.csv   # 25,890+ samples -> Used for Text-to-Sign (3D Animation)
│   └── gestures.csv                          # Core conversational words and phrase signs
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
# Flask Server
PORT=5000
HOST=127.0.0.1
DEBUG=True
SECRET_KEY=your_secure_random_key

# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017/signbridge_db
MONGO_DB_NAME=signbridge_db

# Clerk Authentication (Email OTP & User Management)
# Get keys at: https://dashboard.clerk.com
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
CLERK_JWKS_URL=https://your-instance.clerk.accounts.dev/.well-known/jwks.json

# Stripe Payment Gateway
# Get keys at: https://dashboard.stripe.com
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PREMIUM_MONTHLY=price_...
STRIPE_PRICE_LIFETIME=price_...
STRIPE_PRICE_CUSTOM_TRAINING=price_...

# Exchange Rate for INR Display
USD_TO_INR_RATE=83.0
EXCHANGE_RATE_PROVIDER=fixed  # fixed, exchangerate-api, openexchangerates
EXCHANGE_RATE_API_KEY=

# Usage Tracking
FREE_MONTHLY_ALLOWANCE_SECONDS=14400  # 4 hours = 14400 seconds
USAGE_HEARTBEAT_INTERVAL_SECONDS=30
USAGE_INACTIVITY_TIMEOUT_SECONDS=120
```

**Important Stripe Notes:**
- The project uses **ad-hoc price creation** via `price_data` in Checkout Sessions (not pre-created Price IDs for development).
- **Managed Payments** is enabled by default on new Stripe test accounts and requires `tax_code` on line items. This project disables it via `managed_payments[enabled]=false` in the Checkout Session to avoid tax configuration complexity in development.
- The `tax_code` `txcd_10000000` (General - Electronically Supplied Services) was tested but caused Checkout page initialization failures (`/payment_pages/.../init` 400) on this account. Disabling Managed Payments is the current workaround.

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
2. **Fingerspell letters**: Form signs like `T` → `H` → `A` → `M` → `K` → `S`.
3. Watch the **Letter-to-Word Constructor** display your letter chips, auto-correct `THAMKS` → `THANKS`, and provide autocomplete suggestions.
4. Click **"➕ Commit Word"** or tap any suggestion chip to add the word to your sentence.
5. Click **"✨ AI Polish Grammar"** to refine sign glosses into natural English (`ME WANT WATER` → *"I would like some water, please."*).
6. Click **"🔊 Speak Aloud"** to hear the sentence spoken.

### 2. Voice/Text to Sign (Hearing Partner)
1. Switch to the **"🗣️ Voice/Text to Sign"** tab.
2. Click **"🎤 Voice Input"** or type a sentence in the message box.
3. Click **"✨ Render Sign Language Animation"**.
4. The animated skeleton will render each sign gloss and fingerspell unfamiliar words.

### 3. User Accounts & Subscriptions
1. Click **"👤 Sign In (OTP)"** to log in with passwordless email verification.
2. Click **"⭐ Upgrade to Pro"** or the user menu to view subscription tiers.
3. Choose a plan (Premium monthly, Lifetime, or Custom Training) and checkout via Stripe.
4. Complete payment with Stripe test card: `4242 4242 4242 4242` (any future date, any CVC).
5. On success, the app verifies the session and upgrades your plan.

### 4. Language Selection (Premium/Lifetime Users)
1. Click the **🌐 Language button** in the top bar (visible for Premium/Lifetime users).
2. Select from available languages — locked languages show upgrade prompts.
3. Click to switch; the app updates your preferred language instantly.

### 5. Custom Model Training
1. Click **"Training"** in user menu or navigate to Custom Training page.
2. Fill out the request form: language name, ISO code, country, variant, use case, dataset info.
3. Submit request → proceed to $15 Stripe payment.
4. After payment, request enters admin review queue.
5. Admin reviews, trains, validates, and approves/rejects.
6. On approval, the custom language becomes available in your language selector.

### 6. Admin Dashboard (Master Admin: offsray7044@gmail.com)
1. Log in as master admin — Admin button appears in user menu.
2. Click **Admin** to access dashboard.
3. Manage users, training requests, languages, view payments, audit logs.
4. Grant/revoke admin roles for sub-admins via user management.

---

## 📡 REST API Reference

### Authentication & User
| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/auth/config` | `GET` | Fetch Clerk and Stripe publishable configuration keys |
| `/api/auth/sync` | `POST` | Synchronize Clerk user profile into MongoDB |
| `/api/auth/profile` | `GET` | Get authenticated user profile |
| `/api/auth/preferences` | `PUT` | Update user preferences (language, sign system, speech) |

### Subscription & Payments
| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/payment/plans` | `GET` | Retrieve all subscription plans with INR pricing |
| `/api/payment/create-checkout-session` | `POST` | Create Stripe Checkout session (plan_id, email) |
| `/api/payment/verify-session` | `POST` | Verify Checkout Session by session_id |
| `/api/payment/webhook` | `POST` | Handle asynchronous Stripe payment events |
| `/api/payment/debug-checkout-session` | `POST` | Debug: create minimal test Checkout Sessions |

### Usage Tracking
| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/usage/start` | `POST` | Start productive usage session |
| `/api/usage/heartbeat` | `POST` | Send heartbeat for active session |
| `/api/usage/stop` | `POST` | Stop usage session |
| `/api/usage/current` | `GET` | Get current active session |
| `/api/usage/summary` | `GET` | Get monthly usage summary with allowance |
| `/api/usage/history` | `GET` | Get 12-month usage history |

### Language Management
| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/language/list` | `GET` | List languages (filtered by user entitlement) |
| `/api/language/<id>` | `GET` | Get language details |
| `/api/language/switch` | `POST` | Switch user's preferred language |
| `/api/language/current` | `GET` | Get user's current language |

### Custom Training
| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/custom-training/request` | `POST` | Create new training request |
| `/api/custom-training/requests` | `GET` | List user's training requests |
| `/api/custom-training/request/<id>` | `GET` | Get specific request details |
| `/api/custom-training/request/<id>/checkout` | `POST` | Create payment checkout for request |
| `/api/custom-training/verify-payment` | `POST` | Verify training payment |

### Admin (Requires Admin Role)
| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/admin/dashboard` | `GET` | System statistics overview |
| `/api/admin/users` | `GET` | Paginated user list with filters |
| `/api/admin/users/<id>/plan` | `POST` | Update user subscription plan |
| `/api/admin/users/<id>/admin` | `POST` | Grant/revoke admin role (master admin only) |
| `/api/admin/training-requests` | `GET` | List all training requests |
| `/api/admin/training-request/<id>` | `GET` | Get training request details |
| `/api/admin/training-request/<id>/status` | `POST` | Update request status |
| `/api/admin/training-request/<id>/approve` | `POST` | Final approve with model path |
| `/api/admin/training-request/<id>/reject` | `POST` | Reject request |
| `/api/admin/languages` | `GET` | List all languages |
| `/api/admin/languages` | `POST` | Update language configuration |
| `/api/admin/languages/custom` | `POST` | Add custom trained language |
| `/api/admin/payments` | `GET` | Recent payment history |
| `/api/admin/action-logs` | `GET` | Admin action audit logs |

### Core Features
| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/health` | `GET` | Health status, database state, model readiness |
| `/api/labels` | `GET` | List of all trained sign gesture labels |
| `/api/predict` | `POST` | Predict sign gesture from base64/form-data webcam frame |
| `/api/text-to-sign` | `POST` | Generate 3D landmark animation sequence from English text |
| `/api/gloss-to-sentence` | `POST` | AI grammar synthesis from sign glosses to fluent English |
| `/api/gestures/word-construct` | `POST` | Letter buffer autocorrect & prefix autocomplete |
| `/api/gestures/stats` | `GET` | Dataset statistics |
| `/api/gestures/import-csv` | `POST` | Import CSV dataset |
| `/api/gestures/export-csv` | `POST` | Export to CSV |
| `/api/history` | `GET` | Recent translation history |

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