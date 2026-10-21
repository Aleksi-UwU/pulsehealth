import requests
from typing import Optional, Dict, Any

OPEN_FOOD_FACTS_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

def fetch_barcode_nutrition(barcode: str) -> Optional[Dict[str, Any]]:
    """
    Fetch nutritional data for a barcode from Open Food Facts API.
    """
    barcode = barcode.strip().replace(" ", "")
    if not barcode:
        return None

    headers = {
        "User-Agent": "PulseHealthApp/1.0 (health-journey; contact: dev@pulsehealth.local)"
    }
    url = OPEN_FOOD_FACTS_URL.format(barcode=barcode)

    try:
        response = requests.get(url, headers=headers, timeout=6)
        if response.status_code != 200:
            return None
        
        data = response.json()
        if data.get("status") != 1:
            return None

        product = data.get("product", {})
        nutriments = product.get("nutriments", {})

        # Prefer serving values if available, else 100g values
        serving_size = product.get("serving_size") or "1 serving"
        
        # Energy / Calories
        calories = (
            nutriments.get("energy-kcal_serving") or
            nutriments.get("energy-kcal_100g") or
            nutriments.get("energy-kcal") or
            (nutriments.get("energy_100g", 0) / 4.184) # Convert kJ to kcal
        )
        try:
            calories = float(calories or 0.0)
        except (ValueError, TypeError):
            calories = 0.0

        # Protein
        protein = nutriments.get("proteins_serving") or nutriments.get("proteins_100g") or 0.0
        try:
            protein = float(protein or 0.0)
        except (ValueError, TypeError):
            protein = 0.0

        # Carbs
        carbs = nutriments.get("carbohydrates_serving") or nutriments.get("carbohydrates_100g") or 0.0
        try:
            carbs = float(carbs or 0.0)
        except (ValueError, TypeError):
            carbs = 0.0

        # Fat
        fat = nutriments.get("fat_serving") or nutriments.get("fat_100g") or 0.0
        try:
            fat = float(fat or 0.0)
        except (ValueError, TypeError):
            fat = 0.0

        # Fiber
        fiber = nutriments.get("fiber_serving") or nutriments.get("fiber_100g") or 0.0
        try:
            fiber = float(fiber or 0.0)
        except (ValueError, TypeError):
            fiber = 0.0

        name = product.get("product_name") or product.get("product_name_en") or "Packaged Food"
        brands = product.get("brands") or ""
        full_name = f"{brands} {name}".strip() if brands and brands not in name else name

        return {
            "barcode": barcode,
            "food_name": full_name,
            "calories": round(calories, 1),
            "protein_g": round(protein, 1),
            "carbs_g": round(carbs, 1),
            "fat_g": round(fat, 1),
            "fiber_g": round(fiber, 1),
            "serving": serving_size,
            "image_url": product.get("image_front_small_url") or product.get("image_url") or "",
            "brand": brands,
            "source": "barcode"
        }
    except Exception as e:
        print(f"Error fetching barcode {barcode}: {e}")
        return None
