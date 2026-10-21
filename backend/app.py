import os
import socket
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

import database as db
import openfoodfacts as off
import ai_coach

# Initialize database schema on startup
db.init_db()

app = FastAPI(title="PulseHealth - Health Journey & AI Coach", version="1.0.0")

# Enable CORS for local network / iPhone access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper to find local LAN IP for iPhone pairing
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# Pydantic models for request bodies
class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    current_weight_kg: Optional[float] = None
    target_weight_kg: Optional[float] = None
    activity_level: Optional[str] = None
    daily_calorie_target: Optional[int] = None
    daily_protein_target: Optional[int] = None
    daily_carb_target: Optional[int] = None
    daily_fat_target: Optional[int] = None
    target_deficit_kcal: Optional[int] = None
    sync_token: Optional[str] = None

class HealthSyncPayload(BaseModel):
    date: Optional[str] = None
    token: Optional[str] = None
    steps: Optional[int] = 0
    active_calories: Optional[float] = 0.0
    resting_calories: Optional[float] = 0.0
    total_calories: Optional[float] = 0.0
    exercise_minutes: Optional[int] = 0
    stand_hours: Optional[int] = 0
    resting_heart_rate: Optional[float] = 0.0
    hrv_ms: Optional[float] = 0.0
    sleep_hours: Optional[float] = 0.0
    sleep_deep_hours: Optional[float] = 0.0
    weight_kg: Optional[float] = 0.0
    source: Optional[str] = "apple_health"

class FoodLogItem(BaseModel):
    date: Optional[str] = None
    meal_type: str = "snack"
    food_name: str
    calories: float
    protein_g: Optional[float] = 0.0
    carbs_g: Optional[float] = 0.0
    fat_g: Optional[float] = 0.0
    fiber_g: Optional[float] = 0.0
    serving: Optional[str] = "1 serving"
    source: Optional[str] = "manual"
    barcode: Optional[str] = None

class TextParseRequest(BaseModel):
    text: str
    meal_type: Optional[str] = "lunch"

class CoachChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

class WaterLogRequest(BaseModel):
    amount_ml: int
    date: Optional[str] = None

class SleepLogRequest(BaseModel):
    sleep_hours: float
    sleep_deep_hours: Optional[float] = 0.0
    date: Optional[str] = None

# --- API Endpoints ---

@app.get("/api/profile")
def get_user_profile():
    return db.get_profile()

@app.post("/api/profile")
def update_user_profile(req: ProfileUpdateRequest):
    data = req.dict(exclude_unset=True)
    return db.update_profile(data)

@app.get("/api/dashboard")
def get_dashboard_summary(target_date: Optional[str] = None):
    d = target_date or date.today().isoformat()
    profile = db.get_profile()
    health = db.get_health_metrics(d) or {
        "date": d,
        "steps": 0,
        "active_calories": 0.0,
        "resting_calories": 0.0,
        "total_calories": 0.0,
        "exercise_minutes": 0,
        "stand_hours": 0,
        "resting_heart_rate": 0.0,
        "hrv_ms": 0.0,
        "sleep_hours": 0.0,
        "weight_kg": profile.get("current_weight_kg", 80.0)
    }

    food_items = db.get_food_logs(d)
    workouts = db.get_workouts(d)
    ai_rec = db.get_ai_recommendation(d)

    # Calculate nutritional totals
    calories_in = sum(f["calories"] for f in food_items)
    protein_in = sum(f["protein_g"] for f in food_items)
    carbs_in = sum(f["carbs_g"] for f in food_items)
    fat_in = sum(f["fat_g"] for f in food_items)
    fiber_in = sum(f["fiber_g"] for f in food_items)

    # Calculate Basal Metabolic Rate (BMR) using Mifflin-St Jeor equation as baseline
    # Men: 10 * weight (kg) + 6.25 * height (cm) - 5 * age + 5
    # Women: 10 * weight (kg) + 6.25 * height (cm) - 5 * age - 161
    w = health.get("weight_kg") or profile.get("current_weight_kg", 80.0)
    h = profile.get("height_cm", 175.0)
    a = profile.get("age", 28)
    is_male = profile.get("gender", "male").lower() == "male"
    calc_bmr = (10 * w) + (6.25 * h) - (5 * a) + (5 if is_male else -161)

    resting_burn = health.get("resting_calories") or calc_bmr
    active_burn = health.get("active_calories") or 0.0
    total_energy_out = health.get("total_calories") or (resting_burn + active_burn)

    # Net Deficit calculation
    current_deficit = total_energy_out - calories_in
    target_deficit = profile.get("target_deficit_kcal", 500)
    
    # Calorie budget remaining
    daily_budget = profile.get("daily_calorie_target", 1850)
    calories_remaining = daily_budget - calories_in
    water_ml = db.get_water_intake(d)

    sleep_hrs = round(health.get("sleep_hours") or 0.0, 1)
    sleep_deep = round(health.get("sleep_deep_hours") or 0.0, 1)
    hrv = health.get("hrv_ms") or 0.0
    sleep_score = min(100, max(0, round((sleep_hrs / 8.0) * 70 + (min(hrv, 80.0) / 80.0) * 30))) if sleep_hrs > 0 else 0
    sleep_quality = "Optimal" if sleep_hrs >= 7.5 else ("Fair" if sleep_hrs >= 6.0 else ("Low" if sleep_hrs > 0 else "Unrecorded"))

    return {
        "date": d,
        "profile": profile,
        "health": health,
        "sleep": {
            "hours": sleep_hrs,
            "deep_hours": sleep_deep,
            "target_hours": 8.0,
            "score": sleep_score,
            "quality": sleep_quality,
            "percentage": min(round((sleep_hrs / 8.0) * 100), 100)
        },
        "water": {
            "total_ml": water_ml,
            "target_ml": 3000,
            "percentage": min(round((water_ml / 3000) * 100), 100)
        },
        "food": {
            "items": food_items,
            "totals": {
                "calories_in": round(calories_in, 1),
                "protein_g": round(protein_in, 1),
                "carbs_g": round(carbs_in, 1),
                "fat_g": round(fat_in, 1),
                "fiber_g": round(fiber_in, 1),
            },
            "remaining_calories": round(calories_remaining, 1),
        },
        "energy_balance": {
            "bmr_kcal": round(resting_burn, 1),
            "active_burn_kcal": round(active_burn, 1),
            "total_energy_out_kcal": round(total_energy_out, 1),
            "calories_in_kcal": round(calories_in, 1),
            "current_deficit_kcal": round(current_deficit, 1),
            "target_deficit_kcal": target_deficit,
            "deficit_status": "Ahead" if current_deficit >= target_deficit else "Building"
        },
        "workouts": workouts,
        "ai_recommendation": ai_rec
    }

@app.api_route("/api/sync/health", methods=["GET", "POST"])
async def sync_apple_health_metrics(request: Request):
    """
    Universal Autonomous Webhook for Apple Watch Series 10 / Apple Health.
    Supports:
    1. Native Apple Shortcuts (JSON body or query params)
    2. Health Auto Export app (nested data.metrics array)
    3. Direct URL Webhook triggers
    """
    # 1. Extract token from header, query param, or body
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "").strip()
    elif auth_header:
        token = auth_header.strip()
    
    if not token:
        token = request.query_params.get("token")

    raw_payload = {}
    if request.method == "POST":
        try:
            raw_payload = await request.json()
        except Exception:
            raw_payload = {}
        if not token:
            token = raw_payload.get("token")
    else:
        raw_payload = dict(request.query_params)

    # 2. Verify token
    profile = db.get_profile()
    expected_token = profile.get("sync_token")
    if expected_token and token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid sync token")

    parsed_data: Dict[str, Any] = {
        "date": raw_payload.get("date") or date.today().isoformat(),
        "source": "apple_health"
    }

    # 3. Check for Health Auto Export format (data.metrics)
    if "data" in raw_payload and isinstance(raw_payload["data"], dict) and "metrics" in raw_payload["data"]:
        metrics_list = raw_payload["data"].get("metrics", [])
        for m in metrics_list:
            m_name = m.get("name", "").lower()
            samples = m.get("data", [])
            if not samples:
                continue
            if m_name in ["active_energy", "active_calories"]:
                parsed_data["active_calories"] = round(sum(float(s.get("qty", 0.0)) for s in samples), 1)
            elif m_name in ["step_count", "steps"]:
                parsed_data["steps"] = int(sum(float(s.get("qty", 0)) for s in samples))
            elif m_name in ["apple_exercise_time", "exercise_minutes"]:
                parsed_data["exercise_minutes"] = int(sum(float(s.get("qty", 0)) for s in samples))
            elif m_name in ["apple_stand_time", "stand_hours"]:
                parsed_data["stand_hours"] = int(sum(float(s.get("qty", 0)) for s in samples))
            elif m_name in ["resting_heart_rate"]:
                parsed_data["resting_heart_rate"] = round(float(samples[-1].get("qty", 0.0)), 1)
            elif m_name in ["heart_rate_variability_sdnn", "hrv", "hrv_ms"]:
                parsed_data["hrv_ms"] = round(float(samples[-1].get("qty", 0.0)), 1)
            elif m_name in ["sleep_analysis", "sleep_hours"]:
                parsed_data["sleep_hours"] = round(sum(float(s.get("qty", 0.0)) for s in samples), 1)
            elif m_name in ["basal_energy_burned", "resting_calories"]:
                parsed_data["resting_calories"] = round(sum(float(s.get("qty", 0.0)) for s in samples), 1)
            elif m_name in ["body_mass", "weight", "weight_kg"]:
                parsed_data["weight_kg"] = round(float(samples[-1].get("qty", 0.0)), 1)
    else:
        # Standard flat format (Apple Shortcuts or direct payload)
        field_mapping = {
            "steps": ["steps", "step_count"],
            "active_calories": ["active_calories", "active_energy", "activeCalories"],
            "resting_calories": ["resting_calories", "basal_energy_burned", "restingCalories"],
            "total_calories": ["total_calories", "totalCalories"],
            "exercise_minutes": ["exercise_minutes", "apple_exercise_time", "exerciseMinutes"],
            "stand_hours": ["stand_hours", "apple_stand_time", "standHours"],
            "resting_heart_rate": ["resting_heart_rate", "restingHeartRate", "rhr"],
            "hrv_ms": ["hrv_ms", "hrv", "heart_rate_variability_sdnn", "hrvMs"],
            "sleep_hours": ["sleep_hours", "sleep_analysis", "sleepHours"],
            "sleep_deep_hours": ["sleep_deep_hours", "sleepDeepHours"],
            "weight_kg": ["weight_kg", "weight", "body_mass", "weightKg"]
        }
        for target_field, candidates in field_mapping.items():
            for c in candidates:
                if c in raw_payload and raw_payload[c] is not None:
                    try:
                        if target_field in ["steps", "exercise_minutes", "stand_hours"]:
                            parsed_data[target_field] = int(float(raw_payload[c]))
                        else:
                            parsed_data[target_field] = round(float(raw_payload[c]), 1)
                    except (ValueError, TypeError):
                        pass
                    break

    saved = db.upsert_health_metrics(parsed_data)
    return {
        "status": "success",
        "message": "Health telemetry synced instantaneously",
        "data": saved
    }

@app.post("/api/food/log")
def log_food_item(item: FoodLogItem):
    data = item.dict(exclude_unset=True)
    res = db.add_food_log(data)
    return {"status": "success", "item": res}

@app.delete("/api/food/log/{log_id}")
def remove_food_item(log_id: int):
    success = db.delete_food_log(log_id)
    if not success:
        raise HTTPException(status_code=404, detail="Food log not found")
    return {"status": "success", "deleted_id": log_id}

@app.post("/api/water/log")
def log_water_intake(req: WaterLogRequest):
    d = req.date or date.today().isoformat()
    total = db.add_water_intake(d, req.amount_ml)
    return {"status": "success", "total_ml": total, "target_ml": 3000}

@app.post("/api/sleep/log")
def log_sleep_record(req: SleepLogRequest):
    d = req.date or date.today().isoformat()
    saved = db.upsert_health_metrics({
        "date": d,
        "sleep_hours": round(req.sleep_hours, 1),
        "sleep_deep_hours": round(req.sleep_deep_hours or 0.0, 1),
        "source": "sleep_tracker"
    })
    return {"status": "success", "metrics": saved}

@app.post("/api/food/parse-text")
def parse_food_from_text(req: TextParseRequest):
    """
    AI Natural language food logger.
    """
    try:
        parsed = ai_coach.parse_food_text(req.text)
        # Attach default meal type if needed
        for item in parsed.get("items", []):
            if "meal_type" not in item:
                item["meal_type"] = req.meal_type or item.get("meal_type_hint", "lunch")
        return {"status": "success", "result": parsed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/food/scan-photo")
async def scan_food_photo(
    file: UploadFile = File(...),
    meal_type: str = Form("lunch")
):
    """
    AI Multimodal camera / photo food analyzer.
    """
    try:
        contents = await file.read()
        mime = file.content_type or "image/jpeg"
        parsed = ai_coach.analyze_food_photo(contents, mime_type=mime)
        for item in parsed.get("items", []):
            item["meal_type"] = meal_type
        return {"status": "success", "result": parsed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/food/barcode/{code}")
def scan_barcode(code: str):
    """
    Lookup nutritional information by UPC / EAN barcode from Open Food Facts.
    """
    result = off.fetch_barcode_nutrition(code)
    if not result:
        raise HTTPException(status_code=404, detail=f"Barcode {code} not found in food database")
    return {"status": "success", "product": result}

@app.post("/api/coach/scan-equipment")
async def scan_gym_equipment(file: UploadFile = File(...)):
    """
    AI Multimodal camera / photo gym equipment identifier and exercise guide with demonstration GIF.
    """
    try:
        contents = await file.read()
        mime = file.content_type or "image/jpeg"
        guide = ai_coach.identify_gym_equipment(contents, mime_type=mime)
        return {"status": "success", "guide": guide}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/coach/generate")
def generate_coach_recommendation(target_date: Optional[str] = None):
    """
    Generates a personalized daily workout prescription and caloric deficit coaching plan.
    """
    d = target_date or date.today().isoformat()
    profile = db.get_profile()
    health = db.get_health_metrics(d) or {
        "date": d,
        "steps": 0,
        "active_calories": 0.0,
        "resting_calories": 0.0,
        "total_calories": 0.0,
        "resting_heart_rate": 0.0,
        "hrv_ms": 0.0,
        "sleep_hours": 0.0
    }
    today_foods = db.get_food_logs(d)
    recent = db.get_recent_history(days=7)

    try:
        rec = ai_coach.recommend_daily_workout_and_deficit(
            user_profile=profile,
            health_metrics=health,
            today_food_logs=today_foods,
            recent_history=recent
        )
        rec["date"] = d
        saved = db.save_ai_recommendation(rec)

        # Automatically create or update today's prescribed workout in workouts table
        w = rec.get("recommended_workout", {})
        if w and w.get("title"):
            db.add_workout({
                "date": d,
                "title": w.get("title", "AI Prescribed Workout"),
                "workout_type": w.get("workout_type", "strength"),
                "duration_minutes": w.get("duration_minutes", 30),
                "calories_burned": w.get("estimated_calories_burn", 250),
                "exercises_json": w.get("exercises", []),
                "notes": f"HR Zone: {w.get('target_heart_rate_zone', '')} | Warmup: {w.get('warmup', '')}"
            })

        return {"status": "success", "recommendation": saved}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/coach/chat")
def chat_with_ai_coach(req: CoachChatRequest):
    """
    Conversational AI coach grounded in user's live Apple Watch and food data.
    """
    d = date.today().isoformat()
    profile = db.get_profile()
    health = db.get_health_metrics(d) or {}
    foods = db.get_food_logs(d)
    
    summary = {
        "current_weight": f"{profile.get('current_weight_kg', 80)}kg",
        "target_weight": f"{profile.get('target_weight_kg', 72)}kg",
        "calories_in": sum(f["calories"] for f in foods),
        "protein_in": sum(f["protein_g"] for f in foods),
        "active_burn": health.get("active_calories", 0),
        "steps": health.get("steps", 0),
        "sleep_hours": health.get("sleep_hours", "N/A"),
        "hrv": health.get("hrv_ms", "N/A"),
        "target_deficit": profile.get("target_deficit_kcal", 500)
    }

    try:
        reply = ai_coach.chat_with_coach(req.message, req.history, summary)
        return {"status": "success", "reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workouts")
def create_workout(workout_data: Dict[str, Any]):
    """
    Log or add a workout directly to the database.
    """
    if "date" not in workout_data:
        workout_data["date"] = date.today().isoformat()
    res = db.add_workout(workout_data)
    return {"status": "success", "workout": res}

@app.post("/api/workouts/toggle/{workout_id}")
def toggle_workout(workout_id: int):
    updated = db.toggle_workout_completed(workout_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Workout not found")
    return {"status": "success", "workout": updated}

@app.get("/api/history")
def get_history(days: int = 14):
    history = db.get_recent_history(days)
    return {"status": "success", "history": history}

@app.get("/api/sync/shortcut-info")
def get_shortcut_info():
    lan_ip = get_local_ip()
    profile = db.get_profile()
    token = profile.get("sync_token", "health-sync-token-12345")
    webhook_url = f"http://{lan_ip}:8000/api/sync/health"
    app_url = f"http://{lan_ip}:8000"

    return {
        "lan_ip": lan_ip,
        "app_url": app_url,
        "webhook_url": webhook_url,
        "sync_token": token,
        "instructions": (
            "On your iPhone 16 Pro Max, open the Shortcuts app and create a new Shortcut. "
            "Use 'Find Health Samples' to get Active Energy, Resting Energy, Steps, Sleep, HRV, and Resting Heart Rate, "
            f"then use 'Get Contents of URL' to POST JSON to: {webhook_url}"
        )
    }

# Serve frontend PWA static files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "PulseHealth API is running. Frontend not found."}

@app.get("/manifest.json")
def serve_manifest():
    return FileResponse(os.path.join(FRONTEND_DIR, "manifest.json"))

@app.get("/sw.js")
def serve_service_worker():
    return FileResponse(os.path.join(FRONTEND_DIR, "sw.js"), media_type="application/javascript")
