import os
import requests
from dotenv import load_dotenv

load_dotenv()


class FirebaseManager:
    """
    Fetches logistics data from Firebase Realtime Database via the REST API.
    Only live_shipments is available; historical returns an empty list.
    """

    def __init__(self, live_collection: str = "live_shipments"):
        
        self._live_collection = live_collection
        raw = os.getenv("FIREBASE_CRED_PATH", "").strip()
        if raw.endswith("/.json"):
            self._base_url = raw[: -len("/.json")]
        elif raw.endswith(".json"):
            self._base_url = raw[: -len(".json")]
        else:
            self._base_url = raw.rstrip("/")


    def fetch_live(self) -> list[dict]:
        """Fetch all records from the live_shipments node via the REST API."""
        url = f"{self._base_url}/{self._live_collection}.json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data is None:
            return []
        
        if isinstance(data, dict):
            return [v for v in data.values() if isinstance(v, dict)]
        if isinstance(data, list):
            return [item for item in data if item is not None]
        return []

    def fetch_all(self) -> dict:
        """Returns live shipments"""
        return {
            "live": self.fetch_live(),
        }
