"""City rotation for auto-switching during discovery."""

from __future__ import annotations

CITY_TIERS = {
    "tier_1_india": ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Pune", "Kolkata", "Ahmedabad"],
    "tier_2_india": ["Jaipur", "Lucknow", "Kanpur", "Nagpur", "Indore", "Thane", "Bhopal", "Visakhapatnam", "Patna", "Vadodara", "Ghaziabad", "Ludhiana", "Agra", "Nashik", "Faridabad", "Meerut", "Rajkot", "Varanasi"],
    "tier_3_india": ["Srinagar", "Amritsar", "Allahabad", "Ranchi", "Guwahati", "Chandigarh", "Mysore", "Coimbatore", "Kochi", "Thiruvananthapuram", "Mangalore", "Hubli", "Belgaum", "Dehradun", "Gwalior", "Raipur", "Jabalpur", "Jodhpur"],
    "tier_1_global": ["New York", "London", "Singapore", "Dubai", "Sydney", "Toronto"],
}


class CityRotator:
    """Rotates through cities until target lead count is reached."""

    def __init__(self, target_count: int, preset: dict | None = None) -> None:
        self.target = target_count
        self.found = 0
        self.exhausted_cities: set[str] = set()
        self.city_queue = self._build_queue(preset)

    def _build_queue(self, preset: dict | None) -> list[str]:
        cities: list[str] = []
        if preset and "target" in preset and "cities" in preset["target"]:
            custom = preset["target"]["cities"]
            if custom != ["auto_rotate"]:
                return custom
        for tier in ["tier_1_india", "tier_2_india", "tier_3_india", "tier_1_global"]:
            cities.extend(CITY_TIERS.get(tier, []))
        return cities

    def get_next_city(self) -> str | None:
        for city in self.city_queue:
            if city not in self.exhausted_cities:
                return city
        return None

    def mark_exhausted(self, city: str, found_count: int) -> None:
        if found_count < 5:
            self.exhausted_cities.add(city)
        self.found += found_count

    def is_complete(self) -> bool:
        return self.found >= self.target
