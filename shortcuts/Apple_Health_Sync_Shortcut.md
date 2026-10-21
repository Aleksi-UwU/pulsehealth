# ⌚ Apple Watch Series 10 & iPhone 16 Pro Max Automation Guide

This guide enables **100% automated health syncing** from your Apple Watch Series 10 and iPhone 16 Pro Max directly into your **PulseHealth** journey app without needing a Mac or third-party paid subscriptions.

---

## 🎯 How It Works
Apple Health automatically stores all biometric readings collected by your Apple Watch Series 10 (Active Energy, Steps, Heart Rate, HRV, Sleep, Workouts).
Using the native **Apple Shortcuts** app on your iPhone, we query today's metrics and send a lightweight JSON payload to your PulseHealth webhook.

---

## 🚀 Option 1: 3-Minute Apple Shortcut Setup (Recommended)

1. Open the **Shortcuts** app on your iPhone 16 Pro Max.
2. Tap the **`+`** icon in the top right to create a new shortcut. Name it **"Sync PulseHealth"**.
3. Add the following native actions in order:

### Step 1: Query Apple Health Samples
- Add action: **Find Health Samples**
  - Type: **Active Energy**
  - Date: **is today**
  - Group by: **Day**
  - Calculate: **Sum**
  - Set Variable: `ActiveCalories`

- Add action: **Find Health Samples**
  - Type: **Steps**
  - Date: **is today**
  - Group by: **Day**
  - Calculate: **Sum**
  - Set Variable: `Steps`

- Add action: **Find Health Samples**
  - Type: **Apple Exercise Time**
  - Date: **is today**
  - Group by: **Day**
  - Calculate: **Sum**
  - Set Variable: `ExerciseMins`

- Add action: **Find Health Samples**
  - Type: **Resting Heart Rate**
  - Date: **is today**
  - Sort by: **Latest First**
  - Limit: **1 sample**
  - Set Variable: `RestingHR`

- Add action: **Find Health Samples**
  - Type: **Heart Rate Variability SDNN**
  - Date: **is today**
  - Sort by: **Latest First**
  - Limit: **1 sample**
  - Set Variable: `HRV`

- Add action: **Find Health Samples**
  - Type: **Sleep Analysis**
  - Filter: **State is Asleep**
  - Date: **is in the last 24 hours**
  - Calculate: **Total Time (in hours)**
  - Set Variable: `SleepHours`

---

### Step 2: Build the JSON Dictionary
- Add action: **Dictionary**
  - Add Number: `active_calories` ➔ `ActiveCalories`
  - Add Number: `steps` ➔ `Steps`
  - Add Number: `exercise_minutes` ➔ `ExerciseMins`
  - Add Number: `resting_heart_rate` ➔ `RestingHR`
  - Add Number: `hrv_ms` ➔ `HRV`
  - Add Number: `sleep_hours` ➔ `SleepHours`
  - Add Text: `token` ➔ `health-sync-token-12345`

---

### Step 3: Send POST to Your Webhook
- Add action: **Get Contents of URL**
  - URL: `https://pulsehealth-jade.vercel.app/api/sync/health`
  - Method: **POST**
  - Headers:
    - `Content-Type`: `application/json`
  - Request Body: **JSON**
  - JSON: Choose the **Dictionary** from Step 2

---

## ⚡ Option 2: Automatic Background Trigger
To sync without touching your phone:
1. In the **Shortcuts** app, tap the **Automation** tab at the bottom.
2. Tap **`+` (New Automation)**.
3. Choose either:
   - **Time of Day**: Every day at **8:30 PM** (or your preferred evening time).
   - **Workout Ends**: When any workout finishes on your Apple Watch.
4. Select **Run Immediately** (toggle off "Ask Before Running").
5. Action: Select your **Sync PulseHealth** shortcut.
Now, every day your Apple Watch Series 10 stats update your PulseHealth dashboard automatically in the background!

---

## 📲 Installing PulseHealth as a Full-Screen PWA on iPhone 16 Pro Max
1. Ensure your iPhone is on the same Wi-Fi network as your PC (or connected via Tailscale).
2. Open **Safari** on your iPhone 16 Pro Max.
3. Visit the URL shown on your screen (e.g. `http://192.168.1.XX:8000`).
4. Tap the **Share** button (the box with an upward arrow at the bottom of Safari).
5. Scroll down and tap **"Add to Home Screen"**.
6. Tap **Add**.
Now launch **PulseHealth** from your home screen — it runs in full-screen standalone OLED dark mode, designed with safe-area spacing for the iPhone 16 Pro Max Dynamic Island!
