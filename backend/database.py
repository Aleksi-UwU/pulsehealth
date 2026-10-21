import sqlite3
import os
import json
from datetime import datetime, date
from typing import Optional, Dict, Any, List

# Dynamic DB path: Vercel serverless has a read-only filesystem except /tmp
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    DB_PATH = "/tmp/health_journey.db"
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "health_journey.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # User Profile table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_profile (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        name TEXT DEFAULT 'Harshil',
        age INTEGER DEFAULT 28,
        gender TEXT DEFAULT 'male',
        height_cm REAL DEFAULT 175.0,
        current_weight_kg REAL DEFAULT 82.0,
        target_weight_kg REAL DEFAULT 72.0,
        activity_level TEXT DEFAULT 'moderately_active',
        daily_calorie_target INTEGER DEFAULT 1850,
        daily_protein_target INTEGER DEFAULT 140,
        daily_carb_target INTEGER DEFAULT 180,
        daily_fat_target INTEGER DEFAULT 55,
        target_deficit_kcal INTEGER DEFAULT 500,
        sync_token TEXT DEFAULT 'health-sync-token-12345',
        updated_at TEXT
    )
    """)

    # Seed default user if empty
    cursor.execute("SELECT COUNT(*) FROM user_profile WHERE id = 1")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO user_profile (
            id, name, age, gender, height_cm, current_weight_kg, target_weight_kg,
            activity_level, daily_calorie_target, daily_protein_target,
            daily_carb_target, daily_fat_target, target_deficit_kcal, sync_token, updated_at
        ) VALUES (
            1, 'Harshil', 28, 'male', 175.0, 82.0, 72.0,
            'moderately_active', 1850, 140, 180, 55, 500, 'health-sync-token-12345', ?
        )
        """, (datetime.utcnow().isoformat(),))

    # Apple Health / Watch Metrics
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS health_metrics (
        date TEXT PRIMARY KEY,
        steps INTEGER DEFAULT 0,
        active_calories REAL DEFAULT 0.0,
        resting_calories REAL DEFAULT 0.0,
        total_calories REAL DEFAULT 0.0,
        exercise_minutes INTEGER DEFAULT 0,
        stand_hours INTEGER DEFAULT 0,
        resting_heart_rate REAL DEFAULT 0.0,
        hrv_ms REAL DEFAULT 0.0,
        sleep_hours REAL DEFAULT 0.0,
        sleep_deep_hours REAL DEFAULT 0.0,
        weight_kg REAL DEFAULT 0.0,
        synced_at TEXT,
        source TEXT DEFAULT 'apple_health'
    )
    """)

    # Food Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS food_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        meal_type TEXT NOT NULL,
        food_name TEXT NOT NULL,
        calories REAL NOT NULL,
        protein_g REAL DEFAULT 0.0,
        carbs_g REAL DEFAULT 0.0,
        fat_g REAL DEFAULT 0.0,
        fiber_g REAL DEFAULT 0.0,
        serving TEXT DEFAULT '1 serving',
        source TEXT DEFAULT 'manual',
        barcode TEXT,
        logged_at TEXT NOT NULL
    )
    """)

    # Workouts & Exercises
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        title TEXT NOT NULL,
        workout_type TEXT DEFAULT 'strength',
        duration_minutes INTEGER DEFAULT 30,
        calories_burned REAL DEFAULT 0.0,
        completed INTEGER DEFAULT 0,
        exercises_json TEXT DEFAULT '[]',
        notes TEXT DEFAULT '',
        logged_at TEXT NOT NULL
    )
    """)

    # AI Daily Recommendations & Workout Prescriptions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE NOT NULL,
        readiness_score INTEGER DEFAULT 80,
        readiness_label TEXT DEFAULT 'Optimal',
        summary TEXT NOT NULL,
        calorie_deficit_analysis TEXT NOT NULL,
        recommended_workout TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

# Profile operations
def get_profile() -> Dict[str, Any]:
    conn = get_connection()
    row = conn.cursor().execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else {}

def update_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    fields = [
        "name", "age", "gender", "height_cm", "current_weight_kg",
        "target_weight_kg", "activity_level", "daily_calorie_target",
        "daily_protein_target", "daily_carb_target", "daily_fat_target",
        "target_deficit_kcal", "sync_token"
    ]
    updates = []
    values = []
    for f in fields:
        if f in data:
            updates.append(f"{f} = ?")
            values.append(data[f])
    
    if updates:
        updates.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        values.append(1)
        query = f"UPDATE user_profile SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
    conn.close()
    return get_profile()

# Health metrics operations
def upsert_health_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    m_date = metrics.get("date", date.today().isoformat())
    
    # Calculate total calories if resting and active are available
    active = float(metrics.get("active_calories", 0.0) or 0.0)
    resting = float(metrics.get("resting_calories", 0.0) or 0.0)
    total = float(metrics.get("total_calories", 0.0) or (active + resting))

    cursor.execute("""
    INSERT INTO health_metrics (
        date, steps, active_calories, resting_calories, total_calories,
        exercise_minutes, stand_hours, resting_heart_rate, hrv_ms,
        sleep_hours, sleep_deep_hours, weight_kg, synced_at, source
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(date) DO UPDATE SET
        steps = excluded.steps,
        active_calories = excluded.active_calories,
        resting_calories = CASE WHEN excluded.resting_calories > 0 THEN excluded.resting_calories ELSE health_metrics.resting_calories END,
        total_calories = excluded.total_calories,
        exercise_minutes = excluded.exercise_minutes,
        stand_hours = excluded.stand_hours,
        resting_heart_rate = CASE WHEN excluded.resting_heart_rate > 0 THEN excluded.resting_heart_rate ELSE health_metrics.resting_heart_rate END,
        hrv_ms = CASE WHEN excluded.hrv_ms > 0 THEN excluded.hrv_ms ELSE health_metrics.hrv_ms END,
        sleep_hours = CASE WHEN excluded.sleep_hours > 0 THEN excluded.sleep_hours ELSE health_metrics.sleep_hours END,
        sleep_deep_hours = CASE WHEN excluded.sleep_deep_hours > 0 THEN excluded.sleep_deep_hours ELSE health_metrics.sleep_deep_hours END,
        weight_kg = CASE WHEN excluded.weight_kg > 0 THEN excluded.weight_kg ELSE health_metrics.weight_kg END,
        synced_at = excluded.synced_at,
        source = excluded.source
    """, (
        m_date,
        int(metrics.get("steps", 0) or 0),
        active,
        resting,
        total,
        int(metrics.get("exercise_minutes", 0) or 0),
        int(metrics.get("stand_hours", 0) or 0),
        float(metrics.get("resting_heart_rate", 0.0) or 0.0),
        float(metrics.get("hrv_ms", 0.0) or 0.0),
        float(metrics.get("sleep_hours", 0.0) or 0.0),
        float(metrics.get("sleep_deep_hours", 0.0) or 0.0),
        float(metrics.get("weight_kg", 0.0) or 0.0),
        datetime.utcnow().isoformat(),
        metrics.get("source", "apple_health")
    ))
    conn.commit()

    # Also update profile current weight if weight provided
    if float(metrics.get("weight_kg", 0.0) or 0.0) > 0:
        cursor.execute("UPDATE user_profile SET current_weight_kg = ?, updated_at = ? WHERE id = 1",
                       (float(metrics["weight_kg"]), datetime.utcnow().isoformat()))
        conn.commit()

    row = cursor.execute("SELECT * FROM health_metrics WHERE date = ?", (m_date,)).fetchone()
    conn.close()
    return dict(row) if row else {}

def get_health_metrics(m_date: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.cursor().execute("SELECT * FROM health_metrics WHERE date = ?", (m_date,)).fetchone()
    conn.close()
    return dict(row) if row else None

# Food log operations
def add_food_log(item: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO food_logs (
        date, meal_type, food_name, calories, protein_g,
        carbs_g, fat_g, fiber_g, serving, source, barcode, logged_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item.get("date", date.today().isoformat()),
        item.get("meal_type", "snack").lower(),
        item.get("food_name", "Meal item"),
        float(item.get("calories", 0.0)),
        float(item.get("protein_g", 0.0)),
        float(item.get("carbs_g", 0.0)),
        float(item.get("fat_g", 0.0)),
        float(item.get("fiber_g", 0.0)),
        item.get("serving", "1 serving"),
        item.get("source", "manual"),
        item.get("barcode", None),
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    new_id = cursor.lastrowid
    row = cursor.execute("SELECT * FROM food_logs WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return dict(row)

def delete_food_log(log_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM food_logs WHERE id = ?", (log_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_food_logs(target_date: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.cursor().execute(
        "SELECT * FROM food_logs WHERE date = ? ORDER BY id ASC", (target_date,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Workout operations
def add_workout(workout: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    exercises = workout.get("exercises_json", "[]")
    if isinstance(exercises, (list, dict)):
        exercises = json.dumps(exercises)

    cursor.execute("""
    INSERT INTO workouts (
        date, title, workout_type, duration_minutes,
        calories_burned, completed, exercises_json, notes, logged_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        workout.get("date", date.today().isoformat()),
        workout.get("title", "Daily Workout"),
        workout.get("workout_type", "strength"),
        int(workout.get("duration_minutes", 30)),
        float(workout.get("calories_burned", 0.0)),
        int(workout.get("completed", 0)),
        exercises,
        workout.get("notes", ""),
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    new_id = cursor.lastrowid
    row = cursor.execute("SELECT * FROM workouts WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return dict(row)

def toggle_workout_completed(workout_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE workouts SET completed = 1 - completed WHERE id = ?", (workout_id,))
    conn.commit()
    row = cursor.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_workouts(target_date: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.cursor().execute(
        "SELECT * FROM workouts WHERE date = ? ORDER BY id ASC", (target_date,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["exercises"] = json.loads(d["exercises_json"])
        except Exception:
            d["exercises"] = []
        result.append(d)
    return result

# AI Recommendations
def save_ai_recommendation(rec: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    rec_date = rec.get("date", date.today().isoformat())
    w_json = rec.get("recommended_workout", {})
    if isinstance(w_json, (dict, list)):
        w_json = json.dumps(w_json)

    c_analysis = rec.get("calorie_deficit_analysis", "")
    if isinstance(c_analysis, (dict, list)):
        c_analysis = json.dumps(c_analysis)

    cursor.execute("""
    INSERT INTO ai_recommendations (
        date, readiness_score, readiness_label, summary,
        calorie_deficit_analysis, recommended_workout, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(date) DO UPDATE SET
        readiness_score = excluded.readiness_score,
        readiness_label = excluded.readiness_label,
        summary = excluded.summary,
        calorie_deficit_analysis = excluded.calorie_deficit_analysis,
        recommended_workout = excluded.recommended_workout,
        created_at = excluded.created_at
    """, (
        rec_date,
        int(rec.get("readiness_score", 85)),
        rec.get("readiness_label", "Optimal"),
        rec.get("summary", ""),
        c_analysis,
        w_json,
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    row = cursor.execute("SELECT * FROM ai_recommendations WHERE date = ?", (rec_date,)).fetchone()
    conn.close()
    res = dict(row)
    try:
        res["recommended_workout"] = json.loads(res["recommended_workout"])
    except Exception:
        pass
    try:
        res["calorie_deficit_analysis"] = json.loads(res["calorie_deficit_analysis"])
    except Exception:
        pass
    return res

def get_ai_recommendation(target_date: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.cursor().execute(
        "SELECT * FROM ai_recommendations WHERE date = ?", (target_date,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    res = dict(row)
    try:
        res["recommended_workout"] = json.loads(res["recommended_workout"])
    except Exception:
        pass
    try:
        res["calorie_deficit_analysis"] = json.loads(res["calorie_deficit_analysis"])
    except Exception:
        pass
    return res

# History and trends
def get_recent_history(days: int = 14) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    # Fetch health metrics
    health_rows = cursor.execute("""
        SELECT * FROM health_metrics ORDER BY date DESC LIMIT ?
    """, (days,)).fetchall()
    
    # Fetch food totals grouped by date
    food_rows = cursor.execute("""
        SELECT date, 
               SUM(calories) as total_calories_in,
               SUM(protein_g) as total_protein_g,
               SUM(carbs_g) as total_carbs_g,
               SUM(fat_g) as total_fat_g
        FROM food_logs
        GROUP BY date
        ORDER BY date DESC LIMIT ?
    """, (days,)).fetchall()
    conn.close()

    food_map = {r["date"]: dict(r) for r in food_rows}
    combined = []
    for h in health_rows:
        hd = dict(h)
        f = food_map.get(hd["date"], {
            "total_calories_in": 0.0,
            "total_protein_g": 0.0,
            "total_carbs_g": 0.0,
            "total_fat_g": 0.0
        })
        hd["nutrition"] = f
        
        # Calculate net balance and deficit
        # Net Energy = Calories In - Total Energy Burned (or Resting + Active)
        energy_out = hd["total_calories"] if hd["total_calories"] > 0 else (hd["resting_calories"] + hd["active_calories"])
        c_in = f["total_calories_in"]
        deficit = energy_out - c_in if energy_out > 0 else 0
        hd["energy_out_kcal"] = round(energy_out, 1)
        hd["energy_in_kcal"] = round(c_in, 1)
        hd["deficit_kcal"] = round(deficit, 1)
        combined.append(hd)
    
    return sorted(combined, key=lambda x: x["date"])
