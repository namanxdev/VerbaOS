# Speech-to-Intent Assistive System 🎤🧠

A patient-focused speech-to-intent assistive system designed for stroke/aphasia patients. The system converts short audio recordings into actionable intents, enabling caregivers to quickly understand and respond to patient needs.

> **Built for Microsoft Imagine Cup** - Powered by HuBERT & Wav2Vec2 models on Azure ML

![System Architecture](https://img.shields.io/badge/Azure%20ML-Powered-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![React](https://img.shields.io/badge/React-Frontend-61DAFB)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Supported Intents](#-supported-intents)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [API Documentation](#-api-documentation)
- [Audio Requirements](#-audio-requirements)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)

---

## 🎯 Overview

This assistive system enables patients with speech difficulties to communicate their needs through simple voice commands. The system:

1. **Records** short audio clips (1-3 seconds) from patients
2. **Processes** audio using HuBERT/Wav2Vec2 deep learning models on Azure ML
3. **Detects** intent using embedding-based classification with cosine similarity
4. **Displays** actionable buttons for caregivers to confirm and respond

---

## ✨ Features

- **Real-time Speech Processing** - Process patient speech in under 2 seconds
- **Dual Model Architecture** - HuBERT primary with Wav2Vec fallback for reliability
- **Learning Loop** - System learns from confirmed intents to improve accuracy
- **Neumorphic UI** - Accessible, visually clear interface with dark/light themes
- **Low Confidence Handling** - Shows alternatives when intent is unclear
- **Visual Feedback** - Animated system diagram showing processing stages

---

## 🏗️ System Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   React App     │────▶│   FastAPI       │────▶│   Azure ML      │
│   (Frontend)    │     │   Backend       │     │   (HuBERT/      │
│                 │◀────│                 │◀────│    Wav2Vec2)    │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
      │                        │
      │  Audio Recording       │  Intent Detection
      │  (Web Audio API)       │  + Embedding Storage
      │                        │
      ▼                        ▼
┌─────────────────┐     ┌─────────────────┐
│  16kHz Mono WAV │     │  Intent DB      │
│  Max 3 seconds  │     │  (JSON-based)   │
└─────────────────┘     └─────────────────┘
```

### How It Works

1. **Patient presses "Speak"** on the frontend interface
2. **Frontend records audio** using Web Audio API (auto-stops at 3 seconds)
3. **Audio is converted** to 16kHz mono WAV format
4. **Frontend sends WAV file** to `POST /api/audio`
5. **Backend calls Azure ML** for speech-to-intent processing
6. **Backend returns intent** with confidence score and UI options
7. **Patient/Caregiver confirms** the detected action

---

## 🎯 Supported Intents

| Intent | Description | UI Options |
|--------|-------------|------------|
| `HELP` | Patient needs assistance | Confirm Help, Cancel |
| `EMERGENCY` | Urgent medical situation | Cancel Emergency |
| `WATER` | Patient needs hydration | Confirm Water, Cancel |
| `PAIN` | Patient is in discomfort | Confirm Pain, Where?, Cancel |
| `BATHROOM` | Toileting needs | Confirm Bathroom, Cancel |
| `TIRED` | Rest/sleep needed | Confirm Rest, Cancel |
| `COLD` | Temperature - feels cold | Confirm Cold, Cancel |
| `HOT` | Temperature - feels hot | Confirm Hot, Cancel |
| `YES` | Affirmative confirmation | OK |
| `NO` | Negative/cancellation | OK |

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Azure ML** - HuBERT & Wav2Vec2 model hosting
- **FAISS** - Vector similarity search for intent matching
- **NumPy** - Embedding computations
- **httpx** - Async HTTP client for Azure ML calls

### Frontend
- **React 19** - UI framework
- **Vite** - Build tool and dev server
- **Tailwind CSS 4** - Utility-first styling
- **Framer Motion** - Animations and transitions
- **Radix UI** - Accessible dialog and toast components
- **Axios** - HTTP client

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+** 
- **Node.js 18+** and npm
- **Azure ML** endpoints configured with HuBERT/Wav2Vec models

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd Backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   .\venv\Scripts\activate   # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   
   Create a `.env` file in the `Backend` directory:
   ```env
   # Azure ML - HuBERT (Primary)
   REST_END_POINT__HUBERT=https://your-hubert-endpoint.azureml.net/score
   PRIMARY_KEY__HUBERT=your_hubert_api_key

   # Azure ML - Wav2Vec (Fallback)
   REST_END_POINT__WAVE2VEC=https://your-wav2vec-endpoint.azureml.net/score
   PRIMARY_KEY__WAVE2VEC=your_wav2vec_api_key

   # Server Config (Optional)
   HOST=127.0.0.1
   PORT=8000
   DEBUG=false
   ```

5. **Run the backend server:**
   ```bash
   uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

6. **Verify the API is running:**
   - OpenAPI Docs: http://127.0.0.1:8000/docs
   - ReDoc: http://127.0.0.1:8000/redoc
   - Health Check: http://127.0.0.1:8000/api/health

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure API endpoint (optional):**
   
   Create a `.env` file:
   ```env
   VITE_API_URL=http://127.0.0.1:8000
   ```

4. **Run the development server:**
   ```bash
   npm run dev
   ```

5. **Access the application:**
   
   Open http://localhost:5173 in your browser

---

## 📚 API Documentation

### Endpoints

#### `POST /api/audio`
Process audio and detect intent.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `audio` - WAV file (16kHz, mono, max 3s, max 1MB)

**Response:**
```json
{
  "intent": "WATER",
  "confidence": 0.89,
  "status": "confirmed",
  "ui_options": ["Confirm Water", "Cancel"],
  "next_action": "show_buttons",
  "transcription": null,
  "alternatives": null,
  "embedding_id": "uuid-here",
  "model_used": "HuBERT"
}
```

#### `GET /api/health`
Check system health and ML endpoint status.

**Response:**
```json
{
  "status": "ok",
  "ml_endpoints": {
    "hubert": {"reachable": true},
    "wave2vec": {"reachable": true}
  }
}
```

#### `GET /api/intents`
Get list of available intents.

#### `GET /api/db-stats`
Get embedding database statistics.

---

## 🎤 Audio Requirements

| Parameter | Value |
|-----------|-------|
| Format | WAV |
| Sample Rate | 16000 Hz (16kHz) |
| Channels | Mono (1 channel) |
| Bit Depth | 16-bit |
| Max Duration | 3 seconds |
| Max File Size | 1 MB |

---

## 📁 Project Structure

```
Imagine_cup_Backend/
├── Backend/
│   ├── main.py                  # FastAPI application entry point
│   ├── requirements.txt         # Python dependencies
│   ├── intent_embeddings.json   # Stored intent embeddings (learning)
│   ├── .env                     # Environment variables (create this)
│   └── app/
│       ├── config.py            # Application settings
│       ├── models/
│       │   └── schemas.py       # Pydantic request/response models
│       ├── routes/
│       │   ├── audio.py         # Audio processing endpoints
│       │   └── health.py        # Health check endpoints
│       └── services/
│           ├── azure_ml.py      # Azure ML integration
│           ├── intent_embeddings.py  # Embedding-based classification
│           ├── intent_logic.py  # Intent detection logic
│           └── logger.py        # Logging utilities
│
└── frontend/
    ├── package.json             # NPM dependencies
    ├── vite.config.js           # Vite configuration
    ├── tailwind.config.js       # Tailwind CSS config
    └── src/
        ├── App.jsx              # Root React component
        ├── main.jsx             # Application entry point
        ├── index.css            # Global styles
        ├── components/
        │   ├── app/             # Application-specific components
        │   │   ├── RecordButton.jsx
        │   │   ├── IntentCard.jsx
        │   │   ├── ActionButtons.jsx
        │   │   ├── DiagramLayout.jsx
        │   │   ├── ListeningWave.jsx
        │   │   └── QuickActions.jsx
        │   └── ui/              # Reusable UI components
        │       ├── button.jsx
        │       ├── card.jsx
        │       ├── dialog.jsx
        │       ├── toast.jsx
        │       └── ThemeToggle.jsx
        ├── hooks/
        │   ├── useAudioRecorder.js  # Audio recording hook
        │   └── use-toast.js         # Toast notifications
        ├── pages/
        │   └── Home.jsx         # Main application page
        └── services/
            └── api.js           # Backend API client
```

---

## ⚙️ Configuration

### Backend Settings (`app/config.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_AUDIO_SIZE_BYTES` | 1048576 | Maximum audio file size (1 MB) |
| `MAX_AUDIO_DURATION_SECONDS` | 3 | Maximum recording duration |
| `SAMPLE_RATE` | 16000 | Required audio sample rate |
| `AZURE_ML_TIMEOUT_SECONDS` | 120 | ML endpoint timeout |
| `CONFIDENCE_CONFIRMED` | 0.75 | Threshold for auto-confirmation |
| `CONFIDENCE_NEEDS_CONFIRMATION` | 0.4 | Threshold for showing alternatives |

### Confidence Levels

- **≥ 0.75**: Intent confirmed, show action buttons
- **0.4 - 0.75**: Needs confirmation, show alternatives
- **< 0.4**: Unknown, prompt to repeat

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is developed for the Microsoft Imagine Cup competition.

---

## 🙏 Acknowledgments

- **Microsoft Azure ML** for model hosting infrastructure
- **HuBERT** and **Wav2Vec2** research teams at Meta AI
- **Radix UI** for accessible component primitives
- **Tailwind CSS** for rapid UI development
