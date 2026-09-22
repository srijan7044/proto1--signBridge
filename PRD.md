# SignBridge — Product Requirements Document (PRD)

## 1. Document Control

| Field | Value |
|---|---|
| **Document Title** | SignBridge — Bi-Directional Sign Language Communicator |
| **Owner** | Hand Gesture Research Team |
| **Project ID** | SBR-2026 |
| **Status** | Draft |
| **Version** | 1.0 |
| **Created** | 2026-09-21 |
| **Last Updated** | 2026-09-21 |

---

## 2. Overview

### 2.1 Purpose
SignBridge is an end-to-end, bi-directional communication accessibility suite designed to bridge communication between Deaf/Hard-of-Hearing/Mute individuals and Hearing individuals. The platform provides two complementary communication flows:

1. **Sign-to-Speech**: Deaf/Mute users sign into a webcam; the system interprets hand gestures in real-time, constructs words and sentences, and speaks them aloud.
2. **Speech-to-Sign**: Hearing users speak or type text; the system generates an animated 3D skeleton hand gesture sequence representing the equivalent sign language.

### 2.2 Problem Statement
Deaf, mute, and hard-of-hearing individuals face significant communication barriers in daily interactions. Existing solutions are either expensive, require specialized hardware, or only solve one direction of communication. SignBridge provides a single, unified, software-only platform that requires only a standard webcam and browser, making sign language communication accessible to anyone.

### 2.3 Goals & Objectives

| Goal | Metric | Target |
|---|---|---|
| Real-time sign recognition accuracy | Confidence rate on test dataset | >85% for single-letter, >80% for common words |
| Word construction accuracy | Autocorrect success rate | >95% of common misspellings corrected |
| Grammar synthesis quality | Human-rated fluency score | >4.0/5.0 |
| Application startup time | Server cold start | <3 seconds |
| Authentication reliability | OTP delivery success rate | >98% |

---

## 3. Stakeholders

### 3.1 User Personas

#### Persona 1: Deaf/Mute Communicator
- **Name**: Aisha Patel
- **Age**: 34
- **Background**: Librarian, fluent in Indian Sign Language (ISL) and American Sign Language (ASL)
- **Needs**: Communicate with hearing customers and colleagues in real-time without an interpreter
- **Technical Comfort**: Intermediate — comfortable with web applications and webcam usage
- **Devices**: Laptop with built-in webcam, smartphone for voice backup

#### Persona 2: Hearing Partner
- **Name**: Robert Chen
- **Age**: 45
- **Background**: Store manager, interacts with Deaf customers regularly
- **Needs**: Understand what Deaf customers are trying to communicate to him
- **Technical Comfort**: Basic — requires intuitive, low-friction interface
- **Devices**: Desktop computer with webcam, tablet

#### Persona 3: Educator/Researcher
- **Name**: Dr. Sarah Martinez
- **Age**: 52
- **Background**: University researcher in Human-Computer Interaction (HCI) and accessibility
- **Needs**: Custom gesture dataset collection, model retraining, academic publication support
- **Technical Comfort**: Advanced — comfortable with CLI tools and Python
- **Devices**: High-end workstation, multiple webcams for research

### 3.2 Business Stakeholders
- **Product Lead**: Defines roadmap and feature prioritization
- **Research Team**: Academic collaborators contributing to gesture recognition algorithms
- **Accessibility Advocates**: External consultants providing feedback on inclusivity

---

## 4. Features & Requirements

### 4.1 Epic A: Sign-to-Speech Translation

#### Feature A.1: Real-Time Webcam Hand Tracking
| Requirement ID | Requirement |
|---|---|
| A.1.1 | The application shall capture video from a standard webcam at 640×480 resolution |
| A.1.2 | The application shall use MediaPipe Hands to detect up to 2 hands and extract 21 3D landmarks per hand (x, y, z coordinates) |
| A.1.3 | The application shall normalize landmarks to be translation-invariant (wrist at origin) and scale-invariant (normalized by palm size) |
| A.1.4 | The application shall support both single-hand and dual-hand gesture detection |
| A.1.5 | The application shall draw hand skeleton overlays with landmarks and connections |

#### Feature A.2: Gesture Classification
| Requirement ID | Requirement |
|---|---|
| A.2.1 | The application shall classify hand gestures using a trained RandomForestClassifier model (sign_classifier.joblib) |
| A.2.2 | The model shall be loaded lazily at first request and cached in memory |
| A.2.3 | The application shall output the top prediction label and confidence score |
| A.2.4 | The application shall reject predictions where confidence < 0.55 (MIN_CONFIDENCE) |
| A.2.5 | The application shall reject predictions where the confidence margin between top-1 and top-2 classes < 0.05 (MIN_MARGIN) |
| A.2.6 | The application shall require a sign to appear consistently across a stability window of 5 frames with >= 60% agreement (STABILITY_THRESHOLD) to confirm a sign |
| A.2.7 | The application shall enforce a minimum 0.7-second (REPEAT_COOLDOWN) gap before the same sign can be confirmed twice |

#### Feature A.3: Letter-to-Word Construction
| Requirement ID | Requirement |
|---|---|
| A.3.1 | The application shall collect single-letter signs (A-Z) into a word buffer displayed as interactive chip UI elements |
| A.3.2 | The application shall provide real-time Levenshtein-distance-based spell autocorrection (e.g., "THAMKS" → "THANKS", "HELO" → "HELLO", "WATR" → "WATER") |
| A.3.3 | The application shall support maximum edit distance of 2 for autocorrection |
| A.3.4 | The application shall provide prefix-based autocomplete suggestions from a dictionary of 100+ core vocabulary words |
| A.3.5 | The application shall allow users to manually commit the corrected word to the sentence builder or select a suggestion chip |
| A.3.6 | The application shall allow backspace deletion of the last letter in the word buffer |
| A.3.7 | The application shall allow clearing the entire word buffer |

#### Feature A.4: Sentence Assembly & Output
| Requirement ID | Requirement |
|---|---|
| A.4.1 | The application shall display the assembled sentence in an editable text area |
| A.4.2 | The application shall support space, backspace, and clear operations via keyboard shortcuts |
| A.4.3 | The application shall provide text-to-speech (TTS) output via Web Speech API (browser) or pyttsx3 (desktop) |
| A.4.4 | The application shall support auto-speak mode that speaks each confirmed sign automatically |
| A.4.5 | The application shall flash the sentence input border green on new word addition |

#### Feature A.5: AI Grammar Synthesis
| Requirement ID | Requirement |
|---|---|
| A.5.1 | The application shall convert sign gloss sentences (e.g., "ME WANT WATER") into grammatically fluent English (e.g., "I would like some water, please.") |
| A.5.2 | The application shall handle WH-question reordering (e.g., "YOU NAME WHAT" → "What is your name?") |
| A.5.3 | The application shall support pronoun mapping (ME → I, MY → my, YOU → you, etc.) |
| A.5.4 | The application shall apply proper capitalization and punctuation (periods for statements, question marks for questions) |
| A.5.5 | The application shall use a curated dictionary of 50+ common ASL/ISL gloss-to-English phrase patterns |
| A.5.6 | The application shall provide predictive next-word suggestion chips based on context |

### 4.2 Epic B: Speech-to-Sign Animation

#### Feature B.1: Voice & Text Input
| Requirement ID | Requirement |
|---|---|
| B.1.1 | The application shall support browser-based speech recognition using the Web Speech API |
| B.1.2 | The application shall display real-time interim speech recognition results |
| B.1.3 | The application shall support manual text input as a fallback to voice |
| B.1.4 | The application shall provide quick-phrase chips for common messages ("Hello", "Thank you", "Yes", "No", "Good job", "Help me") |

#### Feature B.2: Sign Language Animation
| Requirement ID | Requirement |
|---|---|
| B.2.1 | The application shall convert English text sentences into sign language gloss sequences of individual letters |
| B.2.2 | The application shall generate 3D hand skeleton animation frames from the gloss sequence |
| B.2.3 | The application shall interpolate 6 transition frames between consecutive letter signs |
| B.2.4 | The application shall support animation playback with play, pause, replay, and speed controls (0.5x, 1.0x, 1.5x) |
| B.2.5 | The application shall render hand skeletons on an HTML5 canvas with wrist anchor positioning |
| B.2.6 | The application shall display a per-frame caption indicating which word is being signed |
| B.2.7 | The application shall render gloss pill badges for word identification |

#### Feature B.3: Fingerspelling Fallback
| Requirement ID | Requirement |
|---|---|
| B.3.1 | The application shall fingerspell unrecognized words letter-by-letter |
| B.3.2 | The application shall retrieve real landmark data from the SignAlphaSet dataset for known letters |
| B.3.3 | The application shall generate synthetic hand pose landmarks as a fallback when dataset data is unavailable |

### 4.3 Epic C: User Authentication & Profiles

#### Feature C.1: Passwordless Authentication
| Requirement ID | Requirement |
|---|---|
| C.1.1 | The application shall support passwordless authentication via Clerk Email OTP |
| C.1.2 | The application shall provide a local simulated OTP mode for development when Clerk SDK keys are not configured |
| C.1.3 | The application shall support real-time Clerk JS SDK integration with dynamic appearance theming |
| C.1.4 | The application shall store user session tokens in localStorage for persistence |
| C.1.5 | The application shall support sign-out functionality that clears all session data |

#### Feature C.2: User Profile Management
| Requirement ID | Requirement |
|---|---|
| C.2.1 | The application shall sync user profile data (clerk_id, email, name, image_url) to MongoDB |
| C.2.2 | The application shall store user preferences (preferred sign system: ASL/ISL, speech rate) |
| C.2.3 | The application shall display user avatar, display name, and membership plan in the topbar |
| C.2.4 | The application shall lock the application shell until the user authenticates |

#### Feature C.3: Auth Gate UI
| Requirement ID | Requirement |
|---|---|
| C.3.1 | The application shall display an auth gate screen with a hero pane and sign-in form when the user is not authenticated |
| C.3.2 | The auth gate shall include a fallback email OTP form with email entry and code verification steps |
| C.3.3 | The application shall provide real-time status feedback during OTP send and verification |

### 4.4 Epic D: Subscription & Monetization

#### Feature D.1: Subscription Tiers
| Requirement ID | Requirement |
|---|---|
| D.1.1 | The application shall offer three subscription tiers: Free Explorer, Pro Communicator ($9.99/month), Enterprise & School ($29.99/month) |
| D.1.2 | The application shall display pricing tiers in a modal with feature comparisons |
| D.1.3 | The Free tier shall include core sign-to-speech, text-to-sign, letter-to-word auto-spelling, and 20 saved history items |
| D.1.4 | The Pro tier shall include unlimited AI grammar synthesis, full CSV dataset import/export, cloud sync, and priority recognition |
| D.1.5 | The Enterprise tier shall include custom gesture model training, multi-user classroom support, and dedicated API access |

#### Feature D.2: Stripe Payment Integration
| Requirement ID | Requirement |
|---|---|
| D.2.1 | The application shall integrate with Stripe Checkout for subscription payments |
| D.2.2 | The application shall handle Stripe webhook events for payment success, failure, and refund events |
| D.2.3 | The application shall update user membership plan upon successful payment |
| D.2.4 | The application shall support local simulated payments for development without real Stripe keys |

### 4.5 Epic E: Data Persistence & Dataset Management

#### Feature E.1: MongoDB Integration
| Requirement ID | Requirement |
|---|---|
| E.1.1 | The application shall use MongoDB for persistent storage of user profiles, gesture datasets, payment transactions, and conversation history |
| E.1.2 | The application shall automatically fall back to an in-memory database if MongoDB is unreachable, ensuring core recognition features remain functional |
| E.1.3 | The application shall store conversation/translation history with raw gloss, translated sentence, and timestamp |
| E.1.4 | The application shall retrieve recent conversation history (limit 25 items) per user |

#### Feature E.2: Gesture Dataset Management
| Requirement ID | Requirement |
|---|---|
| E.2.1 | The application shall support CSV-based gesture dataset import/export |
| E.2.2 | The dataset CSV format shall include label and 126-dimensional landmark feature columns |
| E.2.3 | The application shall maintain two primary datasets: `gestures_letters_self.csv` (31,200+ samples) and `gestures_letters_SignAlphaSet_1.csv` (25,890+ samples) |
| E.2.4 | The application shall support gesture data collection via webcam with configurable sample count |

#### Feature E.3: Model Training
| Requirement ID | Requirement |
|---|---|
| E.3.1 | The application shall provide a CLI tool (`train_model.py`) for training/retraining the RandomForest gesture classifier |
| E.3.2 | The trained model shall be saved as a joblib file (sign_classifier.joblib) |
| E.3.3 | The model labels shall be saved as a separate joblib file (labels.joblib) |

### 4.6 Epic F: Desktop CLI & Research Utilities

#### Feature F.1: Research Tools
| Requirement ID | Requirement |
|---|---|
| F.1.1 | The application shall provide a real-time desktop webcam translator (`realtime_translate.py`) using OpenCV GUI |
| F.1.2 | The application shall provide a data collection tool (`collect_data.py`) for gathering custom gesture datasets |
| F.1.3 | The application shall provide a video generation tool (`text_to_sign.py`) for rendering sign language videos from text |
| F.1.4 | The application shall provide a landmark normalization utility (`normalization.py`) |
| F.1.5 | The application shall provide a quick diagnostic tool (`quick_test.py`) for model evaluation |

#### Feature F.2: Document Generation
| Requirement ID | Requirement |
|---|---|
| F.2.1 | The application shall include academic documentation in IEEE conference paper format (PDF and Word) |
| F.2.2 | The application shall provide a document generation tool (`generate_documents.py`) for creating research papers |

---

## 5. Technical Architecture

### 5.1 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                            Browser                            │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    web/index.html                        │  │
│  │         web/style.css — Glassmorphic UI                  │  │
│  │  web/app.js — Camera, Auth, Stripe, Word Builder        │  │
│  └──────────┬───────────────────────┬──────────────────┘  │
│             │                       │                        │
│     [Webcam Stream]        [Stripe Checkout]                  │
│             │                       │                        │
└────────────┼───────────────────────┼────────────────────────┘
             │                       │
┌────────────▼──────────────────────▼────────────────────────┐
│                       Backend Server (Flask)               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  server.py — Root entrypoint                          │ │
│  │                                                        │ │
│  │  backend/config.py — Centralized config & .env loader │ │
│  │  backend/db.py — MongoDB + in-memory fallback          │ │
│  │  backend/app.py — Flask app factory                   │ │
│  │                                                        │ │
│  │  backend/routes/                                        │ │
│  │    └── auth_routes.py  — /api/auth/*                   │ │
│  │    └── payment_routes.py — /api/payment/*              │ │
│  │    └── gesture_routes.py — /api/gestures/*             │ │
│  │    └── translate_routes.py — /api/*                    │ │
│  │                                                        │ │
│  │  backend/models/                                        │ │
│  │    └── user_model.py — User profiles & preferences     │ │
│  │    └── gesture_model.py — Landmark dataset records     │ │
│  │    └── payment_model.py — Stripe transactions           │ │
│  │    └── history_model.py — Conversation logs             │ │
│  │                                                        │ │
│  │  backend/utils/                                         │ │
│  │    └── clerk_auth.py — JWT validation decorators       │ │
│  │    └── word_engine.py — Word construction + grammar     │ │
│  │    └── helpers.py — API response utilities              │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
             │                       │
             │          MongoDB (Cloud/Local)
             │                        │
             ▼                        ▼
┌──────────────────────┐  ┌──────────────────────────────────┐
│    model/             │  │          data/                   │
│ sign_classifier.joblib│  │ gestures_letters_self.csv         │
│ labels.joblib         │  │ gestures_letters_SignAlphaSet_1.csv │
└──────────────────────┘  └──────────────────────────────────┘
```

### 5.2 Technology Stack

| Layer | Technology | Version/Notes |
|---|---|---|
| **Frontend** | HTML5, CSS3 (Glassmorphic), Vanilla JavaScript (ES6+) | No framework — direct DOM manipulation |
| **Backend** | Python 3.11, Flask 3.x | RESTful API architecture |
| **Computer Vision** | MediaPipe 0.10.14, OpenCV 4.8+ | Hand landmark extraction |
| **Machine Learning** | scikit-learn 1.5+, joblib 1.4+ | RandomForestClassifier |
| **Data Processing** | numpy 1.26+, pandas 2.2+ | Feature extraction & normalization |
| **Authentication** | Clerk Email OTP | JWT with JWKS validation |
| **Payments** | Stripe Checkout | Webhook event handling |
| **Database** | MongoDB 4.6+ (PyMongo) | With in-memory fallback |
| **Text-to-Speech** | Web Speech API (browser), pyttsx3 | Dual-path TTS |
| **Deployment** | Single-file Python server | `python server.py` |

### 5.3 Data Flow

#### 5.3.1 Sign-to-Speech Pipeline
```
Webcam Frame → MediaPipe Hands (21 landmarks × 2 hands) → 
Normalized Feature Vector (126-D) → RandomForestClassifier → 
Predicted Label + Confidence → Stability Window Filter → 
Letter Buffer / Word Commit → Sentence Building → 
AI Grammar Synthesis → Text-to-Speech Output
```

#### 5.3.2 Speech-to-Sign Pipeline
```
Voice Input / Text Input → Web Speech API → 
Text Normalization → Sentence-to-Gloss Tokenization → 
Landmark Frame Generation (from CSV/dataset) → 
Frame Interpolation (6 transition frames) → 
3D Skeleton Animation Render (HTML5 Canvas)
```

### 5.4 Key Algorithms

#### 5.4.1 Hand Landmark Normalization
- **Translation Invariance**: Subtract wrist coordinates (landmark 0) from all landmarks
- **Scale Invariance**: Normalize by palm size (distance from wrist to middle finger MCP at landmark 9)
- **Feature Vector**: 21 landmarks × 3 coordinates × 2 hands = 126-dimensional vector

#### 5.4.2 Stability Filtering
- **Window Size**: 5 most recent predictions
- **Agreement Threshold**: 60% of frames must agree on the same sign
- **Cooldown**: Minimum 0.7 seconds between confirming the same sign
- **Confidence Threshold**: Minimum 0.55 confidence with 0.05 margin to top-2

#### 5.4.3 Levenshtein Autocorrect
- **Algorithm**: Edit distance with optimization to skip words with length difference > 2
- **Max Distance**: 2 character edits (insert, delete, substitute)

#### 5.4.4 Grammar Synthesis
- **Rule-based**: Exact phrase matching (50+ patterns), sub-phrase matching, WH-question reordering
- **Pronoun Alignment**: ASL-to-English pronoun mapping
- **Punctuation**: Automatic period/question mark application

---

## 6. API Specification

### 6.1 REST API Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/health` | GET | Optional | System health: model readiness, database state, labels count |
| `/api/labels` | GET | — | List of all trained sign gesture labels with count |
| `/api/predict` | POST | — | Predict sign from base64/form-data image frame |
| `/api/text-to-sign` | POST | — | Generate 3D landmark animation sequence from English text |
| `/api/gloss-to-sentence` | POST | Optional | AI grammar synthesis from sign glosses to fluent English |
| `/api/history` | GET | Optional | Recent translation history (limit 25) |
| `/api/gestures/word-construct` | POST | — | Letter buffer autocorrect & prefix autocomplete |
| `/api/gestures/stats` | GET | Optional | Gesture dataset statistics |
| `/api/gestures/import` | POST | Optional | CSV dataset import |
| `/api/gestures/export` | GET | Optional | CSV dataset export |
| `/api/auth/config` | GET | — | Clerk and Stripe publishable configuration keys |
| `/api/auth/sync` | POST | Required | Synchronize Clerk user profile into MongoDB |
| `/api/auth/profile` | GET | Optional | Get user profile and preferences |
| `/api/payment/plans` | GET | — | Available subscription pricing plans |
| `/api/payment/create-checkout-session` | POST | Optional | Create a Stripe Checkout session |
| `/api/payment/webhook` | POST | — | Handle asynchronous Stripe payment events |

### 6.2 Response Format
All API responses follow a standardized envelope:

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

---

## 7. User Interface Design

### 7.1 Design System
- **Theme**: Glassmorphic dark mode (default) with light mode toggle
- **Color Palette**: 
  - Primary: Cyan (#38bdf8) → Blue (#0284c7) gradient
  - Secondary: Indigo (#6366f1) → Violet (#8b5cf6) gradient (AI features)
  - Surfaces: Semi-transparent overlays with backdrop blur
- **Typography**: Inter font family, variable weights (300–800)
- **Radius**: Small (8px), Medium (12px), Large (20px)

### 7.2 UI Components

| Component | Description |
|---|---|
| **Auth Gate** | Full-screen lock screen with hero illustration, Clerk sign-in mount, and fallback OTP form |
| **Mode Tabs** | Tabbed navigation between "Sign to Speech" and "Voice/Text to Sign" modes |
| **Video Container** | Webcam feed with camera-off overlay, skeleton tracking overlay |
| **Capture Controls** | Camera toggle, live tracking toggle, capture frame button |
| **Result Box** | Large display of detected sign label and confidence percentage |
| **Word Assembler** | Letter buffer chips, suggestion chips, commit/backspace/clear controls |
| **Sentence Builder** | Editable text area with grammar polish, delete word, clear, speak buttons |
| **Animation Canvas** | 640×480 HTML5 canvas rendering 3D hand skeleton animations |
| **Playback Controls** | Play/pause, replay, speed selector (0.5x, 1.0x, 1.5x) |
| **Gloss Pills** | Horizontal scrollable list of gloss words with active highlighting |
| **Pricing Modal** | Three-tier subscription comparison with Stripe checkout buttons |
| **Phrase Chips** | Quick-access buttons for common messages in voice-to-sign mode |

### 7.3 Responsiveness
- **Desktop (>900px)**: Two-column workspace layout with side-by-side panels
- **Tablet (768–900px)**: Stacked panels, horizontal auth gate layout switches to vertical
- **Mobile (<768px)**: Single column, condensed controls, touch-friendly button sizes

---

## 8. Performance & Scalability

### 8.1 Performance Targets

| Metric | Target |
|---|---|
| Frame processing latency | <100ms per frame (webcam mode) |
| API response time (predict) | <500ms |
| API response time (text-to-sign) | <1000ms |
| Page load time (first paint) | <1.5 seconds |
| Model load time | <5 seconds |

### 8.2 Scalability Considerations
- Model is loaded once and cached in memory (lazy singleton pattern)
- Database connections use connection pooling via PyMongo
- In-memory fallback database for offline/resilient operation
- Static assets served directly from Flask static folder

### 8.3 Limitations
- Real-time recognition requires a modern browser with MediaPipe support
- Video-to-sign generation is fingerspelling-only (letter-by-letter), not full sign vocabulary animation
- Mobile browser support depends on Web Speech API availability

---

## 9. Data Requirements

### 9.1 Datasets

| Dataset | Description | Samples | Usage |
|---|---|---|---|
| `gestures_letters_self.csv` | Self-collected gesture dataset | 31,200+ | Sign-to-Text classifier training |
| `gestures_letters_SignAlphaSet_1.csv` | SignAlphaSet letter landmarks | 25,890+ | Text-to-Sign 3D animation |
| `gestures.csv` | Core conversational words and phrases | Variable | Additional sign vocabulary |

### 9.2 Data Schema
**Gesture Landmark Record (CSV)**:
- `label`: String sign/letter label (A-Z, word signs)
- 126 float columns: normalized x, y, z coordinates for 21 landmarks × 2 hands

**User Profile (MongoDB)**:
- `clerk_id`: Unique user identifier
- `email`, `first_name`, `last_name`, `image_url`: Profile data
- `membership_plan`: "free", "pro", "enterprise", "lifetime"
- `preferences`: Sign system (ASL/ISL), speech rate, theme

**Translation History (MongoDB)**:
- `user_id`, `raw_gloss`, `translated_sentence`, `timestamp`

---

## 10. Security & Compliance

### 10.1 Authentication
- Passwordless authentication via Clerk Email OTP
- JWT token validation with JWKS endpoint verification
- Bearer token authentication for protected API endpoints

### 10.2 Data Protection
- User profile data synchronized via authenticated backend endpoints
- No raw video frames stored persistently (processed in-memory)
- Session tokens stored in localStorage with appropriate security context

### 10.3 Stripe Integration
- Stripe publishable key exposed client-side (by design)
- Stripe secret key used server-side only in webhook handlers
- Webhook events verified via endpoint signature

### 10.4 Environment Variables
The following sensitive values must be provided via `.env`:
- `CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- `MONGO_URI`, `MONGO_DB_NAME`
- `STRIPE_PRICE_PRO_MONTHLY`, `STRIPE_PRICE_LIFETIME`

---

## 11. Deployment & Operations

### 11.1 Prerequisites
- Python 3.11+
- Virtual environment with dependencies from `requirements.txt`
- `.env` file with required configuration keys
- Webcam (recommended: 720p or higher)
- MongoDB (optional — auto-falls back to in-memory)

### 11.2 Installation

```bash
git clone <repository_url>
cd handgesture-research

python -m venv .venv
.venv\Scripts\activate  # Windows
# or: source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

### 11.3 Running the Application

```bash
python server.py
```

Access at `http://127.0.0.1:5000`.

### 11.4 CLI Utilities

| Command | Purpose |
|---|---|
| `python train_model.py` | Train/retrain the gesture classifier |
| `python collect_data.py --label MY_SIGN --samples 300` | Collect custom gesture data |
| `python realtime_translate.py` | Desktop real-time sign translator (OpenCV GUI) |
| `python text_to_sign.py --sentence "Hello thank you" --output out.mp4` | Generate sign language video |
| `python normalization.py --input data/gestures.csv` | Normalize landmark dataset |
| `python quick_test.py` | Quick model diagnostic |

---

## 12. Success Metrics

### 12.1 Technical KPIs
| Metric | Baseline | Target |
|---|---|---|
| Sign recognition accuracy | TBD | >80% |
| Autocorrect accuracy | TBD | >95% |
| Grammar synthesis accuracy | TBD | >85% |
| API uptime | N/A | 99.5% |
| Authentication success rate | N/A | >98% |

### 12.2 User Experience KPIs
| Metric | Target |
|---|---|
| First-time user can complete a sign-to-speech cycle | <2 minutes |
| First-time user can complete a speech-to-sign cycle | <1 minute |
| Authentication flow completion rate | >90% |
| Subscription conversion rate (Free to Pro) | >5% |

### 12.3 Research KPIs
| Metric | Target |
|---|---|
| Gestures in active dataset | >50,000 samples |
| Supported sign labels | >100 distinct signs |
| Academic paper acceptance rate | Target IEEE conference paper |

---

## 13. Future Roadmap

### 13.1 Phase 1 (Near-term)
- [ ] Expand gesture vocabulary to 250+ signs
- [ ] Add ISL (Indian Sign Language) specific dataset
- [ ] Implement offline-first PWA support
- [ ] Add mobile app (React Native) with camera integration
- [ ] Implement batch dataset import/export via UI

### 13.2 Phase 2 (Mid-term)
- [ ] Add two-hand gesture support for complex signs
- [ ] Implement real sign language video synthesis (not just fingerspelling)
- [ ] Add sign language learning mode with guided tutorials
- [ ] Implement multi-user classroom mode for educators
- [ ] Add voice-to-speech relay for hearing-impaired users

### 13.3 Phase 3 (Long-term)
- [ ] Integrate large language model for contextual grammar correction
- [ ] Add emotion detection in sign language
- [ ] Implement custom model training UI for enterprise users
- [ ] Support regional sign language variants globally
- [ ] Deploy as a cloud service with dedicated GPU inference

---

## 14. Appendices

### 14.1 Configuration Constants

| Constant | Value | Description |
|---|---|---|
| `STABILITY_WINDOW` | 5 | Frames to analyze for sign confirmation |
| `STABILITY_THRESHOLD` | 0.60 | Agreement fraction required |
| `REPEAT_COOLDOWN` | 0.7s | Minimum gap between same sign confirmations |
| `MIN_CONFIDENCE` | 0.55 | Minimum prediction confidence |
| `MIN_MARGIN` | 0.05 | Confidence gap to top-2 class |
| `FEATURE_VECTOR_LENGTH` | 126 | 21 landmarks × 3 coords × 2 hands |
| `TRANSITION_FRAMES` | 6 | Interpolated frames between signs |

### 14.2 Pricing Configuration

| Plan | Price | Key Features |
|---|---|---|
| Free Explorer | $0/month | Webcam recognition, text-to-sign, 20 history items |
| Pro Communicator | $9.99/month | Unlimited AI grammar, CSV export, cloud sync |
| Enterprise & School | $29.99/month | Custom models, classroom multi-user, dedicated API |
| Lifetime | $79.99 (one-time) | All current + future features |

### 14.3 File Inventory

| Path | Description |
|---|---|
| `server.py` | Root entrypoint — launches Flask app |
| `backend/` | Modular Python backend (config, db, app, models, routes, utils) |
| `web/` | Frontend (index.html, style.css, app.js) |
| `data/` | Gesture datasets (CSV) |
| `model/` | Trained ML model (joblib files) |
| `text_to_sign.py` | Text-to-sign animation generator |
| `realtime_translate.py` | Desktop real-time translator |
| `train_model.py` | Model training utility |
| `collect_data.py` | Gesture data collection tool |
| `normalization.py` | Landmark normalization utility |
| `quick_test.py` | Model diagnostic tool |
| `synthetic_data_generator.py` | Synthetic landmark data generator |
| `generate_documents.py` | Research paper generator |
| `camera_diagnostic.py` | Webcam diagnostics |
| `troubleshoot.py` | Troubleshooting utility |
| `requirements.txt` | Python dependencies |
| `.env` | Environment configuration |
| `SignBridge_IEEE_Conference_Paper.pdf` | Academic paper (PDF) |
| `SignBridge_IEEE_Conference_Paper.docx` | Academic paper (Word) |
