# 🔥 PulseHealth - Apple Watch & iPhone 16 Pro Max AI Health Journey

An AI-powered, full-stack health & fitness companion engineered specifically for your **Apple Watch Series 10** and **iPhone 16 Pro Max**, built to help you track fitness stats, effortlessly log nutrition, and receive personalized exercise recommendations for fat loss.

---

## 🌟 Key Features

### 1. ⌚ Apple Watch Series 10 Telemetry Sync
- **Automated Biometrics**: Syncs **Active Calories (Move Ring)**, **Exercise Minutes**, **Stand Hours**, **Steps**, **Resting Heart Rate**, **Heart Rate Variability (HRV)**, **Sleep Duration & Stages**, and **Weight**.
- **Automated iOS Shortcuts Webhook**: Ready-to-use Apple Shortcut configuration sends today's health samples automatically in the background (e.g. daily at 8:30 PM or whenever a workout ends).
- **Manual Quick Sync Fallback**: Allows immediate input or testing from the web interface.

### 2. 🥗 3-Way Smart Food & Macro Logging
- **✨ AI Natural Language Logging (Gemini 3.8 Flash)**: Simply type or speak what you ate (e.g., *"2 scrambled eggs with avocado toast and an iced Americano"*). The AI parses realistic portions, calories, protein, carbs, fats, and fiber.
- **📸 AI Plate Photo Scanner**: Take a picture of your meal plate with your iPhone camera. Gemini Multimodal Vision estimates portions and provides dietitian tips.
- **🏷️ Camera Barcode Scanner + Open Food Facts**: Point your iPhone camera at packaged foods. Automatically decodes barcodes and fetches verified nutrition facts from Open Food Facts in real time.

### 3. ⚡ Science-Based AI Workout & Weight Loss Coach
- **Recovery & Readiness Analysis**: Analyzes your Apple Watch **HRV (ms)** and **Sleep hours** to assess Central Nervous System (CNS) recovery.
- **Dynamic Exercise Prescriptions**:
  - **High Readiness** (High HRV, 7+ hrs sleep): Prescribes progressive resistance training (hypertrophy / compound lifts) to preserve lean muscle mass during a caloric deficit.
  - **Fatigued / Low Sleep** (Low HRV, <6 hrs sleep): Prescribes low-impact **Zone 2 fat oxidation** (incline treadmill walk, light cycling) and mobility, avoiding cortisol spikes that stall fat loss and trigger bingeing.
- **Caloric Deficit Guidance**: Compares your Total Energy Expenditure (BMR + Apple Watch Active Burn) against calories consumed to maintain your ideal 400–600 kcal fat-loss deficit.
- **Interactive Coach Chat**: Ask questions anytime (e.g., *"Can I fit a protein shake tonight?", "My legs are sore, what should I do instead?"*).

### 4. 📱 iPhone 16 Pro Max OLED PWA
- Native-feeling Progressive Web App designed with safe-area spacing for the **Dynamic Island** and bottom home indicator.
- Concentric Apple Health Activity Rings rendered in smooth SVG with neon drop-shadows.

---

## 🚀 Quick Start Guide

### Step 1: Start the Server on your Windows PC
Double-click `run.bat` or run:
```powershell
python start_server.py
```
Your terminal will display your machine's local Wi-Fi address (e.g., `http://192.168.1.45:8000`).

---

### Step 2: Open on your iPhone 16 Pro Max
1. Ensure your iPhone is connected to the same Wi-Fi network as your PC (or connected via Tailscale).
2. Open **Safari** on your iPhone and navigate to `http://<YOUR_PC_IP>:8000`.
3. Tap the **Share** button at the bottom of Safari (the square with an arrow pointing up).
4. Select **"Add to Home Screen"** and tap **Add**.
5. Launch **PulseHealth** directly from your home screen as a full-screen app!

---

### Step 3: Set up Automatic Apple Watch Syncing (Apple Shortcut)
Open `shortcuts/Apple_Health_Sync_Shortcut.md` for the step-by-step 3-minute visual walkthrough.
- Queries today's Apple Watch samples (**Active Calories**, **Steps**, **Exercise Time**, **Resting HR**, **HRV**, **Sleep**).
- Sends a POST request to `http://<YOUR_PC_IP>:8000/api/sync/health`.
- Set an iOS Automation to run every evening automatically!

---

## 📂 Project Architecture

```
Health app/
├── backend/
│   ├── app.py                 # FastAPI backend, REST endpoints & static PWA server
│   ├── database.py            # SQLite schema (Health metrics, Food logs, Profile, Workouts)
│   ├── ai_coach.py            # Gemini 3.8 Flash & 3.5 Flash-Lite nutrition & exercise engine
│   ├── openfoodfacts.py       # Barcode scanner lookup via Open Food Facts API
│   ├── requirements.txt       # Python dependencies
│   └── health_journey.db      # Local SQLite database
├── frontend/
│   ├── index.html             # iPhone 16 Pro Max optimized mobile PWA
│   ├── manifest.json          # PWA manifest (Standalone iOS display)
│   ├── sw.js                  # Service Worker for offline performance
│   ├── css/
│   │   └── styles.css         # Apple Health dark theme & activity rings
│   ├── js/
│   │   └── app.js             # Core reactive app, barcode scanner, charts, & API client
│   └── icons/                 # High-resolution PWA icons
├── shortcuts/
│   └── Apple_Health_Sync_Shortcut.md  # iOS Shortcut setup guide
├── test_system.py             # Full end-to-end integration test
├── start_server.py            # LAN IP detector & Uvicorn launcher
├── run.bat                    # 1-click Windows startup script
└── README.md
```

---

## 🧪 Verifying the Installation
To test all integrations (Database, Apple Watch sync, Food logging, Barcode lookup, and Gemini AI):
```powershell
python test_system.py
```
