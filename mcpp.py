from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import json
from datetime import datetime
import uvicorn

app = FastAPI(title="Restaurant MCP Server")

# Database setup
def init_db():
    conn = sqlite3.connect('restaurant.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            reservation_date TEXT NOT NULL,
            reservation_time TEXT NOT NULL,
            party_size INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Data Models
class ReservationRequest(BaseModel):
    customer_name: str
    phone_number: str
    reservation_date: str
    reservation_time: str
    party_size: int

class AvailabilityCheck(BaseModel):
    date: str
    time: str
    party_size: int

# MCP Tools Endpoint
@app.get("/mcp/tools")
async def get_tools():
    """MCP Tools Discovery Endpoint"""
    tools = [
        {
            "name": "check_availability",
            "description": "Check if tables are available for a given date, time and party size",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Reservation date (YYYY-MM-DD)"},
                    "time": {"type": "string", "description": "Reservation time (HH:MM)"},
                    "party_size": {"type": "integer", "description": "Number of people"}
                },
                "required": ["date", "time", "party_size"]
            }
        },
        {
            "name": "make_reservation",
            "description": "Create a new restaurant reservation",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Customer's full name"},
                    "phone_number": {"type": "string", "description": "Customer's phone number"},
                    "reservation_date": {"type": "string", "description": "Reservation date (YYYY-MM-DD)"},
                    "reservation_time": {"type": "string", "description": "Reservation time (HH:MM)"},
                    "party_size": {"type": "integer", "description": "Number of people"}
                },
                "required": ["customer_name", "phone_number", "reservation_date", "reservation_time", "party_size"]
            }
        },
        {
            "name": "get_menu",
            "description": "Get today's menu specials",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    ]
    return {"tools": tools}

# MCP Tool Execution Endpoint
@app.post("/mcp/tools/{tool_name}")
async def execute_tool(tool_name: str, parameters: dict):
    """Execute MCP Tools"""
    
    if tool_name == "check_availability":
        return await check_availability(parameters)
    
    elif tool_name == "make_reservation":
        return await make_reservation(parameters)
    
    elif tool_name == "get_menu":
        return await get_menu_specials()
    
    else:
        raise HTTPException(status_code=404, detail="Tool not found")

# Tool Implementations
async def check_availability(params: dict):
    """Check table availability"""
    date = params.get("date")
    time = params.get("time")
    party_size = params.get("party_size")
    
    # Simple availability logic (in real app, check against existing reservations)
    # For demo, assume we have tables for up to 8 people at any time
    if party_size <= 8:
        return {
            "available": True,
            "message": f"Table for {party_size} is available on {date} at {time}",
            "suggested_times": [f"{int(time.split(':')[0])+1}:00", f"{int(time.split(':')[0])-1}:00"]
        }
    else:
        return {
            "available": False,
            "message": f"Sorry, we cannot accommodate parties larger than 8 people",
            "suggested_times": []
        }

async def make_reservation(params: dict):
    """Create a reservation"""
    conn = sqlite3.connect('restaurant.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO reservations (customer_name, phone_number, reservation_date, reservation_time, party_size)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            params["customer_name"],
            params["phone_number"],
            params["reservation_date"],
            params["reservation_time"],
            params["party_size"]
        ))
        
        reservation_id = cursor.lastrowid
        conn.commit()
        
        return {
            "success": True,
            "reservation_id": reservation_id,
            "message": f"Reservation confirmed for {params['customer_name']} on {params['reservation_date']} at {params['reservation_time']} for {params['party_size']} people"
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to create reservation: {str(e)}"
        }
    
    finally:
        conn.close()

async def get_menu_specials():
    """Get today's menu specials"""
    menu = {
        "specials": [
            {"item": "Grilled Salmon", "price": "$24.99", "description": "Fresh salmon with lemon butter sauce"},
            {"item": "Mushroom Risotto", "price": "$18.99", "description": "Creamy arborio rice with wild mushrooms"},
            {"item": "Tiramisu", "price": "$8.99", "description": "Classic Italian dessert"}
        ]
    }
    return menu

# Dynamic Webhook Variables Example
@app.post("/webhook/customer-info")
async def update_customer_info(customer_data: dict):
    """Update customer information for dynamic variables"""
    # Store in session or database
    return {"status": "updated", "customer_name": customer_data.get("name")}

@app.get("/")
async def root():
    return {"message": "Restaurant MCP Server is running!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
