import os
import json
import base64
import re
import requests
from datetime import datetime, date
from typing import Optional, Dict, Any, List

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODELS_TO_TRY = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-flash-latest"]

def _call_gemini(contents: list, system_instruction: str = "", response_mime_type: str = "application/json") -> str:
    """
    Direct REST call to Gemini with automatic model fallback for resilience.
    """
    key = os.environ.get("GEMINI_API_KEY", GEMINI_API_KEY)
    if not key:
        raise ValueError("GEMINI_API_KEY is not set.")

    last_error = None
    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048,
            }
        }
        
        if response_mime_type == "application/json":
            payload["generationConfig"]["responseMimeType"] = "application/json"
            
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        try:
            resp = requests.post(url, json=payload, timeout=18)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
            elif resp.status_code in [404, 503, 429]:
                # Try next model
                last_error = f"Model {model_name} returned status {resp.status_code}: {resp.text}"
                continue
            else:
                last_error = f"HTTP {resp.status_code}: {resp.text}"
        except Exception as e:
            last_error = str(e)
            continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")

def _extract_json(text: str) -> Dict[str, Any]:
    """Helper to cleanly extract JSON even if enclosed in markdown backticks."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)

def parse_food_text(text: str) -> Dict[str, Any]:
    """
    Parse natural language description of meals into structured food items and macronutrients.
    """
    system_prompt = """
    You are an expert sports nutritionist and dietitian specializing in accurate calorie and macronutrient breakdown for fat loss and muscle retention.
    Given a user's natural language meal description, extract each item, estimate realistic portion sizes, calories (kcal), protein (g), carbohydrates (g), fat (g), and dietary fiber (g).
    Always return valid JSON adhering strictly to this schema:
    {
        "items": [
            {
                "food_name": "Scrambled Eggs",
                "calories": 180,
                "protein_g": 12.0,
                "carbs_g": 2.0,
                "fat_g": 14.0,
                "fiber_g": 0.0,
                "serving": "2 large eggs with 1 tsp butter",
                "meal_type_hint": "breakfast"
            }
        ],
        "totals": {
            "calories": 180,
            "protein_g": 12.0,
            "carbs_g": 2.0,
            "fat_g": 14.0,
            "fiber_g": 0.0
        },
        "dietitian_tip": "High protein, great for satiety."
    }
    """
    
    contents = [
        {"parts": [{"text": f"Analyze this meal and provide calories and macronutrients: {text}"}]}
    ]

    raw_output = _call_gemini(contents, system_instruction=system_prompt, response_mime_type="application/json")
    return _extract_json(raw_output)

def analyze_food_photo(image_bytes: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
    """
    Multimodal vision: Analyze a food photo to detect items, portions, calories, and macros.
    """
    system_prompt = """
    You are an elite AI nutritionist with computer vision expertise.
    Examine the provided food image carefully:
    1. Identify all recognizable food items, ingredients, sauces, and beverages.
    2. Estimate realistic portion sizes (in grams or standard servings).
    3. Calculate total estimated calories, protein, carbohydrates, fats, and fiber.
    4. Provide actionable fat-loss advice on this meal (e.g. protein density, fiber, hidden dressings).
    
    Output strictly in this JSON format:
    {
        "items": [
            {
                "food_name": "Grilled Chicken Breast",
                "calories": 240,
                "protein_g": 45.0,
                "carbs_g": 0.0,
                "fat_g": 5.0,
                "fiber_g": 0.0,
                "serving": "180g (palm-sized portion)"
            }
        ],
        "totals": {
            "calories": 240,
            "protein_g": 45.0,
            "carbs_g": 0.0,
            "fat_g": 5.0,
            "fiber_g": 0.0
        },
        "visual_confidence": "high",
        "dietitian_tip": "Excellent lean protein source to preserve muscle in a caloric deficit."
    }
    """

    b64_data = base64.b64encode(image_bytes).decode("utf-8")
    contents = [
        {
            "parts": [
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": b64_data
                    }
                },
                {"text": "Analyze the calories and macronutrients of this meal from the photo."}
            ]
        }
    ]

    raw_output = _call_gemini(contents, system_instruction=system_prompt, response_mime_type="application/json")
    return _extract_json(raw_output)

def recommend_daily_workout_and_deficit(
    user_profile: Dict[str, Any],
    health_metrics: Dict[str, Any],
    today_food_logs: List[Dict[str, Any]],
    recent_history: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Core AI Exercise & Weight Loss Coach:
    Synthesizes Apple Watch Series 10 biometric data (HRV, Sleep, Active Calories, RHR, Steps)
    with today's food intake to prescribe the optimal workout and caloric deficit strategy.
    """
    system_prompt = """
    You are an elite, evidence-based exercise physiologist and fat loss coach.
    Your mission: Prescribe the optimal daily exercise routine and caloric deficit strategy to help the user lose fat while retaining maximum lean muscle mass.
    
    Key Physiological Principles:
    1. Recovery-Readiness:
       - Apple Watch HRV (Heart Rate Variability in ms) and Sleep hours determine central nervous system readiness.
       - High HRV (>50ms or above baseline) + 7+ hours sleep = High readiness. Prescribe progressive resistance training (hypertrophy / compound strength) or higher intensity training.
       - Low HRV (<35ms) or <6 hours sleep = Fatigued / Strained. Prescribe low-impact Zone 2 fat oxidation (incline walking, easy cycling) and mobility. NEVER overtrain a sleep-deprived user (it spikes cortisol, breaks down muscle, and causes hunger binges).
    2. Calorie Deficit & Energy Balance:
       - Basal Metabolic Rate (BMR) + Apple Watch Active Energy = Total Daily Energy Expenditure (TDEE).
       - Sustainable fat loss deficit is 400 - 600 kcal.
       - Verify today's calorie intake against the deficit goal.
    3. Muscle Preservation:
       - Resistance training with adequate protein (1.6g-2.2g per kg) signals the body to burn adipose tissue rather than muscle tissue during a deficit.
    
    Output strictly in this JSON format:
    {
        "readiness_score": 85,
        "readiness_label": "High Readiness (Optimal)",
        "recovery_status": "Your HRV (58ms) and 7.4 hrs of sleep indicate solid parasympathetic recovery. Your nervous system is primed for resistance training.",
        "calorie_deficit_analysis": {
            "tdee_projected_kcal": 2400,
            "calories_consumed_so_far": 1450,
            "active_calories_watch": 620,
            "current_deficit_kcal": 550,
            "deficit_status": "On Track (-550 kcal)",
            "guidance": "You have room for a 350-400 kcal high-protein dinner to finish in your optimal 500 kcal fat loss deficit."
        },
        "recommended_workout": {
            "title": "Hypertrophy Push & Core Sculpt",
            "workout_type": "strength",
            "duration_minutes": 45,
            "intensity": "Moderate-High",
            "target_heart_rate_zone": "Zone 2-3 (120 - 150 BPM)",
            "estimated_calories_burn": 320,
            "warmup": "5 min dynamic arm swings, cat-cows, light push-ups",
            "exercises": [
                {
                    "name": "Dumbbell Bench Press",
                    "sets": 4,
                    "reps": "8-10",
                    "rest_seconds": 90,
                    "form_tip": "Slow 3-second eccentric lower to maximize muscle fiber recruitment."
                },
                {
                    "name": "Incline Dumbbell Flyes",
                    "sets": 3,
                    "reps": "12",
                    "rest_seconds": 60,
                    "form_tip": "Focus on deep chest stretch, don't bang weights at the top."
                },
                {
                    "name": "Cable Tricep Pushdowns",
                    "sets": 3,
                    "reps": "12-15",
                    "rest_seconds": 60,
                    "form_tip": "Keep elbows pinned to your ribs throughout."
                },
                {
                    "name": "Incline Treadmill Zone 2 Walk",
                    "sets": 1,
                    "reps": "15 mins",
                    "rest_seconds": 0,
                    "form_tip": "12% incline at 4.5 km/h. Breathe through nose to stay purely in the fat-burning zone."
                }
            ],
            "cooldown": "5 min hamstring and chest doorway stretch"
        },
        "summary": "High recovery day. Hit upper body resistance training to preserve lean mass, followed by 15 mins of Zone 2 walking to accelerate fat oxidation."
    }
    """

    # Prepare context data
    c_in = sum(f.get("calories", 0) for f in today_food_logs)
    p_in = sum(f.get("protein_g", 0) for f in today_food_logs)
    c_target = user_profile.get("daily_calorie_target", 1850)
    p_target = user_profile.get("daily_protein_target", 140)

    user_context = {
        "user_profile": {
            "age": user_profile.get("age", 28),
            "gender": user_profile.get("gender", "male"),
            "height_cm": user_profile.get("height_cm", 175),
            "current_weight_kg": user_profile.get("current_weight_kg", 82),
            "target_weight_kg": user_profile.get("target_weight_kg", 72),
            "daily_calorie_target": c_target,
            "daily_protein_target": p_target,
            "target_deficit_kcal": user_profile.get("target_deficit_kcal", 500)
        },
        "apple_watch_data_today": {
            "steps": health_metrics.get("steps", 0),
            "active_calories_kcal": health_metrics.get("active_calories", 0.0),
            "resting_calories_kcal": health_metrics.get("resting_calories", 0.0),
            "total_calories_kcal": health_metrics.get("total_calories", 0.0),
            "exercise_minutes": health_metrics.get("exercise_minutes", 0),
            "stand_hours": health_metrics.get("stand_hours", 0),
            "resting_heart_rate_bpm": health_metrics.get("resting_heart_rate", 0.0),
            "hrv_ms": health_metrics.get("hrv_ms", 0.0),
            "sleep_hours": health_metrics.get("sleep_hours", 0.0),
            "sleep_deep_hours": health_metrics.get("sleep_deep_hours", 0.0)
        },
        "nutrition_today": {
            "calories_consumed": round(c_in, 1),
            "protein_consumed_g": round(p_in, 1),
            "meals_logged_count": len(today_food_logs),
            "items_logged": [f.get("food_name", "") for f in today_food_logs]
        },
        "recent_history_days": len(recent_history)
    }

    contents = [
        {"parts": [{"text": f"Here is the user's current health, Apple Watch, and nutrition data. Generate today's personalized exercise and weight loss coaching plan: {json.dumps(user_context)}"}]}
    ]

    raw_output = _call_gemini(contents, system_instruction=system_prompt, response_mime_type="application/json")
    return _extract_json(raw_output)

def chat_with_coach(user_message: str, chat_history: List[Dict[str, str]], context_summary: Dict[str, Any]) -> str:
    """
    Interactive Q&A with the AI Health & Weight Loss Coach.
    """
    system_prompt = f"""
    You are the user's personal AI Health & Weight Loss Coach inside their PulseHealth app.
    You have direct, real-time access to their Apple Watch Series 10 biometric stats, food log, and weight loss trajectory.
    
    Current User Context:
    - Current Weight: {context_summary.get('current_weight', '80kg')} | Goal: {context_summary.get('target_weight', '70kg')}
    - Today's Calorie Intake: {context_summary.get('calories_in', 0)} kcal (Protein: {context_summary.get('protein_in', 0)}g)
    - Today's Apple Watch Active Burn: {context_summary.get('active_burn', 0)} kcal | Steps: {context_summary.get('steps', 0)}
    - Sleep Last Night: {context_summary.get('sleep_hours', 'N/A')} hrs | HRV: {context_summary.get('hrv', 'N/A')} ms
    - Net Calorie Deficit Target: {context_summary.get('target_deficit', 500)} kcal
    
    Tone: Pragmatic, direct, science-backed, highly motivating, zero fluff. Answer in concise markdown.
    """

    contents = []
    # Add recent chat history (up to last 6 turns)
    for msg in chat_history[-6:]:
        role = "user" if msg.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

    contents.append({"role": "user", "parts": [{"text": user_message}]})

    return _call_gemini(contents, system_instruction=system_prompt, response_mime_type="text/plain")
