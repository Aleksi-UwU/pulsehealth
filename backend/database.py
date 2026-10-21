import sqlite3
import os
import json
import requests
from datetime import datetime, date
from typing import Optional, Dict, Any, List

# Check for Turso Cloud Database or local SQLite
TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL", "").strip()
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "").strip()

# Convert libsql:// to https:// for HTTP pipeline API
if TURSO_DATABASE_URL.startswith("libsql://"):
    TURSO_HTTP_URL = TURSO_DATABASE_URL.replace("libsql://", "https://")
elif TURSO_DATABASE_URL.startswith("http://") or TURSO_DATABASE_URL.startswith("https://"):
    TURSO_HTTP_URL = TURSO_DATABASE_URL
else:
    TURSO_HTTP_URL = ""

USE_TURSO = bool(TURSO_HTTP_URL and TURSO_AUTH_TOKEN)

# Dynamic local DB path (Vercel serverless has a read-only filesystem except /tmp)
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    LOCAL_DB_PATH = "/tmp/health_journey.db"
else:
    LOCAL_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "health_journey.db")

def _to_turso_arg(v: Any) -> Dict[str, Any]:
    if v is None:
        return {"type": "null"}
    if isinstance(v, bool):
        return {"type": "integer", "value": "1" if v else "0"}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    return {"type": "text", "value": str(v)}

def _turso_execute(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Execute SQL query against Turso Cloud Database via REST pipeline."""
    url = f"{TURSO_HTTP_URL}/v2/pipeline"
    headers = {
        "Authorization": f"Bearer {TURSO_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    stmt = {
        "sql": sql,
        "args": [_to_turso_arg(p) for p in params]
    }
    payload = {
        "requests": [
            {"type": "execute", "stmt": stmt},
            {"type": "close"}
        ]
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=8)
    if resp.status_code != 200:
        raise RuntimeError(f"Turso API error ({resp.status_code}): {resp.text}")
    
    data = resp.json()
    results = data.get("results", [])
    if not results or results[0].get("type") != "ok":
        error_msg = results[0].get("error", {}).get("message", "Unknown Turso error") if results else "No results"
        raise RuntimeError(f"Turso query error: {error_msg}")
    
    res = results[0]["response"]["result"]
    cols = [c["name"] for c in res.get("cols", [])]
    rows = []
    for r in res.get("rows", []):
        row_dict = {}
        for idx, col_name in enumerate(cols):
            val_obj = r[idx]
            val = val_obj.get("value")
            if val_obj.get("type") == "integer" and val is not None:
                val = int(val)
            elif val_obj.get("type") == "float" and val is not None:
                val = float(val)
            row_dict[col_name] = val
        rows.append(row_dict)
    return rows

def get_connection():
    conn = sqlite3.connect(LOCAL_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def execute_query(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Unified query executor supporting both Turso Cloud and local SQLite."""
    if USE_TURSO:
        return _turso_execute(sql, params)
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        result = [dict(r) for r in rows]
        conn.commit()
        conn.close()
        return result

def execute_mutation(sql: str, params: tuple = ()) -> int:
    """Unified mutation executor supporting both Turso Cloud and local SQLite."""
    if USE_TURSO:
        _turso_execute(sql, params)
        return 1
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        last_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return last_id or 1

def init_db():
    queries = [
        """
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
        """,
        """
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
        """,
        """
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
        """,
        """
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
        """,
        """
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
        """,
        """
        CREATE TABLE IF NOT EXISTS water_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount_ml INTEGER NOT NULL,
            logged_at TEXT NOT NULL
        )
        """
    ]

    for q in queries:
        execute_mutation(q)

    # Seed default user profile if empty
    profiles = execute_query("SELECT COUNT(*) as cnt FROM user_profile WHERE id = 1")
    count = profiles[0].get("cnt", 0) if profiles else 0
    if count == 0:
        execute_mutation("""
            INSERT INTO user_profile (
                id, name, age, gender, height_cm, current_weight_kg, target_weight_kg,
                activity_level, daily_calorie_target, daily_protein_target,
                daily_carb_target, daily_fat_target, target_deficit_kcal, sync_token, updated_at
            ) VALUES (
                1, 'Harshil', 28, 'male', 175.0, 82.0, 72.0,
                'moderately_active', 1850, 140, 180, 55, 500, 'health-sync-token-12345', ?
            )
        """, (datetime.utcnow().isoformat(),))

# Profile operations
def get_profile() -> Dict[str, Any]:
    rows = execute_query("SELECT * FROM user_profile WHERE id = 1")
    return rows[0] if rows else {}

def update_profile(data: Dict[str, Any]) -> Dict[str, Any]:
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
        query_str = f"UPDATE user_profile SET {', '.join(updates)} WHERE id = ?"
        execute_mutation(query_str, tuple(values))
        
    return get_profile()

# Health metrics operations
def upsert_health_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    m_date = metrics.get("date", date.today().isoformat())
    active = float(metrics.get("active_calories", 0.0) or 0.0)
    resting = float(metrics.get("resting_calories", 0.0) or 0.0)
    total = float(metrics.get("total_calories", 0.0) or (active + resting))

    execute_mutation("""
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

    # Update profile current weight if weight is provided
    if float(metrics.get("weight_kg", 0.0) or 0.0) > 0:
        execute_mutation("UPDATE user_profile SET current_weight_kg = ?, updated_at = ? WHERE id = 1",
                         (float(metrics["weight_kg"]), datetime.utcnow().isoformat()))

    rows = execute_query("SELECT * FROM health_metrics WHERE date = ?", (m_date,))
    return rows[0] if rows else {}

def get_health_metrics(m_date: str) -> Optional[Dict[str, Any]]:
    rows = execute_query("SELECT * FROM health_metrics WHERE date = ?", (m_date,))
    return rows[0] if rows else None

# Food log operations
def add_food_log(item: Dict[str, Any]) -> Dict[str, Any]:
    m_date = item.get("date", date.today().isoformat())
    now_iso = datetime.utcnow().isoformat()
    execute_mutation("""
    INSERT INTO food_logs (
        date, meal_type, food_name, calories, protein_g,
        carbs_g, fat_g, fiber_g, serving, source, barcode, logged_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        m_date,
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
        now_iso
    ))
    rows = execute_query("SELECT * FROM food_logs WHERE date = ? ORDER BY id DESC LIMIT 1", (m_date,))
    return rows[0] if rows else {}

def delete_food_log(log_id: int) -> bool:
    execute_mutation("DELETE FROM food_logs WHERE id = ?", (log_id,))
    return True

def get_food_logs(target_date: str) -> List[Dict[str, Any]]:
    return execute_query("SELECT * FROM food_logs WHERE date = ? ORDER BY id ASC", (target_date,))

# Water log operations
def add_water_intake(target_date: str, amount_ml: int) -> int:
    execute_mutation("""
        INSERT INTO water_logs (date, amount_ml, logged_at) VALUES (?, ?, ?)
    """, (target_date, amount_ml, datetime.utcnow().isoformat()))
    return get_water_intake(target_date)

def get_water_intake(target_date: str) -> int:
    rows = execute_query("SELECT SUM(amount_ml) as total_ml FROM water_logs WHERE date = ?", (target_date,))
    if rows and rows[0].get("total_ml") is not None:
        return int(rows[0]["total_ml"])
    return 0

# Workout operations
def add_workout(workout: Dict[str, Any]) -> Dict[str, Any]:
    m_date = workout.get("date", date.today().isoformat())
    exercises = workout.get("exercises_json", "[]")
    if isinstance(exercises, (list, dict)):
        exercises = json.dumps(exercises)

    execute_mutation("""
    INSERT INTO workouts (
        date, title, workout_type, duration_minutes,
        calories_burned, completed, exercises_json, notes, logged_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        m_date,
        workout.get("title", "Daily Workout"),
        workout.get("workout_type", "strength"),
        int(workout.get("duration_minutes", 30)),
        float(workout.get("calories_burned", 0.0)),
        int(workout.get("completed", 0)),
        exercises,
        workout.get("notes", ""),
        datetime.utcnow().isoformat()
    ))
    rows = execute_query("SELECT * FROM workouts WHERE date = ? ORDER BY id DESC LIMIT 1", (m_date,))
    res = rows[0] if rows else {}
    if res and res.get("exercises_json"):
        try:
            res["exercises"] = json.loads(res["exercises_json"])
        except Exception:
            res["exercises"] = []
    return res

def toggle_workout_completed(workout_id: int) -> Optional[Dict[str, Any]]:
    execute_mutation("UPDATE workouts SET completed = 1 - completed WHERE id = ?", (workout_id,))
    rows = execute_query("SELECT * FROM workouts WHERE id = ?", (workout_id,))
    res = rows[0] if rows else None
    if res and res.get("exercises_json"):
        try:
            res["exercises"] = json.loads(res["exercises_json"])
        except Exception:
            res["exercises"] = []
    return res

def get_workouts(target_date: str) -> List[Dict[str, Any]]:
    rows = execute_query("SELECT * FROM workouts WHERE date = ? ORDER BY id ASC", (target_date,))
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
    rec_date = rec.get("date", date.today().isoformat())
    w_json = rec.get("recommended_workout", {})
    if isinstance(w_json, (dict, list)):
        w_json = json.dumps(w_json)

    c_analysis = rec.get("calorie_deficit_analysis", "")
    if isinstance(c_analysis, (dict, list)):
        c_analysis = json.dumps(c_analysis)

    execute_mutation("""
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
    return get_ai_recommendation(rec_date) or rec

def get_ai_recommendation(target_date: str) -> Optional[Dict[str, Any]]:
    rows = execute_query("SELECT * FROM ai_recommendations WHERE date = ?", (target_date,))
    if not rows:
        return None
    res = rows[0]
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
    health_rows = execute_query("""
        SELECT * FROM health_metrics ORDER BY date DESC LIMIT ?
    """, (days,))
    
    food_rows = execute_query("""
        SELECT date, 
               SUM(calories) as total_calories_in,
               SUM(protein_g) as total_protein_g,
               SUM(carbs_g) as total_carbs_g,
               SUM(fat_g) as total_fat_g,
               SUM(fiber_g) as total_fiber_g
        FROM food_logs
        GROUP BY date
        ORDER BY date DESC LIMIT ?
    """, (days,))

    food_map = {r["date"]: dict(r) for r in food_rows}
    combined = []
    for hd in health_rows:
        f = food_map.get(hd["date"], {
            "total_calories_in": 0.0,
            "total_protein_g": 0.0,
            "total_carbs_g": 0.0,
            "total_fat_g": 0.0,
            "total_fiber_g": 0.0
        })
        hd["nutrition"] = f
        
        energy_out = hd["total_calories"] if hd["total_calories"] > 0 else (hd["resting_calories"] + hd["active_calories"])
        c_in = f["total_calories_in"]
        deficit = energy_out - c_in if energy_out > 0 else 0
        hd["energy_out_kcal"] = round(energy_out, 1)
        hd["energy_in_kcal"] = round(c_in, 1)
        hd["deficit_kcal"] = round(deficit, 1)
        combined.append(hd)
    
    return sorted(combined, key=lambda x: x["date"])
