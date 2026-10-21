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

    return {
        "date": d,
        "profile": profile,
        "health": health,
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

@app.post("/api/sync/health")
def sync_apple_health_metrics(payload: HealthSyncPayload):
    """
    Webhook endpoint to ingest Apple Watch Series 10 / Apple Health data.
    Works with Apple Shortcuts or Health Auto Export app.
    """
    profile = db.get_profile()
    if payload.token and profile.get("sync_token") and payload.token != profile.get("sync_token"):
        raise HTTPException(status_code=401, detail="Invalid sync token")

    data = payload.dict(exclude_unset=True)
    if "token" in data:
        del data["token"]

    saved = db.upsert_health_metrics(data)
    return {
        "status": "success",
        "message": "Apple Health data synced successfully",
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
