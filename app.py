from flask import Flask, render_template, request, redirect, url_for, session, Response, jsonify, flash, stream_with_context
from pymongo import MongoClient
from datetime import datetime, timedelta
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
purchasedOrders = db.purchasedOrders

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

# COMPUTE TOTAL COST PER UNIT FOR PRODUCT
# SUMS (QTYPERUNIT * ITEM COSTPERUNIT) FOR ALL BOM ITEMS 
def update_product_cost(productName):
    bom_items = list(BOM_Entries.find({"productName": productName}))
    total_cost = 0

    for item in bom_items:
        qty = float(item.get("qtyPerUnit", 0))
        # GET CURRENT INVENTORY COST
        inventory_item = Inventory_Entries.find_one({"itemName": item["itemName"]})
        item_cost = float(inventory_item.get("costPerUnit", 0)) if inventory_item else 0
        total_cost += qty * item_cost

    # UPDATE ALL BOM ENTRIES FOR THIS PRODUCT
    BOM_Entries.update_many(
        {"productName": productName},
        {"$set": {"costPerUnit": total_cost}}
    )

    # STORE PRODUCT COST IN COLLECTION
    productCount.update_one(
        {"name": productName},
        {"$set": {"costPerUnit": total_cost}},
        upsert=True
    )

    return total_cost

# COMPUTE TOTAL PRODUCT COST FROM ALL BOM ITEMS
# [qtyPerUnit * inventory costPerUnit]
# UPDATES EVERY BOM ENTRY FOR THAT PRODUCT WITH TOTAL
def update_bom_total_cost(productName):
    bom_items = list(BOM_Entries.find({"productName": productName}))
    total_cost = 0

    for item in bom_items:
        qty = float(item.get("qtyPerUnit", 0))
        inventory_item = Inventory_Entries.find_one({"itemName": item["itemName"]})
        item_cost = float(inventory_item.get("costPerUnit", 0)) if inventory_item else 0
        total_cost += qty * item_cost

    # Update all BOM entries for this product with the total cost
    BOM_Entries.update_many(
        {"productName": productName},
        {"$set": {"costPerUnit": total_cost}}
    )

    # Optional: also store in productCount collection if needed
    productCount.update_one(
        {"name": productName},
        {"$set": {"costPerUnit": total_cost}},
        upsert=True
    )

    return total_cost

# COMPUTE THE LEAD TIME OF A PRODUCT, AS THE MAX LEAD TIME of all BOM ITEMS
def update_product_lead_time(productName):
    bom_items = list(BOM_Entries.find({"productName": productName}))
    
    max_lead_time = 0
    for item in bom_items:
        inventory_item = Inventory_Entries.find_one({"itemName": item["itemName"]})
        if inventory_item:
            item_lead = float(inventory_item.get("leadTime", 0))
            max_lead_time = max(max_lead_time, item_lead)

    # Update all BOM entries for this product
    BOM_Entries.update_many(
        {"productName": productName},
        {"$set": {"leadTime": max_lead_time}}
    )

    # Optionally update productCount collection too
    productCount.update_one(
        {"name": productName},
        {"$set": {"leadTime": max_lead_time}},
        upsert=True
    )

    return max_lead_time

# NUMBER VALIDATION:
def validate_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def validate_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
    
def check_stock_notifications(item_name, current_stock, reorder_level):
    """
    Sends low stock or reorder reminder notifications,
    but avoids duplicates for the same item and alert type.
    """
    # Determine alert type
    if current_stock < reorder_level:
        notif_type = "error"
        title = f"Low Stock Alert: {item_name}"
        message = f"Current Stock: {current_stock}, Below minimum threshold of {reorder_level}"
    elif current_stock <= reorder_level * 1.2:  # approaching threshold
        notif_type = "warning"
        title = f"Reorder Reminder: {item_name}"
        message = f"Current Stock: {current_stock} (approaching minimum threshold of {reorder_level})"
    else:
        # Stock is sufficient, remove any previous low-stock notifications for this item
        notifications.delete_many({
            "itemName": item_name,
            "type": {"$in": ["error", "warning"]}
        })
        return

    # Check if a notification of the same type already exists
    exists = notifications.find_one({
        "itemName": item_name,
        "type": notif_type,
        "message": message
    })

    if not exists:
        add_notification(title, message, notif_type)
        # Store the item name in the notification for easier tracking
        notifications.update_one(
            {"_id": notifications.find().sort("_id", -1).limit(1)[0]["_id"]},
            {"$set": {"itemName": item_name}}
        )

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
    
    # FETCH ALL PURCHASED ORDERS
    all_orders = list(purchasedOrders.find().sort("orderDate", -1))

    # DATA FOR TOP BOXES
    today = datetime.now().date()
    end_of_week = today + timedelta(days=6)

    today_orders = [
        o for o in all_orders
        if datetime.strptime(o.get("orderDate", ""), "%Y-%m-%d").date() == today
    ]
    today_count = len(today_orders)
    today_total_qty = sum(float(o.get("quantityOrdered", 0)) for o in today_orders)

    # This Week
    week_orders = [
        o for o in all_orders
        if today <= datetime.strptime(o.get("orderDate", ""), "%Y-%m-%d").date() <= end_of_week
    ]
    week_count = len(week_orders)
    week_total_qty = sum(float(o.get("quantityOrdered", 0)) for o in week_orders)

    produced_orders = [
    o for o in all_orders if float(o.get("receivedQuantity", 0)) > 0 and o.get("status", "").lower() != "cancelled"
    ]
    total_units_produced = sum(float(o.get("receivedQuantity", 0)) for o in produced_orders)

    # COMPUTE COUNT
    open_count = sum(1 for order in all_orders if order.get("status", "").lower() != "cancelled")
    completed_count = sum(1 for order in all_orders if order.get("status", "").lower() == "completed")
    in_progress_count = sum(1 for order in all_orders if order.get("status", "").lower() == "processing")
    cancelled_count = sum(1 for order in all_orders if order.get("status", "").lower() == "cancelled")

    # FETCH 3 LATEST NOTIFICATIONS
    recent_notifications_docs = list(notifications.find().sort("timestamp", -1).limit(3))
    recent_notifications = [f"{n['title']}: {n['message']}" for n in recent_notifications_docs]

    return render_template(
        'Dashboard.html',
        open_count=open_count,
        completed_count=completed_count,
        in_progress_count=in_progress_count,
        cancelled_count=cancelled_count,
        recent_notifications=recent_notifications,
        purchased_orders=all_orders,
        # top boxes data
        today_count=today_count,
        today_total_qty=today_total_qty,
        week_count=week_count,
        week_total_qty=week_total_qty,
        total_units_produced=total_units_produced
    )

@app.route('/admin')
def admin():
    if session.get('role') != 'admin':
        return redirect(url_for('signin'))
    return render_template('admin.html')

# PRODUCTION
@app.route('/Production')
def production():
    if 'user' not in session:
        return redirect(url_for('signin'))
    
    # GET ALL INVENTORY ITEMS BELOW THEIR REORDER LEVEL
    low_stock_items = list(Inventory_Entries.find({
        "$expr": {"$lt": ["$currentStock", "$reorderLevel"]} # ALLOWS COMPARING TWO FIELDS
    }))
    
    return render_template('Production.html', items=low_stock_items)

@app.route("/place-order", methods=["POST"])
def place_order():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        data = request.get_json()
        item_id = data.get("_id")

        if not item_id:
            return jsonify({"success": False, "message": "Missing item ID"}), 400

        # FIND THE ITEM
        item = Inventory_Entries.find_one({"_id": ObjectId(item_id)})
        if not item:
            return jsonify({"success": False, "message": "Item not found"}), 404

        # ADD THE REORDERED QUANTITY TO CURRENT STOCK
        reorder_qty = validate_int(item.get("reorderQty", 0))
        new_stock = validate_int(item.get("currentStock", 0)) + reorder_qty

        Inventory_Entries.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {"currentStock": new_stock}}
        )

        # ADD NOTIFICATION
        add_notification(
            "Order Placed",
            f"{reorder_qty} units added to {item['itemName']} stock",
            "success"
        )

        return jsonify({"success": True, "newStock": new_stock})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# PURCHASED
@app.route('/Purchased')
def purchased_page():
    if 'user' not in session:
        return redirect(url_for('signin'))
    
    purchased_entries = list(purchasedOrders.find().sort("orderDate", -1))
    
    for entry in purchased_entries:
        product_name = entry.get("productName")
        quantity_ordered = float(entry.get("quantityOrdered", 0))
        order_date_str = entry.get("orderDate")

        # GETS ORDER DATE AS DATETIME
        try:
            order_date = datetime.strptime(order_date_str, "%Y-%m-%d")
        except:
            order_date = datetime.now()

        # GET LEAD TIME FROM PRODUCT COLLECTION
        product = productCount.find_one({"name": product_name})
        lead_time = float(product.get("leadTime", 0)) if product else 0

        # CALCULATE EST DELIVERY
        est_days = lead_time * quantity_ordered / 2
        est_delivery_date = order_date + timedelta(days=est_days)

        #  FORMAT AS STRING
        est_delivery_str = est_delivery_date.strftime("%Y-%m-%d")

        # UPDATE ENTRY IN DB
        purchasedOrders.update_one(
            {"_id": entry["_id"]},
            {"$set": {"estimatedDelivery": est_delivery_str}}
        )

        # UPDATE LOCAL COPY FOR RENDERING
        entry["estimatedDelivery"] = est_delivery_str

    
    return render_template(
        "Purchased.html",
        entries=purchased_entries,
        has_data=len(purchased_entries) > 0
    )

@app.route("/update-purchased", methods=["POST"])
def update_purchased():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json()
    order_id = data.get("_id")
    received_qty = validate_int(data.get("receivedQuantity", 0))
    status = data.get("status", "Pending")

    if not order_id:
        return jsonify({"success": False, "message": "Missing order ID"}), 400

    order = purchasedOrders.find_one({"_id": ObjectId(order_id)})
    if not order:
        return jsonify({"success": False, "message": "Order not found"}), 404
    
    quantity_ordered = validate_int(order.get("quantityOrdered", 0))
    outstanding_qty = max(quantity_ordered - received_qty, 0)

    if status != "Cancelled":
        if received_qty >= quantity_ordered:
            status = "Completed"
        elif 0 < received_qty < quantity_ordered:
            status = "Processing"  # optionally "Pending" if you prefer
        else:
            status = "Pending"

    result = purchasedOrders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {
            "receivedQuantity": received_qty,
            "status": status,
            "outstandingQuantity": outstanding_qty
        }}
    )

    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Order not found"}), 404

    return jsonify({
        "success": True,
        "receivedQuantity": received_qty,
        "status": status,
        "outstandingQuantity": outstanding_qty
    })

@app.route('/get_bom_items/<productName>')
def get_bom_items(productName):
    bom_entries = list(BOM_Entries.find({"productName": productName}))
    results = []

    for entry in bom_entries:
        itemName = entry.get("itemName", "")
        inventory_item = Inventory_Entries.find_one({"itemName": itemName})

        if inventory_item:
            qtyPerUnit = float(entry.get("qtyPerUnit", 0))  # BOM-specific qty
            pricePerUnit = float(inventory_item.get("costPerUnit", 0))
        else:
            qtyPerUnit = 0
            pricePerUnit = 0

        results.append({
            "itemName": itemName,
            "qtyPerUnit": qtyPerUnit,
            "pricePerUnit": pricePerUnit
        })

    return jsonify(results)

# INVENTORY 
@app.route('/Inventory', methods=["GET", "POST"])
def inventory_page():
    if 'user' not in session:
        return redirect(url_for('signin'))

    if request.method == "POST":
        itemName = request.form.get("itemName")
        itemCode = generate_part_id(itemName)
        category = request.form.get("category")
        uom = request.form.get("uom")
        
        currentStock = validate_int(request.form.get("currentStock") or 0)
        reorderLvl = validate_int(request.form.get("reorderLevel") or 0)
        reorderQty = validate_int(request.form.get("reorderQty") or 0)
        costPerUnit = validate_float(request.form.get("costPerUnit") or 0)
        
        totalValue = calculate_total_value(currentStock, costPerUnit)
        supplier = request.form.get("supplier")
        
        leadTime = validate_int(request.form.get("leadTime") or 0)

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

        check_stock_notifications(itemName, currentStock, reorderLvl)

        add_notification("NEW Item Created", f"{itemName}[{itemCode}]", "success")
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
        current_stock = validate_float(data.get("currentStock"))
        cost_per_unit = validate_float(data.get("costPerUnit"))
        total_value = calculate_total_value(current_stock, cost_per_unit)


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

        check_stock_notifications(item_name, current_stock, validate_int(data.get("reorderLevel")))

        update_bom_total_cost(item_name)
        affected_products = BOM_Entries.find({"itemName": item_name})
        for prod in affected_products:
            update_product_lead_time(prod["productName"])

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

    inventory_entries = list(Inventory_Entries.find({}, projection))

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

@app.route('/activity')
def activity():
    if 'user' not in session:
        return redirect(url_for('signin'))
    logs = list(notifications.find().sort("_id", -1))
    return render_template('activity.html', logs=logs)

from flask import stream_with_context
from bson import ObjectId

@app.route('/stream')
def stream():
    @stream_with_context
    def event_stream():
        last_id = None
        while True:
            try:
                time.sleep(2)  # CHECK EVERY 2 SECONDS
                query = {}
                if last_id:
                    query = {"_id": {"$gt": ObjectId(last_id)}}

                new_logs = list(notifications.find(query).sort("_id", 1))
                if new_logs:
                    for log in new_logs:
                        # SHALLOW COPY: NORMALIZE FIELDS THAT CAN BREAK RENDER
                        safe_log = dict(log)
                        # CONVERT OBJECTID AND TIMESTAMP TO STRINGS
                        try:
                            safe_log["_id"] = str(safe_log.get("_id"))
                        except Exception:
                            safe_log["_id"] = str(safe_log.get("_id", ""))
                        # STRINGY IF TIMESTAMP IS DATETIME OR OTHER
                        ts = safe_log.get("timestamp")
                        if ts is not None:
                            try:
                                safe_log["timestamp"] = str(ts)
                            except Exception:
                                safe_log["timestamp"] = ts

                        # RENDER NOTIFICATION TEMPLATE
                        html = render_template('_single_notification.html', log=safe_log)
                        yield f"data: {json.dumps({'html': html})}\n\n"
                        last_id = str(log["_id"])
            except Exception as e:
                print("Error in event_stream:", repr(e))
                # YIELD A MINIMAL NON-BREAKING EVENT SO CLIENT'S EVENTSOURCE CONTINUES
                fallback_html = f"<div class='notification error'>Notification render error: {str(e)}</div>"
                yield f"data: {json.dumps({'html': fallback_html})}\n\n"
                # SMALL SLEEP TO AVOID TIGHT EXCEPTION LOOP
                time.sleep(2)

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
        qtyPerUnit = validate_float(request.form.get("qtyPerUnit"))
        if qtyPerUnit <= 0:
            return jsonify({"success": False, "message": "Quantity per unit must be positive."})

        uom = request.form.get("uom")
        supplier = request.form.get("supplier")

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
            "leadTime": 0,
            "costPerUnit": 0 # TEMPORARY
        })

        total_product_cost = update_bom_total_cost(productName)
        product_lead_time = update_product_lead_time(productName)

        add_notification("BOM Updated", f"{productName} Total Cost/Unit Updated to ${total_product_cost:.2f} and Lead Time set to {product_lead_time} days", "success")
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
        imported_products = set() # TO TRACK WHICH PRODUCTS TO UPDATE TOTALS/LEAD TIME

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
                "qtyPerUnit": validate_float(row.get("QTY PER UNIT", 0)),
                "uom": row.get("UOM", "").strip(),
                "supplier": row.get("SUPPLIER", "").strip(),
                "leadTime": validate_float(row.get("LEAD TIME", 0)),
                "costPerUnit": validate_float(row.get("COST/UNIT", 0))
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
            imported_products.add(productName) # TRACK PRODUCTS FOR UPDATE

        # AFTER IMPORT, UPDATE TOTAL COST AND LEAD TIME FOR IMPORTED PRODUCTS
        for product_name in imported_products:
            total_cost = update_bom_total_cost(product_name)
            lead_time = update_product_lead_time(product_name)
            add_notification(
                "BOM Updated via Import",
                f"{product_name} Total Cost/Unit set to {total_cost:.2f}, Lead Time set to {lead_time} days",
                "success"
            )

        message = f"Imported {imported_count} items"
        if duplicate_logs:
            message += "\n" + "\n".join(duplicate_logs)

        add_notification("Import BOM", message, "info")

        return jsonify({"message": message})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)