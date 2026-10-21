// PulseHealth Core Application Engine
let currentTab = "today";
let dashboardData = null;
let chatHistory = [];
let barcodeScannerActive = false;
let videoStream = null;

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  loadDashboard();
  loadProfile();
  setupEventListeners();
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
});

// --- Tab Switching ---
function initTabs() {
  const navBtns = document.querySelectorAll(".nav-item");
  navBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      switchTab(target);
    });
  });
}

function switchTab(tabId) {
  currentTab = tabId;
  document.querySelectorAll(".nav-item").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === tabId);
  });
  document.querySelectorAll(".tab-content").forEach((c) => {
    c.classList.toggle("active", c.id === `tab-${tabId}`);
  });

  if (tabId === "trends") loadTrends();
  if (tabId === "sync") loadSyncInfo();
  if (tabId === "coach" && (!dashboardData || !dashboardData.ai_recommendation)) {
    loadCoachData();
  }
}

// --- API Calls & Data Loaders ---
async function loadDashboard() {
  try {
    const res = await fetch("/api/dashboard");
    const data = await res.json();
    dashboardData = data;
    renderDashboard(data);
    renderFoodTab(data);
    renderCoachTab(data);
  } catch (err) {
    console.error("Failed to load dashboard:", err);
  }
}

async function loadProfile() {
  try {
    const res = await fetch("/api/profile");
    const prof = await res.json();
    populateProfileForm(prof);
  } catch (err) {
    console.error("Failed to load profile:", err);
  }
}

async function loadTrends() {
  try {
    const res = await fetch("/api/history?days=14");
    const json = await res.json();
    renderTrendsCharts(json.history || []);
  } catch (err) {
    console.error("Failed to load trends:", err);
  }
}

async function loadSyncInfo() {
  try {
    const res = await fetch("/api/sync/shortcut-info");
    const info = await res.json();
    document.getElementById("sync-webhook-url").textContent = info.webhook_url;
    document.getElementById("sync-token-display").textContent = info.sync_token;
    document.getElementById("app-lan-url").textContent = info.app_url;
    
    // Generate QR Code using Google Chart API fallback for quick scanning
    const qrImg = document.getElementById("qr-code-img");
    if (qrImg) {
      qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(info.app_url)}`;
    }
  } catch (err) {
    console.error("Failed to load sync info:", err);
  }
}

function copyText(elemId, btnId) {
  const el = document.getElementById(elemId);
  if (!el) return;
  const text = el.textContent.trim();
  navigator.clipboard.writeText(text);
  const btn = document.getElementById(btnId);
  if (btn) {
    const orig = btn.textContent;
    btn.textContent = "✓ Copied!";
    if (navigator.vibrate) navigator.vibrate(20);
    setTimeout(() => { btn.textContent = orig; }, 2000);
  }
}

// --- Render Today Dashboard ---
function renderDashboard(data) {
  const h = data.health || {};
  const f = data.food.totals || {};
  const b = data.energy_balance || {};
  const prof = data.profile || {};

  // Apple Rings
  const moveGoal = 600; // kcal active
  const exerciseGoal = 30; // mins
  const standGoal = 12; // hrs

  const activeKcal = Math.round(h.active_calories || 0);
  const exerciseMins = Math.round(h.exercise_minutes || 0);
  const standHrs = Math.round(h.stand_hours || 0);

  document.getElementById("stat-move-val").textContent = `${activeKcal} / ${moveGoal}`;
  document.getElementById("stat-exercise-val").textContent = `${exerciseMins} / ${exerciseGoal}`;
  document.getElementById("stat-stand-val").textContent = `${standHrs} / ${standGoal}`;

  drawAppleRings(activeKcal / moveGoal, exerciseMins / exerciseGoal, standHrs / standGoal);

  // Calorie Deficit Hero
  const curDeficit = Math.round(b.current_deficit_kcal || 0);
  const targetDeficit = b.target_deficit_kcal || 500;
  const deficitEl = document.getElementById("hero-deficit-num");
  if (deficitEl) {
    deficitEl.textContent = `${curDeficit > 0 ? "-" : "+"}${Math.abs(curDeficit)} kcal`;
    deficitEl.style.color = curDeficit >= targetDeficit ? "var(--accent-cyan)" : (curDeficit > 0 ? "var(--apple-exercise)" : "var(--apple-move)");
  }

  const deficitPct = Math.min(Math.max((curDeficit / targetDeficit) * 100, 0), 100);
  document.getElementById("deficit-bar-fill").style.width = `${deficitPct}%`;
  document.getElementById("deficit-status-label").textContent = 
    curDeficit >= targetDeficit ? `Goal Met (-${targetDeficit} kcal Target)` : `${Math.round(targetDeficit - curDeficit)} kcal remaining to target`;

  // Energy in / out chips
  document.getElementById("hero-energy-in").textContent = `${Math.round(b.calories_in_kcal || 0)} in`;
  document.getElementById("hero-energy-out").textContent = `${Math.round(b.total_energy_out_kcal || 0)} out`;

  // Biometrics
  document.getElementById("bio-steps").textContent = (h.steps || 0).toLocaleString();
  document.getElementById("bio-hrv").textContent = h.hrv_ms ? `${Math.round(h.hrv_ms)} ms` : "--";
  document.getElementById("bio-sleep").textContent = h.sleep_hours ? `${h.sleep_hours.toFixed(1)} h` : "--";
  document.getElementById("bio-rhr").textContent = h.resting_heart_rate ? `${Math.round(h.resting_heart_rate)} bpm` : "--";

  const vo2El = document.getElementById("bio-vo2");
  if (vo2El) vo2El.textContent = h.vo2_max ? `${h.vo2_max.toFixed(1)}` : "--";
  const vo2Sub = document.getElementById("bio-vo2-sub");
  if (vo2Sub && h.vo2_max) {
    vo2Sub.textContent = h.vo2_max >= 45 ? "High (Optimal)" : (h.vo2_max >= 38 ? "Good" : "Fair");
  }

  const zone2El = document.getElementById("bio-zone2");
  if (zone2El) zone2El.textContent = `${h.zone2_minutes || 0} m`;

  const wristTempEl = document.getElementById("bio-wrist-temp");
  if (wristTempEl) {
    const wt = h.wrist_temp_c || 0.0;
    wristTempEl.textContent = `${wt > 0 ? "+" : ""}${wt.toFixed(2)}°`;
    wristTempEl.style.color = Math.abs(wt) >= 0.5 ? "var(--neo-punch)" : "#fff";
  }
  const tempSub = document.getElementById("bio-temp-sub");
  if (tempSub) {
    const wt = h.wrist_temp_c || 0.0;
    tempSub.textContent = wt >= 0.5 ? "⚠️ Strain / Fever" : (wt <= -0.5 ? "Low temp" : "Baseline normal");
  }

  const daylightEl = document.getElementById("bio-daylight");
  if (daylightEl) daylightEl.textContent = `${h.daylight_minutes || 0} m`;

  // Hydration / Water
  const waterData = data.water || { total_ml: 0, target_ml: 3000, percentage: 0 };
  const waterVal = document.getElementById("water-intake-val");
  const waterTarget = document.getElementById("water-target-val");
  const waterBar = document.getElementById("water-bar-fill");
  if (waterVal) waterVal.textContent = waterData.total_ml;
  if (waterTarget) waterTarget.textContent = waterData.target_ml;
  if (waterBar) waterBar.style.width = `${waterData.percentage}%`;

  // Sleep & Recovery Tracker
  const sleepData = data.sleep || {
    hours: h.sleep_hours || 0,
    deep_hours: h.sleep_deep_hours || 0,
    target_hours: 8.0,
    score: h.sleep_hours ? Math.min(100, Math.round((h.sleep_hours / 8.0) * 70 + (Math.min(h.hrv_ms || 50, 80) / 80) * 30)) : null,
    quality: h.sleep_hours >= 7.5 ? "Optimal" : (h.sleep_hours >= 6 ? "Fair" : (h.sleep_hours > 0 ? "Low" : "Unrecorded")),
    percentage: Math.min(Math.round(((h.sleep_hours || 0) / 8.0) * 100), 100)
  };
  const sleepVal = document.getElementById("sleep-duration-val");
  const sleepBar = document.getElementById("sleep-bar-fill");
  const sleepScoreEl = document.getElementById("sleep-score-text");
  const sleepDeepEl = document.getElementById("sleep-deep-text");
  const sleepHoursInput = document.getElementById("sleep-hours-input");
  const sleepDeepInput = document.getElementById("sleep-deep-input");

  if (sleepVal) sleepVal.textContent = sleepData.hours ? sleepData.hours.toFixed(1) : "0.0";
  if (sleepBar) sleepBar.style.width = `${sleepData.percentage}%`;
  if (sleepScoreEl) {
    sleepScoreEl.textContent = sleepData.score ? `Recovery Score: ${sleepData.score}/100 (${sleepData.quality})` : "Recovery Score: Unrecorded";
  }
  if (sleepDeepEl) {
    sleepDeepEl.textContent = `Deep Sleep: ${sleepData.deep_hours > 0 ? sleepData.deep_hours.toFixed(1) + ' hrs' : '--'}`;
  }
  if (sleepHoursInput && !sleepHoursInput.matches(":focus")) {
    sleepHoursInput.value = sleepData.hours || 7.5;
  }
  if (sleepDeepInput && !sleepDeepInput.matches(":focus")) {
    sleepDeepInput.value = sleepData.deep_hours || 1.5;
  }

  // Macros on Today tab
  const pTarget = prof.daily_protein_target || 140;
  const cTarget = prof.daily_carb_target || 180;
  const fTarget = prof.daily_fat_target || 55;

  document.getElementById("today-protein-val").textContent = `${Math.round(f.protein_g || 0)}g`;
  document.getElementById("today-protein-target").textContent = `/ ${pTarget}g`;
  document.getElementById("today-carbs-val").textContent = `${Math.round(f.carbs_g || 0)}g`;
  document.getElementById("today-carbs-target").textContent = `/ ${cTarget}g`;
  document.getElementById("today-fat-val").textContent = `${Math.round(f.fat_g || 0)}g`;
  document.getElementById("today-fat-target").textContent = `/ ${fTarget}g`;
  const fiberVal = document.getElementById("today-fiber-val");
  const fiberTarget = document.getElementById("today-fiber-target");
  if (fiberVal) fiberVal.textContent = `${Math.round(f.fiber_g || 0)}g`;
  if (fiberTarget) fiberTarget.textContent = `/ 35g`;

  // Header date
  const now = new Date();
  document.getElementById("header-date").textContent = now.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric"
  });
}

// --- SVG Apple Rings Renderer ---
function drawAppleRings(movePct, exercisePct, standPct) {
  const container = document.getElementById("rings-svg");
  if (!container) return;

  const clamp = (val) => Math.min(Math.max(val, 0), 1.25);
  const m = clamp(movePct);
  const e = clamp(exercisePct);
  const s = clamp(standPct);

  // Circumferences: 2 * PI * r
  // r1 = 54 -> 339.29
  // r2 = 41 -> 257.61
  // r3 = 28 -> 175.93
  const c1 = 2 * Math.PI * 54;
  const c2 = 2 * Math.PI * 41;
  const c3 = 2 * Math.PI * 28;

  const off1 = c1 * (1 - Math.min(m, 1));
  const off2 = c2 * (1 - Math.min(e, 1));
  const off3 = c3 * (1 - Math.min(s, 1));

  container.innerHTML = `
    <svg viewBox="0 0 130 130" width="130" height="130" style="transform: rotate(-90deg);">
      <!-- Background tracks -->
      <circle cx="65" cy="65" r="54" fill="none" stroke="rgba(255, 36, 86, 0.2)" stroke-width="9" />
      <circle cx="65" cy="65" r="41" fill="none" stroke="rgba(161, 255, 0, 0.2)" stroke-width="9" />
      <circle cx="65" cy="65" r="28" fill="none" stroke="rgba(0, 240, 255, 0.2)" stroke-width="9" />

      <!-- Active Rings -->
      <circle cx="65" cy="65" r="54" fill="none" stroke="var(--apple-move)" stroke-width="9"
        stroke-linecap="round" stroke-dasharray="${c1}" stroke-dashoffset="${off1}"
        style="filter: drop-shadow(0 0 5px var(--apple-move)); transition: stroke-dashoffset 0.8s ease;" />
      
      <circle cx="65" cy="65" r="41" fill="none" stroke="var(--apple-exercise)" stroke-width="9"
        stroke-linecap="round" stroke-dasharray="${c2}" stroke-dashoffset="${off2}"
        style="filter: drop-shadow(0 0 5px var(--apple-exercise)); transition: stroke-dashoffset 0.8s ease;" />

      <circle cx="65" cy="65" r="28" fill="none" stroke="var(--apple-stand)" stroke-width="9"
        stroke-linecap="round" stroke-dasharray="${c3}" stroke-dashoffset="${off3}"
        style="filter: drop-shadow(0 0 5px var(--apple-stand)); transition: stroke-dashoffset 0.8s ease;" />
    </svg>
  `;
}

// --- Render Food Tab ---
function renderFoodTab(data) {
  const items = data.food.items || [];
  const meals = { breakfast: [], lunch: [], dinner: [], snack: [] };
  
  items.forEach((item) => {
    const type = (item.meal_type || "snack").toLowerCase();
    if (meals[type]) meals[type].push(item);
    else meals.snack.push(item);
  });

  const renderMealItems = (list) => {
    if (!list.length) {
      return `<div style="padding: 10px 14px; font-size: 12px; color: var(--text-muted);">No items logged yet</div>`;
    }
    return list.map((item) => `
      <div class="food-item-row">
        <div class="food-details">
          <div class="food-name">${escapeHtml(item.food_name)}</div>
          <div class="food-sub">${escapeHtml(item.serving || "1 serving")} • ${item.source === "barcode" ? "🏷️ Barcode" : (item.source.includes("ai") ? "✨ AI" : "✍️ Manual")}</div>
        </div>
        <div class="food-right">
          <div class="food-macros-chip">
            <span style="font-weight: 700; color: #fff;">${Math.round(item.calories)} kcal</span><br>
            <span style="color: var(--macro-protein);">${Math.round(item.protein_g)}P</span> • 
            <span style="color: var(--macro-carbs);">${Math.round(item.carbs_g)}C</span> • 
            <span style="color: var(--macro-fat);">${Math.round(item.fat_g)}F</span>
          </div>
          <button class="btn-delete" onclick="deleteFoodItem(${item.id})">✕</button>
        </div>
      </div>
    `).join("");
  };

  const getKcalTotal = (list) => Math.round(list.reduce((acc, x) => acc + (x.calories || 0), 0));

  ["breakfast", "lunch", "dinner", "snack"].forEach((m) => {
    const container = document.getElementById(`meal-list-${m}`);
    const kcalEl = document.getElementById(`meal-kcal-${m}`);
    if (container) container.innerHTML = renderMealItems(meals[m]);
    if (kcalEl) kcalEl.textContent = `${getKcalTotal(meals[m])} kcal`;
  });

  // Food totals banner
  const f = data.food.totals || {};
  document.getElementById("food-intake-total").textContent = `${Math.round(f.calories_in || 0)} kcal`;
  document.getElementById("food-remaining-total").textContent = `${Math.round(data.food.remaining_calories || 0)} kcal remaining`;
}

// --- Render Coach Tab ---
function renderCoachTab(data) {
  const rec = data.ai_recommendation;
  const container = document.getElementById("coach-prescription-content");

  if (!rec) {
    container.innerHTML = `
      <div style="text-align: center; padding: 24px 10px;">
        <p style="font-size: 13px; color: var(--text-dim); margin-bottom: 14px;">
          Your coach is ready to analyze today's Apple Watch metrics (HRV, Sleep, Energy Burn) and meal logs to build your personalized workout & deficit plan.
        </p>
        <button class="btn-primary" onclick="generateCoachPlan()">
          ⚡ Generate Today's Workout & Deficit Plan
        </button>
      </div>
    `;
    return;
  }

  const w = rec.recommended_workout || {};
  const exercises = w.exercises || [];

  container.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
      <div>
        <span class="readiness-pill">${escapeHtml(rec.readiness_label || "Optimal")}</span>
        <span style="font-size: 12px; color: var(--text-dim); margin-left: 6px;">Score: ${rec.readiness_score}/100</span>
      </div>
      <button class="btn-secondary" style="width: auto; padding: 6px 12px; margin: 0; font-size: 12px;" onclick="generateCoachPlan()">
        🔄 Refresh
      </button>
    </div>

    <div class="prescription-box">
      <div class="prescription-title">🎯 Recovery & Deficit Analysis</div>
      <div class="prescription-text">${escapeHtml(rec.summary || "")}</div>
      <div style="font-size: 12px; color: var(--accent-cyan); margin-top: 8px; font-weight: 600;">
        ${escapeHtml(rec.calorie_deficit_analysis.guidance || rec.calorie_deficit_analysis || "")}
      </div>
    </div>

    <div class="prescription-box" style="margin-top: 12px; border-left: 4px solid var(--apple-exercise);">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div class="prescription-title" style="color: var(--apple-exercise); margin: 0;">
          🏋️ ${escapeHtml(w.title || "Prescribed Routine")}
        </div>
        <span style="font-size: 12px; color: var(--text-dim);">${w.duration_minutes || 30} mins • ${w.estimated_calories_burn || 250} kcal</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin: 4px 0 10px;">
        Zone: ${escapeHtml(w.target_heart_rate_zone || "Zone 2-3")} | Warmup: ${escapeHtml(w.warmup || "Dynamic mobility")}
      </div>

      <div class="exercise-list">
        ${exercises.map((ex) => `
          <div class="exercise-item">
            <input type="checkbox" style="margin-top: 3px; accent-color: var(--apple-exercise);" />
            <div class="exercise-details">
              <h4>${escapeHtml(ex.name)}</h4>
              <p>${ex.sets} sets × ${ex.reps} • ${ex.rest_seconds || 60}s rest</p>
              ${ex.form_tip ? `<p style="color: var(--accent-cyan); font-style: italic;">Tip: ${escapeHtml(ex.form_tip)}</p>` : ""}
            </div>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

// --- Coach Chat ---
async function sendCoachMessage() {
  const input = document.getElementById("coach-chat-input");
  const msg = input.value.trim();
  if (!msg) return;

  input.value = "";
  appendChatBubble(msg, "user");

  const sendBtn = document.getElementById("coach-send-btn");
  sendBtn.disabled = true;
  sendBtn.innerHTML = `<span class="loading-spinner"></span>`;

  try {
    const res = await fetch("/api/coach/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg, history: chatHistory })
    });
    const data = await res.json();
    appendChatBubble(data.reply, "coach");
    chatHistory.push({ role: "user", content: msg });
    chatHistory.push({ role: "model", content: data.reply });
  } catch (err) {
    appendChatBubble("Sorry, I had trouble reaching your AI coach. Please try again.", "coach");
  } finally {
    sendBtn.disabled = false;
    sendBtn.innerHTML = "➤";
  }
}

function appendChatBubble(text, sender) {
  const chatMessages = document.getElementById("coach-chat-messages");
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${sender}`;
  bubble.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// --- Action Button Handlers ---
async function generateCoachPlan() {
  const btn = event?.target;
  if (btn) btn.innerHTML = `<span class="loading-spinner"></span> Generating...`;
  try {
    const res = await fetch("/api/coach/generate", { method: "POST" });
    const json = await res.json();
    if (dashboardData) {
      dashboardData.ai_recommendation = json.recommendation;
      renderCoachTab(dashboardData);
    }
  } catch (err) {
    alert("Failed to generate plan: " + err.message);
  }
}

async function deleteFoodItem(id) {
  if (!confirm("Remove this food item?")) return;
  try {
    await fetch(`/api/food/log/${id}`, { method: "DELETE" });
    await loadDashboard();
  } catch (err) {
    alert("Error deleting item: " + err.message);
  }
}

// --- Water Intake Handler ---
async function logWater(amountMl) {
  if (navigator.vibrate) navigator.vibrate(20);
  try {
    const res = await fetch("/api/water/log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount_ml: amountMl })
    });
    const json = await res.json();
    if (json.status === "success") {
      await loadDashboard();
    }
  } catch (err) {
    console.error("Failed to log water:", err);
  }
}

// --- Modal Handlers ---
function openModal(id) {
  document.getElementById(id).classList.add("active");
}

function closeModal(id) {
  document.getElementById(id).classList.remove("active");
  if (id === "modal-barcode") {
    stopBarcodeScanner();
  }
}

// --- AI Text Food Parsing ---
async function submitAITextFood() {
  const text = document.getElementById("ai-food-text").value.trim();
  const mealType = document.getElementById("ai-meal-type").value;
  if (!text) return;

  const btn = document.getElementById("btn-ai-text-submit");
  btn.innerHTML = `<span class="loading-spinner"></span> Parsing Meal...`;
  btn.disabled = true;

  try {
    const res = await fetch("/api/food/parse-text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, meal_type: mealType })
    });
    const json = await res.json();
    const items = json.result.items || [];

    // Automatically log all parsed items in parallel
    await Promise.all(items.map((item) => fetch("/api/food/log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        food_name: item.food_name,
        meal_type: mealType,
        calories: item.calories,
        protein_g: item.protein_g,
        carbs_g: item.carbs_g,
        fat_g: item.fat_g,
        fiber_g: item.fiber_g,
        serving: item.serving,
        source: "ai_text"
      })
    })));

    closeModal("modal-ai-text");
    document.getElementById("ai-food-text").value = "";
    await loadDashboard();
  } catch (err) {
    alert("Failed to parse meal: " + err.message);
  } finally {
    btn.innerHTML = `Log with AI`;
    btn.disabled = false;
  }
}

// --- AI Photo Food Logging ---
async function submitAIPhotoFood() {
  const fileInput = document.getElementById("ai-food-file");
  const mealType = document.getElementById("photo-meal-type").value;
  if (!fileInput.files.length) {
    alert("Please snap or select a photo of your food.");
    return;
  }

  const btn = document.getElementById("btn-ai-photo-submit");
  btn.innerHTML = `<span class="loading-spinner"></span> Analyzing Plate...`;
  btn.disabled = true;

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("meal_type", mealType);

  try {
    const res = await fetch("/api/food/scan-photo", {
      method: "POST",
      body: formData
    });
    const json = await res.json();
    const items = json.result.items || [];

    // Log all detected items in parallel
    await Promise.all(items.map((item) => fetch("/api/food/log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        food_name: item.food_name,
        meal_type: mealType,
        calories: item.calories,
        protein_g: item.protein_g,
        carbs_g: item.carbs_g,
        fat_g: item.fat_g,
        fiber_g: item.fiber_g,
        serving: item.serving,
        source: "ai_photo"
      })
    })));

    closeModal("modal-ai-photo");
    fileInput.value = "";
    document.getElementById("photo-preview").style.display = "none";
    await loadDashboard();
  } catch (err) {
    alert("Failed to analyze food photo: " + err.message);
  } finally {
    btn.innerHTML = `Analyze & Log Meal`;
    btn.disabled = false;
  }
}

// --- Barcode Scanner via Camera ---
async function startBarcodeScanner() {
  openModal("modal-barcode");
  const video = document.getElementById("scanner-video");
  const statusEl = document.getElementById("barcode-status");
  statusEl.textContent = "Requesting camera access...";

  try {
    videoStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" }
    });
    video.srcObject = videoStream;
    await video.play();
    barcodeScannerActive = true;
    statusEl.textContent = "Point camera at food package barcode";
    scanBarcodeFrameLoop();
  } catch (err) {
    statusEl.textContent = "Camera access denied or unavailable. Enter barcode manually below.";
    console.error("Camera error:", err);
  }
}

function stopBarcodeScanner() {
  barcodeScannerActive = false;
  if (videoStream) {
    videoStream.getTracks().forEach((track) => track.stop());
    videoStream = null;
  }
}

async function scanBarcodeFrameLoop() {
  if (!barcodeScannerActive) return;
  const video = document.getElementById("scanner-video");

  // Check if native BarcodeDetector API is supported (iOS 17+ Safari)
  if ("BarcodeDetector" in window) {
    try {
      const barcodeDetector = new window.BarcodeDetector({
        formats: ["ean_13", "ean_8", "upc_a", "upc_e", "code_128", "qr_code"]
      });
      const barcodes = await barcodeDetector.detect(video);
      if (barcodes.length > 0) {
        const rawCode = barcodes[0].rawValue;
        handleBarcodeDetected(rawCode);
        return;
      }
    } catch (e) {
      // Fallback frame capture
    }
  }

  requestAnimationFrame(scanBarcodeFrameLoop);
}

async function handleBarcodeDetected(code) {
  stopBarcodeScanner();
  if (navigator.vibrate) navigator.vibrate([40, 30, 40]);
  const statusEl = document.getElementById("barcode-status");
  statusEl.textContent = `Scanned ${code}! Fetching Open Food Facts...`;

  lookupBarcode(code);
}

async function lookupBarcode(barcode) {
  const code = (barcode || document.getElementById("manual-barcode-input").value).trim();
  if (!code) return;

  const resContainer = document.getElementById("barcode-result-container");
  resContainer.innerHTML = `<div style="text-align: center; padding: 20px;"><span class="loading-spinner"></span> Looking up nutrition...</div>`;

  try {
    const res = await fetch(`/api/food/barcode/${encodeURIComponent(code)}`);
    if (!res.ok) throw new Error("Product not found");
    const json = await res.json();
    const prod = json.product;
    window.currentScannedItem = prod;

    resContainer.innerHTML = `
      <div style="background: var(--bg-input); padding: 14px; border-radius: var(--radius-md); border: 1px solid var(--border-glass); margin-top: 10px;">
        <h4 style="font-size: 15px; margin-bottom: 4px;">${escapeHtml(prod.food_name)}</h4>
        <div style="font-size: 12px; color: var(--text-dim); margin-bottom: 8px;">Serving: ${escapeHtml(prod.serving)}</div>
        <div style="display: flex; gap: 8px; font-size: 12px; font-weight: 700;">
          <span style="color: #fff;">${prod.calories} kcal</span> • 
          <span style="color: var(--macro-protein);">${prod.protein_g}g P</span> • 
          <span style="color: var(--macro-carbs);">${prod.carbs_g}g C</span> • 
          <span style="color: var(--macro-fat);">${prod.fat_g}g F</span>
        </div>
        <button class="btn-primary" style="margin-top: 12px; padding: 10px;" onclick="logScannedBarcodeItem()">
          ✓ Add to Food Log
        </button>
      </div>
    `;
  } catch (err) {
    resContainer.innerHTML = `
      <div style="color: var(--apple-move); font-size: 13px; padding: 10px; text-align: center;">
        Barcode not found in database. Try typing what you ate in AI text log instead.
      </div>
    `;
  }
}

async function logScannedBarcodeItem() {
  const prod = window.currentScannedItem;
  if (!prod) return;
  const mealType = document.getElementById("barcode-meal-type").value || "snack";
  try {
    await fetch("/api/food/log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        food_name: prod.food_name,
        meal_type: mealType,
        calories: prod.calories,
        protein_g: prod.protein_g,
        carbs_g: prod.carbs_g,
        fat_g: prod.fat_g,
        fiber_g: prod.fiber_g,
        serving: prod.serving,
        source: "barcode",
        barcode: prod.barcode
      })
    });
    closeModal("modal-barcode");
    window.currentScannedItem = null;
    await loadDashboard();
  } catch (err) {
    alert("Error saving food: " + err.message);
  }
}

// --- Quick Apple Health Manual Sync Modal ---
async function submitManualHealthSync() {
  const steps = parseInt(document.getElementById("manual-steps").value) || 0;
  const activeCal = parseFloat(document.getElementById("manual-active-cal").value) || 0;
  const restingCal = parseFloat(document.getElementById("manual-resting-cal").value) || 0;
  const exerciseMins = parseInt(document.getElementById("manual-exercise-mins").value) || 0;
  const standHrs = parseInt(document.getElementById("manual-stand-hrs").value) || 0;
  const rhr = parseFloat(document.getElementById("manual-rhr").value) || 0;
  const hrv = parseFloat(document.getElementById("manual-hrv").value) || 0;
  const sleep = parseFloat(document.getElementById("manual-sleep").value) || 0;
  const weight = parseFloat(document.getElementById("manual-weight").value) || 0;
  const vo2 = parseFloat(document.getElementById("manual-vo2").value) || 0;
  const zone2 = parseInt(document.getElementById("manual-zone2").value) || 0;
  const wristTemp = parseFloat(document.getElementById("manual-wrist-temp").value) || 0.0;
  const daylight = parseInt(document.getElementById("manual-daylight").value) || 0;

  try {
    await fetch("/api/sync/health", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        steps,
        active_calories: activeCal,
        resting_calories: restingCal,
        exercise_minutes: exerciseMins,
        stand_hours: standHrs,
        resting_heart_rate: rhr,
        hrv_ms: hrv,
        sleep_hours: sleep,
        weight_kg: weight,
        vo2_max: vo2,
        zone2_minutes: zone2,
        wrist_temp_c: wristTemp,
        daylight_minutes: daylight,
        source: "manual_sync"
      })
    });
    closeModal("modal-manual-sync");
    await loadDashboard();
  } catch (err) {
    alert("Sync error: " + err.message);
  }
}

// --- Profile Update ---
function populateProfileForm(prof) {
  if (!prof) return;
  document.getElementById("prof-name").value = prof.name || "Harshil";
  document.getElementById("prof-age").value = prof.age || 28;
  document.getElementById("prof-gender").value = prof.gender || "male";
  document.getElementById("prof-height").value = prof.height_cm || 175;
  document.getElementById("prof-weight").value = prof.current_weight_kg || 80;
  document.getElementById("prof-target-weight").value = prof.target_weight_kg || 72;
  document.getElementById("prof-calorie-target").value = prof.daily_calorie_target || 1850;
  document.getElementById("prof-deficit-target").value = prof.target_deficit_kcal || 500;
  document.getElementById("prof-protein-target").value = prof.daily_protein_target || 140;
}

async function saveProfileSettings() {
  const payload = {
    name: document.getElementById("prof-name").value,
    age: parseInt(document.getElementById("prof-age").value),
    gender: document.getElementById("prof-gender").value,
    height_cm: parseFloat(document.getElementById("prof-height").value),
    current_weight_kg: parseFloat(document.getElementById("prof-weight").value),
    target_weight_kg: parseFloat(document.getElementById("prof-target-weight").value),
    daily_calorie_target: parseInt(document.getElementById("prof-calorie-target").value),
    target_deficit_kcal: parseInt(document.getElementById("prof-deficit-target").value),
    daily_protein_target: parseInt(document.getElementById("prof-protein-target").value)
  };

  try {
    await fetch("/api/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    alert("Settings saved!");
    await loadDashboard();
  } catch (err) {
    alert("Error saving settings: " + err.message);
  }
}

// --- Trends Canvas Charts ---
function renderTrendsCharts(history) {
  const canvas = document.getElementById("trends-canvas");
  if (!canvas || !history.length) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;

  ctx.clearRect(0, 0, w, h);

  // Draw 7-day Deficit Bar Chart
  const last7 = history.slice(-7);
  const barWidth = 32;
  const gap = (w - (barWidth * last7.length)) / (last7.length + 1);

  last7.forEach((item, i) => {
    const x = gap + i * (barWidth + gap);
    const deficit = item.deficit_kcal || 0;
    // Map -800 to +800 onto canvas
    const zeroY = h * 0.6;
    const barHeight = Math.min(Math.abs(deficit) * 0.15, zeroY - 20);

    ctx.fillStyle = deficit >= 450 ? "#00F0FF" : (deficit > 0 ? "#A1FF00" : "#FF2456");
    if (deficit >= 0) {
      ctx.fillRect(x, zeroY - barHeight, barWidth, barHeight);
    } else {
      ctx.fillRect(x, zeroY, barWidth, barHeight);
    }

    // Label
    ctx.fillStyle = "#8E95A5";
    ctx.font = "10px sans-serif";
    ctx.textAlign = "center";
    const dayLabel = item.date.slice(5);
    ctx.fillText(dayLabel, x + barWidth / 2, h - 8);
    ctx.fillText(`${Math.round(deficit)}`, x + barWidth / 2, zeroY - barHeight - 4);
  });

  // Zero line
  ctx.strokeStyle = "rgba(255,255,255,0.15)";
  ctx.beginPath();
  ctx.moveTo(10, h * 0.6);
  ctx.lineTo(w - 10, h * 0.6);
  ctx.stroke();

  // Draw 7-day Sleep Duration Bar Chart
  const sleepCanvas = document.getElementById("sleep-trends-canvas");
  if (sleepCanvas && history.length) {
    const sCtx = sleepCanvas.getContext("2d");
    const sw = sleepCanvas.width;
    const sh = sleepCanvas.height;
    sCtx.clearRect(0, 0, sw, sh);

    const sBarWidth = 32;
    const sGap = (sw - (sBarWidth * last7.length)) / (last7.length + 1);
    const maxSleep = 10.0;
    const targetY = sh - 25 - (8.0 / maxSleep) * (sh - 50);

    // Target benchmark dashed line (8 hrs)
    sCtx.strokeStyle = "rgba(163, 116, 255, 0.4)";
    sCtx.setLineDash([4, 4]);
    sCtx.beginPath();
    sCtx.moveTo(10, targetY);
    sCtx.lineTo(sw - 10, targetY);
    sCtx.stroke();
    sCtx.setLineDash([]);

    sCtx.fillStyle = "#a374ff";
    sCtx.font = "9px sans-serif";
    sCtx.textAlign = "right";
    sCtx.fillText("8h target", sw - 12, targetY - 4);

    last7.forEach((item, i) => {
      const sx = sGap + i * (sBarWidth + sGap);
      const hrs = item.sleep_hours || 0;
      const sBarHeight = Math.min((hrs / maxSleep) * (sh - 50), sh - 50);
      const sy = sh - 25 - sBarHeight;

      sCtx.fillStyle = hrs >= 7.5 ? "#a374ff" : (hrs >= 6.0 ? "#CCFF00" : "#FF2A6D");
      sCtx.fillRect(sx, sy, sBarWidth, sBarHeight);

      // Label
      sCtx.fillStyle = "#8E95A5";
      sCtx.font = "10px sans-serif";
      sCtx.textAlign = "center";
      sCtx.fillText(item.date.slice(5), sx + sBarWidth / 2, sh - 8);
      sCtx.fillStyle = "#FFFFFF";
      sCtx.fillText(hrs > 0 ? `${hrs.toFixed(1)}h` : "--", sx + sBarWidth / 2, sy - 4);
    });
  }
}

// --- Sleep Tracking Operations ---
async function quickLogSleep(hours) {
  if (navigator.vibrate) navigator.vibrate(15);
  try {
    const res = await fetch("/api/sleep/log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sleep_hours: hours,
        sleep_deep_hours: Math.round(hours * 0.2 * 10) / 10
      })
    });
    if (res.ok) {
      await loadDashboard();
    }
  } catch (err) {
    alert("Failed to log sleep: " + err.message);
  }
}

function autoCalcSleepHours() {
  const bed = document.getElementById("sleep-bedtime-input").value;
  const wake = document.getElementById("sleep-waketime-input").value;
  if (!bed || !wake) return;

  const [bH, bM] = bed.split(":").map(Number);
  const [wH, wM] = wake.split(":").map(Number);
  let bMin = bH * 60 + bM;
  let wMin = wH * 60 + wM;
  if (wMin <= bMin) wMin += 1440; // crosses midnight

  const totalHrs = Math.round(((wMin - bMin) / 60) * 10) / 10;
  document.getElementById("sleep-hours-input").value = totalHrs;
  document.getElementById("sleep-deep-input").value = Math.round(totalHrs * 0.2 * 10) / 10;
}

async function submitSleepLog() {
  const hours = parseFloat(document.getElementById("sleep-hours-input").value) || 0;
  const deep = parseFloat(document.getElementById("sleep-deep-input").value) || 0;
  if (hours <= 0) {
    alert("Please enter a valid sleep duration.");
    return;
  }

  try {
    const res = await fetch("/api/sleep/log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sleep_hours: hours,
        sleep_deep_hours: deep
      })
    });
    if (res.ok) {
      closeModal("modal-sleep");
      await loadDashboard();
    } else {
      alert("Error saving sleep log.");
    }
  } catch (err) {
    alert("Failed to save sleep: " + err.message);
  }
}

// --- Instant Apple Watch Trigger ---
function triggerInstantWatchSync() {
  if (navigator.vibrate) navigator.vibrate(25);
  const isIOS = /iPhone|iPad|iPod/.test(navigator.userAgent);
  if (isIOS) {
    // Invoke native iOS Shortcuts URL scheme to pull Watch S10 data immediately
    window.location.href = "shortcuts://run-shortcut?name=Sync%20PulseHealth";
  } else {
    // On non-iOS, prompt quick manual sync modal
    openModal("modal-manual-sync");
  }
  // Fast double-poll to render metrics as soon as Shortcut completes
  setTimeout(loadDashboard, 1500);
  setTimeout(loadDashboard, 4000);
}

// --- Photo Preview & Interaction Feedback ---
function setupEventListeners() {
  const photoInput = document.getElementById("ai-food-file");
  if (photoInput) {
    photoInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file) {
        const preview = document.getElementById("photo-preview");
        preview.src = URL.createObjectURL(file);
        preview.style.display = "block";
      }
    });
  }

  const equipInput = document.getElementById("equipment-photo-file");
  if (equipInput) {
    equipInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file) {
        const preview = document.getElementById("equipment-photo-preview");
        if (preview) {
          preview.src = URL.createObjectURL(file);
          preview.style.display = "block";
        }
      }
    });
  }

  // Autonomous live sync when user returns to app/focus
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      loadDashboard();
    }
  });
  window.addEventListener("focus", () => {
    loadDashboard();
  });

  // Tactile haptic feedback for buttons & controls
  document.addEventListener("click", (e) => {
    if (e.target.closest("button, .nav-item, .btn-action, .btn-water, .section-badge")) {
      if (navigator.vibrate) {
        try {
          navigator.vibrate(15);
        } catch (_) {}
      }
    }
  });
}

// --- Gym Equipment Scanner & Form GIF Guide ---
let currentScannedGuide = null;

async function submitGymEquipmentScan() {
  const fileInput = document.getElementById("equipment-photo-file");
  if (!fileInput || !fileInput.files.length) {
    alert("Please snap or select a photo of the gym equipment.");
    return;
  }

  const btn = document.getElementById("btn-equipment-submit");
  const container = document.getElementById("equipment-results-container");
  btn.innerHTML = `<span class="loading-spinner"></span> Identifying Machine & Form GIF...`;
  btn.disabled = true;
  container.innerHTML = `<div style="text-align: center; padding: 24px 0; color: var(--accent-cyan); font-weight: 700; font-size: 13px;">
    🔍 Analyzing biomechanics, identifying machine, and querying exercise GIF library...
  </div>`;

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const res = await fetch("/api/coach/scan-equipment", {
      method: "POST",
      body: formData
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || "Server error while scanning equipment");
    }
    const data = await res.json();
    currentScannedGuide = data.guide;
    renderEquipmentGuide(data.guide);
  } catch (err) {
    container.innerHTML = `<div style="padding: 12px; background: rgba(255, 75, 75, 0.15); border: 2px solid var(--accent-red); border-radius: var(--radius-sm); color: var(--accent-red); font-size: 13px; font-weight: 600;">
      ❌ Failed to analyze gym equipment: ${escapeHtml(err.message)}
    </div>`;
  } finally {
    btn.innerHTML = `Scan Machine & Show GIF Guide`;
    btn.disabled = false;
  }
}

function renderEquipmentGuide(guide) {
  const container = document.getElementById("equipment-results-container");
  if (!container || !guide) return;

  const primaryMuscle = guide.primary_muscle || "Full Body";
  const secondaries = (guide.secondary_muscles || []).map(m => `<span class="equipment-tag">${escapeHtml(m)}</span>`).join(" ");
  const setupList = (guide.setup_steps || []).map(s => `<li>${escapeHtml(s)}</li>`).join("");
  const executionList = (guide.execution_steps || []).map(s => `<li>${escapeHtml(s)}</li>`).join("");
  const mistakesList = (guide.common_mistakes || []).map(m => `<li>${escapeHtml(m)}</li>`).join("");
  const prescription = guide.recommended_prescription || "3-4 sets × 10-12 reps";

  const gifHtml = guide.gif_url ? `
    <div class="equipment-gif-container">
      <img src="${escapeHtml(guide.gif_url)}" alt="${escapeHtml(guide.equipment_name || 'Gym Machine')} Form GIF" class="equipment-gif" loading="lazy" onerror="this.onerror=null; this.parentElement.innerHTML='<div style=\\'padding: 20px; text-align: center; color: var(--text-dim); font-size: 12px;\\'>🎬 Demonstration GIF preview unavailable.</div>';" />
    </div>
  ` : '';

  container.innerHTML = `
    <div class="equipment-card">
      <div style="font-size: 18px; font-weight: 900; color: #fff; margin-bottom: 8px; letter-spacing: -0.3px;">
        ${escapeHtml(guide.equipment_name || "Identified Gym Machine")}
      </div>
      
      <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px;">
        <span class="equipment-tag primary">🎯 ${escapeHtml(primaryMuscle)}</span>
        ${secondaries}
      </div>

      ${gifHtml}

      <div style="background: rgba(0, 229, 255, 0.1); border: 1.5px solid var(--accent-cyan); border-radius: var(--radius-sm); padding: 8px 12px; margin-bottom: 14px; font-size: 12px; font-weight: 700; color: var(--accent-cyan); display: flex; align-items: center; justify-content: space-between;">
        <span>📋 Recommended:</span>
        <span style="color: #fff;">${escapeHtml(prescription)}</span>
      </div>

      <div class="equipment-guide-section">
        <div class="equipment-guide-title">⚙️ Machine Setup & Adjustments</div>
        <ol class="equipment-guide-list">
          ${setupList || '<li>Adjust seat and thigh pad height for secure anchoring.</li>'}
        </ol>
      </div>

      <div class="equipment-guide-section">
        <div class="equipment-guide-title">💪 Execution & Form Cues</div>
        <ol class="equipment-guide-list">
          ${executionList || '<li>Maintain stable core, control movement through full range of motion.</li>'}
        </ol>
      </div>

      ${mistakesList ? `
      <div class="equipment-guide-section" style="border-left: 3px solid var(--accent-red); padding-left: 8px;">
        <div class="equipment-guide-title" style="color: var(--accent-red);">⚠️ Avoid These Common Mistakes</div>
        <ul class="equipment-guide-list" style="list-style-type: disc;">
          ${mistakesList}
        </ul>
      </div>
      ` : ''}

      <button class="btn-primary" style="margin-top: 14px; background: var(--accent-cyan); color: #000;" onclick="addScannedExerciseToWorkout()">
        ➕ Add to Today's Workout
      </button>
    </div>
  `;
}

async function addScannedExerciseToWorkout() {
  if (!currentScannedGuide) return;
  const g = currentScannedGuide;

  try {
    const res = await fetch("/api/workouts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: g.equipment_name || "Gym Machine Exercise",
        workout_type: "strength",
        duration_minutes: 15,
        calories_burned: 90,
        exercises_json: [
          {
            name: g.equipment_name || "Exercise",
            sets: 3,
            reps: "10-12",
            rest_seconds: 60,
            form_tip: g.execution_steps ? g.execution_steps[0] : (g.recommended_prescription || "")
          }
        ],
        notes: `Target: ${g.primary_muscle || 'Full Body'}. GIF Guide: ${g.gif_url || 'N/A'}`
      })
    });
    if (res.ok) {
      alert(`✅ "${g.equipment_name}" added to today's workout plan!`);
      closeModal("modal-equipment");
      await loadDashboard();
    } else {
      alert("Failed to add exercise to workout.");
    }
  } catch (err) {
    alert("Error logging workout: " + err.message);
  }
}

// Utility
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
