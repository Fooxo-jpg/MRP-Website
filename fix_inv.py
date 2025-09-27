from pymongo import MongoClient
from bson import ObjectId

client = MongoClient("mongodb+srv://Fooxo:2025174371@mrp-database.qopzsma.mongodb.net/")
db = client.MRP_Database
Inventory_Entries = db.inventory

def generate_part_id(item_name, sequence):
    """Simple part code generator based on first letters and sequence."""
    words = item_name.strip().split()
    prefix = ""
    if len(words) >= 2:
        prefix = words[0][0].upper() + words[1][0].upper()
    elif len(words) == 1:
        prefix = words[0][:2].upper()
    else:
        prefix = "XX"
    return f"{prefix}-{sequence:03d}"

# Fetch all items
items = list(Inventory_Entries.find().sort("_id", 1))

for idx, item in enumerate(items, start=1):
    update_doc = {}

    # Integers: currentStock, reorderLevel, reorderQty, leadTime
    for field in ["currentStock", "reorderLevel", "reorderQty", "leadTime"]:
        value = item.get(field, 0)
        try:
            update_doc[field] = int(float(value))
        except (ValueError, TypeError):
            update_doc[field] = 0

    # Floats with 2 decimals: costPerUnit
    value = item.get("costPerUnit", 0)
    try:
        update_doc["costPerUnit"] = round(float(value), 2)
    except (ValueError, TypeError):
        update_doc["costPerUnit"] = 0.00

    # totalValue = currentStock * costPerUnit, rounded to 2 decimals
    update_doc["totalValue"] = round(update_doc["currentStock"] * update_doc["costPerUnit"], 2)

    # Generate itemCode if missing
    if not item.get("itemCode"):
        item_name = item.get("itemName", f"Item{idx}")
        update_doc["itemCode"] = generate_part_id(item_name, idx)

    # Update the document
    Inventory_Entries.update_one({"_id": item["_id"]}, {"$set": update_doc})

print(f"Updated {len(items)} inventory items successfully.")
