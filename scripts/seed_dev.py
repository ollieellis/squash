import requests

BASE_URL = "http://127.0.0.1:8000"

def seed():
    print("--- Seeding Unique Players ---")
    users = [
        {"first_name": "Alice", "last_name": "Smith", "elo": 1200},
        {"first_name": "Bob", "last_name": "Jones", "elo": 1150},
    ]
    for u in users:
        # We try to create; if it returns 409, it means it's already there (idempotent)
        r = requests.post(f"{BASE_URL}/profiles/", json=u)
        if r.status_code == 200:
            print(f"Created: {u['first_name']} {u['last_name']}")
        elif r.status_code == 409:
            print(f"Already exists: {u['first_name']} {u['last_name']}")
        else:
            print(f"Error {r.status_code}: {r.text}")

if __name__ == "__main__":
    seed()
