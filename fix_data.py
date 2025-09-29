from pymongo import MongoClient
from bson import ObjectId

# Connect to MongoDB
client = MongoClient("mongodb+srv://Fooxo:2025174371@mrp-database.qopzsma.mongodb.net/")
db = client.MRP_Database

Inventory_Entries = db.inventory
BOM_Entries = db.bom_entry

def generate_part_id(item_name, sequence):
    """Generate item code based on first letters of first two words and sequence."""
    words = item_name.strip().split()
    if len(words) >= 2:
        prefix = words[0][0].upper() + words[1][0].upper()
    elif len(words) == 1:
        prefix = words[0][:2].upper()
    else:
        prefix = "XX"
    return f"{prefix}-{sequence:03d}"

def reset_and_fix_item_codes():
    # STEP 1: wipe all itemCodes in Inventory + BOM
    Inventory_Entries.update_many({}, {"$unset": {"itemCode": ""}})
    BOM_Entries.update_many({}, {"$unset": {"itemCode": ""}})
    print("🔄 Cleared all existing itemCodes.")

    # STEP 2: regenerate in alphabetical order
    entries = list(Inventory_Entries.find().sort("itemName", 1))

    for idx, entry in enumerate(entries, start=1):
        item_name = entry.get("itemName", "")
        if not item_name:
            continue

        new_code = generate_part_id(item_name, idx)

        # Update Inventory item
        Inventory_Entries.update_one(
            {"_id": entry["_id"]},
            {"$set": {"itemCode": new_code}}
        )

        # Update BOM entries that reference this item
        BOM_Entries.update_many(
            {"itemName": item_name},
            {"$set": {"itemCode": new_code}}
        )

        print(f"✅ {item_name} → {new_code}")

    print("🎉 Item codes reset and regenerated successfully.")

if __name__ == "__main__":
    reset_and_fix_item_codes()