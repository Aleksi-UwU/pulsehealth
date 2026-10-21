import os
import sys

backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import database as db
import openfoodfacts as off
import ai_coach

print("--- 1. Testing Database Initialization ---")
db.init_db()
profile = db.get_profile()
print("User profile loaded:", profile.get("name"), "| Goal Weight:", profile.get("target_weight_kg"))

print("\n--- 2. Testing Apple Health Telemetry Sync ---")
mock_metrics = {
    "date": "2026-10-21",
    "steps": 9240,
    "active_calories": 610.0,
    "resting_calories": 1780.0,
    "total_calories": 2390.0,
    "exercise_minutes": 48,
    "stand_hours": 12,
    "resting_heart_rate": 56.0,
    "hrv_ms": 62.0,
    "sleep_hours": 7.6,
    "weight_kg": 81.4,
    "source": "apple_watch_series_10"
}
saved_health = db.upsert_health_metrics(mock_metrics)
print("Apple Health synced successfully! Active Cal:", saved_health.get("active_calories"), "HRV:", saved_health.get("hrv_ms"))

print("\n--- 3. Testing Food Logging ---")
food_item = db.add_food_log({
    "date": "2026-10-21",
    "meal_type": "breakfast",
    "food_name": "Greek Yogurt with Berries & Honey",
    "calories": 220,
    "protein_g": 20,
    "carbs_g": 24,
    "fat_g": 4,
    "fiber_g": 3,
    "serving": "1 bowl (200g)",
    "source": "manual"
})
print("Food logged:", food_item["food_name"], f"({food_item['calories']} kcal, {food_item['protein_g']}g P)")

print("\n--- 4. Testing Open Food Facts Barcode Lookup ---")
# Barcode for Coca Cola Zero / common grocery item
barcode_test = "5449000000996"
prod = off.fetch_barcode_nutrition(barcode_test)
if prod:
    print("Barcode found:", prod["food_name"], f"({prod['calories']} kcal, {prod['protein_g']}g P)")
else:
    print("Barcode lookup returned None (offline or not found), fallback works.")

print("\n--- 5. Testing Gemini AI Food Text Parser ---")
try:
    parsed_food = ai_coach.parse_food_text("2 scrambled eggs, 1 slice whole wheat toast, black coffee")
    print("AI Parsed Items:", len(parsed_food.get("items", [])))
    print("Parsed Totals:", parsed_food.get("totals"))
    print("Dietitian Tip:", parsed_food.get("dietitian_tip"))
except Exception as e:
    print("AI Food Parse Error:", e)

print("\n--- 6. Testing AI Daily Exercise & Deficit Recommendation ---")
try:
    rec = ai_coach.recommend_daily_workout_and_deficit(
        user_profile=profile,
        health_metrics=saved_health,
        today_food_logs=db.get_food_logs("2026-10-21"),
        recent_history=[]
    )
    rec["date"] = "2026-10-21"
    saved_rec = db.save_ai_recommendation(rec)
    print("AI Readiness:", saved_rec.get("readiness_label"), f"({saved_rec.get('readiness_score')}/100)")
    w = saved_rec.get("recommended_workout", {})
    print("AI Recommended Routine:", w.get("title"), f"({w.get('duration_minutes')} mins, {w.get('target_heart_rate_zone')})")
    print("Exercises Prescribed:", len(w.get("exercises", [])))
except Exception as e:
    print("AI Coach Recommendation Error:", e)

print("\nSystem verification complete!")
