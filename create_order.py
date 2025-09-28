from pymongo import MongoClient
from datetime import datetime, timedelta

# === DATABASE CONNECTION ===
client = MongoClient("mongodb+srv://Fooxo:2025174371@mrp-database.qopzsma.mongodb.net/")
db = client.MRP_Database

BOM_Entries = db.bom_entry
Inventory_Entries = db.inventory
PurchaseOrders = db.purchasedOrders
Notifications = db.notifications

# === FUNCTIONS ===
def generate_po_number(): # FORMAT IS PO-[YEAR]-XX
    year = datetime.now().year
    last_po = PurchaseOrders.find({"poNumber": {"$regex": f"^PO-{year}-"}}).sort("poNumber", -1).limit(1)
    try:
        last_po_number = list(last_po)[0]["poNumber"]
        last_count = int(last_po_number.split("-")[2])
        next_count = last_count + 1
    except IndexError:
        next_count = 1
    return f"PO-{year}-{next_count:02d}"


def get_order_date():
    return datetime.now().strftime("%Y-%m-%d")


def get_unit_price(product_name): # GET UNIT PRICE OF A PRODUCT FROM BOM
    bom_item = BOM_Entries.find_one({"productName": {"$regex": f"^{product_name}$", "$options": "i"}})
    if bom_item:
        return float(bom_item.get("costPerUnit", 0))
    return None

def get_lead_time(product_name):
    bom_item = BOM_Entries.find_one({"productName": {"$regex": f"^{product_name}$", "$options": "i"}})
    if bom_item:
        return float(bom_item.get("leadTime", 0))
    return 0

def calculate_total_cost(unit_price, qty_ordered):
    return unit_price * qty_ordered

def calculate_estimated_delivery(order_date_str, lead_time, qty_ordered):
    order_date = datetime.strptime(order_date_str, "%Y-%m-%d")
    est_days = (lead_time * qty_ordered) / 2
    est_date = order_date + timedelta(days=est_days)
    return est_date.strftime("%Y-%m-%d")

def add_notification(title, message, type="info"):
    Notifications.insert_one({
        "type": type,
        "title": title,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

# SUBTRACT ITEMS USED IN ORDER FROM INVENTORY STOCK
def update_inventory_for_order(product_name, qty_ordered):
    bom_items = list(BOM_Entries.find({"productName": product_name}))
    if not bom_items:
        print(f"⚠ No BOM found for {product_name}, skipping inventory update.")
        return

    for item in bom_items:
        item_name = item.get("itemName")
        qty_per_unit = float(item.get("qtyPerUnit", 0))

        total_needed = qty_ordered * qty_per_unit

        # find item in inventory
        inv_item = Inventory_Entries.find_one({"itemName": item_name})
        if inv_item:
            current_stock = float(inv_item.get("currentStock", 0))
            new_stock = max(current_stock - total_needed, 0)  # avoid negative

            Inventory_Entries.update_one(
                {"_id": inv_item["_id"]},
                {"$set": {"currentStock": new_stock}}
            )
            print(f"✅ Updated {item_name}: -{total_needed}, new stock = {new_stock}")
        else:
            print(f"❌ {item_name} not found in inventory, skipping.")

# === MAIN SCRIPT ===
if __name__ == "__main__":
    print("=== CREATE PURCHASE ORDER ===")

    # Ask for product name until it exists
    product_name = None
    unit_price = None
    while not unit_price:
        user_input = input("Enter Product Name: ").strip()
        unit_price = get_unit_price(user_input)
        if not unit_price:
            print(f"❌ '{user_input}' not found in BOM. Try again.")
        else:
            product_name = user_input

    # ASK FOR QUANTITY
    while True:
        try:
            qty = float(input("Enter Quantity: "))
            if qty <= 0:
                print("❌ Quantity must be greater than 0.")
                continue
            break
        except ValueError:
            print("❌ Invalid number. Try again.")

    # Generate order details
    po_number = generate_po_number()
    order_date = get_order_date()
    total_cost = calculate_total_cost(unit_price, qty)

    lead_time = get_lead_time(product_name)
    estimated_delivery = calculate_estimated_delivery(order_date, lead_time, qty)

    # Save into DB
    PurchaseOrders.insert_one({
        "poNumber": po_number,
        "orderDate": order_date,
        "estimateDelivery": estimated_delivery,
        "productName": product_name,
        "quantityOrdered": qty,
        "unitPrice": unit_price,
        "totalCost": total_cost,
        "status": "Pending",
        "receivedQuantity": 0,
        "outstandingQuantity": qty
    })

    update_inventory_for_order(product_name, qty)
    add_notification(f"New Order Received {po_number}", f"Order: {qty}[{product_name}] for {total_cost}", "success")

    print("\n✅ Purchase Order Created Successfully!")
    print(f"PO Number : {po_number}")
    print(f"Order Date: {order_date}")
    print(f"Est Delivery: {estimated_delivery}")
    print(f"Product   : {product_name}")
    print(f"Quantity  : {qty}")
    print(f"Unit Price: {unit_price}")
    print(f"Total Cost: {total_cost}")