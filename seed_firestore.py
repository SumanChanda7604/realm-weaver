import google.auth
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-02-c19c65f27e59"

def seed_database():
    print(f"Initializing Firestore client for project: {PROJECT_ID}")
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    db = firestore.Client(project=PROJECT_ID, credentials=credentials)
    
    spells_ref = db.collection("spells")
    
    initial_spells = [
        {
            "id": "tidal_surge",
            "name": "Tidal Surge",
            "category": "Water",
            "damage": 150,
            "spirit_stone_cost": 10,
            "unlock_level": 1,
            "description": "Surges azure mountain waters to crush enemies."
        },
        {
            "id": "infernal_flame",
            "name": "Infernal Flame",
            "category": "Fire",
            "damage": 380,
            "spirit_stone_cost": 10,
            "unlock_level": 2,
            "description": "Unleashes blazing dragon fire from deep magma."
        },
        {
            "id": "solar_radiance",
            "name": "Solar Radiance",
            "category": "Holy",
            "damage": 850,
            "spirit_stone_cost": 10,
            "unlock_level": 3,
            "description": "Calls down celestial golden solar light."
        },
        {
            "id": "chaos_oblivion",
            "name": "Chaos Oblivion",
            "category": "Chaos",
            "damage": 2400,
            "spirit_stone_cost": 10,
            "unlock_level": 4,
            "description": "Summons primordial void chaos energy."
        }
    ]
    
    for spell in initial_spells:
        doc_id = spell["id"]
        spells_ref.document(doc_id).set(spell)
        print(f"Seeded spell: {spell['name']} ({doc_id})")
        
    print("✅ Firestore seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
