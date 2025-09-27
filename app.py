from flask import Flask, render_template, request, redirect, url_for, session, Response, jsonify, flash
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import csv
import time
import json
import io

app = Flask(__name__)
app.secret_key = "arandomasssecretkeydapatto"

UPLOADER_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOADER_FOLDER

client = MongoClient("mongodb+srv://Fooxo:2025174371@mrp-database.qopzsma.mongodb.net/")
db = client.MRP_Database

BOM_Entries = db.bom_entry
Inventory_Entries = db.inventory
productCount = db.product
notifications = db.notifications
user_notifications = db.user_notifications

def add_notification(title, message, type="info"):
    notifications.insert_one({
        "type": type,
        "title": title,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

def calculate_total_value(current_stock, cost_per_unit):
    try:
        # Convert inputs to float in case they are strings
        stock = float(current_stock)
        cost = float(cost_per_unit)
        return stock * cost
    except (ValueError, TypeError):
        return 0

def generate_product_code(productName):
    # CHECK IF PRODUCT ALREADY EXISTING (CASE INSENSITIVE)
    existing = productCount.find_one({"name": {"$regex": f"^{productName}$", "$options": "i"}})
    if existing:
        return existing["code"]
    
    #DESCRIPTION, SEPARATED BY COMMA
    parts = productName.split(", ")
    first_word = parts[0].strip()
    code_prefix = first_word[:2].upper()

    # GET HIGHEST COUNTER FROM EXISTING CODE WITH SAME PREFIX
    last_product = productCount.find({"code": {"$regex": f"^{code_prefix}-"}}).sort("code", -1).limit(1)
    try:
        last_code = list(last_product)[0]["code"]
        last_number = int(last_code.split("-")[1])
        number = last_number + 1
    except IndexError:
        number = 1

    number_str = f"{number:03d}"
    
    # Suffix from first and last letter of second word (if exists)
    suffix = ""
    if len(parts) > 1:
        second_word = parts[1].strip()
        if len(second_word) >= 2:
            suffix = "-" + second_word[0].upper() + second_word[-1].upper()
        elif len(second_word) == 1:
            suffix = "-" + second_word[0].upper()
    
    code = f"{code_prefix}-{number}{suffix}"
    
    productCount.insert_one({"name": productName, "code": code})
    
    return code

def generate_part_id(item_name):
    """Generate item code based on first letters of first two words and sequence."""
    words = item_name.strip().split()
    prefix = ""
    if len(words) >= 2:
        prefix = words[0][0].upper() + words[1][0].upper()
    elif len(words) == 1:
        prefix = words[0][:2].upper()
    else:
        prefix = "XX"

    # Count items already in DB to assign sequence number
    count = BOM_Entries.count_documents({})
    sequence = count + 1
    return f"{prefix}-{sequence:03d}"

def reindex_part_numbers():
    """Reassign part numbers sequentially after deletions."""
    entries = list(BOM_Entries.find().sort("_id", 1))
    for idx, entry in enumerate(entries):
        item_name = entry.get("itemName", "")
        words = item_name.strip().split()
        if len(words) >= 2:
            prefix = words[0][0].upper() + words[1][0].upper()
        elif len(words) == 1:
            prefix = words[0][:2].upper()
        else:
            prefix = "XX"
        new_code = f"{prefix}-{idx+1:03d}"
        BOM_Entries.update_one({"_id": entry["_id"]}, {"$set": {"itemCode": new_code}})

# REDIRECT TO LOGIN BY DEFAULT:
@app.route('/')
def home():
    return redirect(url_for('signin'))

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == "admin" and password == "1234":
            session['user'] = username
            session['role'] = 'admin'
            return redirect(url_for('Dashboard'))
        elif username == "employee" and password == "5678":
            session['user'] = username
            session['role'] = 'employee'
            return redirect(url_for('Dashboard'))
        else:
            return render_template('signin.html', error="Invalid credentials")
    return render_template('signin.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('signin'))

@app.route('/Dashboard')
def Dashboard():
    if 'user' not in session:
        return redirect(url_for('signin'))
    return render_template('Dashboard.html')

@app.route('/admin')
def admin():
    if session.get('role') != 'admin':
        return redirect(url_for('signin'))
    return render_template('admin.html')

@app.route('/Production')
def production():
    if 'user' not in session:
        return redirect(url_for('signin'))
    return render_template('Production.html')

@app.route('/Purchased')
def purchased():
    if 'user' not in session:
        return redirect(url_for('signin'))
    return render_template('Purchased.html')

# INVENTORY 
@app.route('/Inventory', methods=["GET", "POST"])
def Inventory():
    if 'user' not in session:
        return redirect(url_for('signin'))

    if request.method == "POST":
        itemName = request.form.get("itemName")
        itemCode = generate_part_id(itemName)
        category = request.form.get("category")
        uom = request.form.get("uom")
        currentStock = int(request.form.get("currentStock") or 0)
        reorderLvl = int(request.form.get("reorderLevel") or 0)
        reorderQty = int(request.form.get("reorderQty") or 0)
        costPerUnit = int(request.form.get("costPerUnit") or 0)
        totalValue = calculate_total_value(currentStock, costPerUnit)
        supplier = request.form.get("supplier")
        leadTime = int(request.form.get("leadTime") or 0)

        #put into mongoDB
        Inventory_Entries.insert_one({
            "itemName": itemName,
            "itemCode": itemCode,
            "category": category,
            "uom": uom,
            "currentStock": currentStock,
            "reorderLevel": reorderLvl,
            "reorderQty": reorderQty,
            "costPerUnit": costPerUnit,
            "totalValue": totalValue,
            "supplier": supplier,
            "leadTime": leadTime,
        })

        add_notification("New Item Created!", f"{itemName}[{itemCode}]", "success")
        return redirect(url_for("Inventory"))
    
    inventory_entries = list(Inventory_Entries.find().sort("itemCode", 1))
    return render_template(
        "Inventory.html",
        entries=inventory_entries,
        has_data=Inventory_Entries.count_documents({}) > 0
    )

@app.route("/update-inventory", methods=["POST"])
def update_inventory():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        item_id = data.get("_id")

        if not item_id:
            return jsonify({"success": False, "message": "_id missing"}), 400
        
        item_name = data.get("name")
        new_item_code = generate_part_id(item_name)
        total_value = calculate_total_value(data.get("currentStock"), data.get("costPerUnit"))

        result = Inventory_Entries.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {
                "itemName": item_name,
                "itemCode": new_item_code,  # regenerate based on name
                "category": data.get("category"),
                "uom": data.get("uom"),
                "currentStock": data.get("currentStock"),
                "reorderLevel": data.get("reorderLevel"),
                "reorderQty": data.get("reorderQty"),
                "costPerUnit": data.get("costPerUnit"),
                "totalValue": total_value,
                "supplier": data.get("supplier"),
                "leadTime": data.get("leadTime")
            }}
        )

        if result.matched_count == 0:
            return jsonify({"success": False, "message": "Item not found"}), 404

        # Optionally: log a notification
        add_notification("Inventory Updated", f"{item_name} [{new_item_code}] was updated", "success")
        return jsonify({"success": True, "itemCode": new_item_code})
    
    except Exception as e:
        print("Error updating inventory:", e)
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/delete-inventory", methods=["POST"])
def delete_inventory():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        data = request.get_json()
        item_id = data.get("_id")

        if not item_id:
            return jsonify({"success": False, "message": "_id missing"}), 400

        result = Inventory_Entries.delete_one({"_id": ObjectId(item_id)})

        if result.deleted_count == 0:
            return jsonify({"success": False, "message": "Item not found"}), 404

        add_notification("Inventory Deleted", f"Item with ID {item_id} was deleted", "warning")
        return jsonify({"success": True})
    
    except Exception as e:
        print("Error deleting inventory:", e)
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/item-analytics/<item_code>")
def item_analytics(item_code):
    # Query BOM_Entries where itemCode matches
    usage_entries = list(BOM_Entries.find({"itemCode": item_code}, {"_id": 0, "productName": 1, "qtyPerUnit": 1, "uom": 1}))
    
    # Return JSON
    return jsonify(usage_entries)

@app.route("/export_csv_inv", methods=["POST"])
def export_csv_inv():
    # Columns to export (match your HTML)
    selected_columns = [
        "ITEM CODE", "ITEM NAME", "CATEGORY", "UOM", "CURRENT STOCK",
        "REORDER LEVEL", "REORDER QTY", "COST/UNIT", "TOTAL VALUE", "SUPPLIER", "LEAD TIME"
    ]

    # Map display names to MongoDB field names
    column_map = {
        "ITEM CODE": "itemCode",
        "ITEM NAME": "itemName",
        "CATEGORY": "category",
        "UOM": "uom",
        "CURRENT STOCK": "currentStock",
        "REORDER LEVEL": "reorderLevel",
        "REORDER QTY": "reorderQty",
        "COST/UNIT": "costPerUnit",
        "TOTAL VALUE": "totalValue",
        "SUPPLIER": "supplier",
        "LEAD TIME": "leadTime"
    }

    # Projection for MongoDB query
    projection = {v: 1 for v in column_map.values()}
    projection["_id"] = 0

    inventory_entries = list(Inventory.find({}, projection))

    # Create CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=selected_columns)
    writer.writeheader()

    for entry in inventory_entries:
        row = {col: entry.get(column_map[col], "") for col in selected_columns}
        writer.writerow(row)

    # Generate file name with current date
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"inventory_export_{date_str}.csv"

    # Return CSV response
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

# NOTIFICATION / ACTIVITY LOG SECTION
@app.route('/activity')
def activity():
    if 'user' not in session:
        return redirect(url_for('signin'))
    logs = list(notifications.find().sort("_id", -1))
    return render_template('activity.html', logs=logs)

@app.route('/stream')
def stream():
    def event_stream():
        last_id = None
        while True:
            time.sleep(2)  # check every 2s (can be tuned down)
            
            query = {}
            if last_id:
                query = {"_id": {"$gt": ObjectId(last_id)}}
            
            new_logs = list(notifications.find(query).sort("_id", 1))  # oldest first
            if new_logs:
                for log in new_logs:
                    html = render_template('_single_notification.html', log=log)
                    yield f"data: {json.dumps({'html': html})}\n\n"
                    last_id = str(log["_id"])
    return Response(event_stream(), mimetype="text/event-stream")

# BOM SECTION
@app.route("/BOM", methods=["GET", "POST"])
def bom():
    if 'user' not in session:
        return redirect(url_for('signin'))

    if request.method == "POST":
        productName = request.form.get("productName")
        itemName = request.form.get("itemName")

        # CHECK IF ITEM EXISTS IN INVENTORY:
        inventory_item = Inventory_Entries.find_one({"itemName": {"$regex": f"^{itemName}$", "$options": "i"}})
        if not inventory_item:
            return jsonify({"success": False, "message": f"Item '{itemName}' does not exist in inventory."})
        
        # IF IT EXISTS THEN CONTINUE
        productCode = generate_product_code(productName)
        bomLevel = request.form.get("bomLevel")
        itemCode = inventory_item["itemCode"] # USES THE ITEM CODE MADE IN INVENTORY
        qtyPerUnit = request.form.get("qtyPerUnit")
        uom = request.form.get("uom")
        supplier = request.form.get("supplier")
        leadTime = request.form.get("leadTime")
        costPerUnit = request.form.get("costPerUnit")

        #put into mongoDB
        BOM_Entries.insert_one({
            "productCode": productCode,
            "productName": productName,
            "bomLevel": bomLevel,
            "itemCode": itemCode,
            "itemName": itemName,
            "qtyPerUnit": qtyPerUnit,
            "uom": uom,
            "supplier": supplier,
            "leadTime": leadTime,
            "costPerUnit": costPerUnit
        })

        add_notification("New Item Created!", f"{itemName}[{itemCode}] | {productName}[{productCode}]", "success")
        return jsonify({"success": True, "message": "BOM Item Added Successfully!"})
    
    bom_entry = list(BOM_Entries.find().sort("number", 1))
    return render_template("BOM.html", entries=bom_entry, has_data=BOM_Entries.count_documents({}) > 0)

@app.route("/export_csv", methods=["POST"])
def export_csv():
    selected_columns = [
        "PRODUCT CODE", "PRODUCT NAME", "BOM LEVEL", "ITEM CODE", 
        "ITEM NAME", "QTY PER UNIT", "UOM", "SUPPLIER", "LEAD TIME", "COST/UNIT"
    ]

    column_map = {
        "PRODUCT CODE": "productCode",
        "PRODUCT NAME": "productName",
        "BOM LEVEL": "bomLevel",
        "ITEM CODE": "itemCode",
        "ITEM NAME": "itemName",
        "QTY PER UNIT": "qtyPerUnit",
        "UOM": "uom",
        "SUPPLIER": "supplier",
        "LEAD TIME": "leadTime",
        "COST/UNIT": "costPerUnit"
    }

    # Projection for MongoDB query
    projection = {v: 1 for v in column_map.values()}
    projection["_id"] = 0

    bom_entries = list(BOM_Entries.find({}, projection))

    # MAKE THE CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=selected_columns)
    writer.writeheader()

    for entry in bom_entries:
        row = {}
        for col in selected_columns:
            mongo_field = column_map[col]
            row[col] = entry.get(mongo_field, "")
        writer.writerow(row)

    # GENERATE FILE NAME WITH CURRENT DATE
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"bom_export_{date_str}.csv"

    # RETURN THE CSV RESPONSE
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

@app.route("/import_csv", methods=["POST"])
def import_csv():
    file = request.files.get("file")
    action = request.form.get("action")  # KEEP or DELETE from modal

    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        # DELETE ACTION : CLEAR EXISTING DATA FIRST
        if action and action.lower() == "delete":
            BOM_Entries.delete_many({})

        # READ CSV
        stream = io.StringIO(file.stream.read().decode("UTF-8"))
        csv_reader = csv.DictReader(stream)

        imported_count = 0
        duplicate_logs = []
        seen = set()

        header_map = {
            "PRODUCT CODE": "productCode",
            "PRODUCT NAME": "productName",
            "BOM LEVEL": "bomLevel",
            "ITEM CODE": "itemCode",
            "ITEM NAME": "itemName",
            "QTY PER UNIT": "qtyPerUnit",
            "UOM": "uom",
            "SUPPLIER": "supplier",
            "LEAD TIME": "leadTime",
            "COST/UNIT": "costPerUnit"
        }

        for row in csv_reader:
            # GET PRODUCT NAME AND ITEM NAME
            productName = row.get("PRODUCT NAME", "").strip()
            if not productName:
                continue  # SKIP ROWS WITHOUT PRODUCT NAME

            itemName = row.get("ITEM NAME", "").strip()
            if not itemName:
                continue  # SKIP ROWS WITHOUT ITEM NAME

            # GENERATE PRODUCT CODE AND ITEM CODE
            productCode = row.get("PRODUCT CODE", "").strip()
            if not productCode:
                productCode = generate_product_code(productName)

            itemCode = row.get("ITEM CODE", "").strip()
            if not itemCode:
                itemCode = generate_part_id(itemName)

            doc = {
                "productCode": productCode,
                "productName": productName,
                "bomLevel": row.get("BOM LEVEL", "").strip(),
                "itemCode": itemCode,
                "itemName": itemName,
                "qtyPerUnit": float(row.get("QTY PER UNIT", 0) or 0),
                "uom": row.get("UOM", "").strip(),
                "supplier": row.get("SUPPLIER", "").strip(),
                "leadTime": float(row.get("LEAD TIME", 0) or 0),
                "costPerUnit": float(row.get("COST/UNIT", 0) or 0)
            }

            key = (doc["productCode"], doc["itemCode"])
            if key in seen:
                continue
            seen.add(key)
            
            if BOM_Entries.find_one({"productCode": doc["productCode"], "itemCode": doc["itemCode"]}):
                duplicate_logs.append(f"Skipped exact duplicate: {itemName}")
                continue

            BOM_Entries.insert_one(doc)
            imported_count += 1

        message = f"Imported {imported_count} items"
        if duplicate_logs:
            message += "\n" + "\n".join(duplicate_logs)

        add_notification("Import BOM", message, "info")

        return jsonify({"message": message})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)