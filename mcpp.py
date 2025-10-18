from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sqlite3
import json
from datetime import datetime

app = FastAPI(title="Wellness Center MCP Server - Telnyx Integration")

# 🔥 CRITICAL: Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
def init_db():
    conn = sqlite3.connect('wellness.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            appointment_type TEXT NOT NULL,
            provider TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Data Models
class TelnyxWebhookRequest(BaseModel):
    call_session_id: Optional[str] = None
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    user_input: Optional[str] = None
    dynamic_variables: Optional[Dict[str, Any]] = None

# MCP Tools Discovery
@app.get("/mcp/tools")
async def get_tools():
    tools = {
        "tools": [
            {
                "name": "check_availability",
                "description": "Check available appointment slots",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Appointment date (YYYY-MM-DD)"},
                        "time": {"type": "string", "description": "Appointment time (HH:MM)"},
                        "provider": {"type": "string", "description": "Healthcare provider"},
                        "appointment_type": {"type": "string", "description": "Type of appointment"}
                    },
                    "required": ["date", "time", "provider", "appointment_type"]
                }
            },
            {
                "name": "book_appointment",
                "description": "Schedule a new appointment",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "patient_name": {"type": "string", "description": "Patient full name"},
                        "phone_number": {"type": "string", "description": "Patient phone number"},
                        "appointment_date": {"type": "string", "description": "Appointment date (YYYY-MM-DD)"},
                        "appointment_time": {"type": "string", "description": "Appointment time (HH:MM)"},
                        "appointment_type": {"type": "string", "description": "Type of appointment"},
                        "provider": {"type": "string", "description": "Healthcare provider"}
                    },
                    "required": ["patient_name", "phone_number", "appointment_date", "appointment_time", "appointment_type", "provider"]
                }
            },
            {
                "name": "get_services",
                "description": "Get available healthcare services",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    }
    return tools

# MCP Tool Execution
@app.post("/mcp/tools/{tool_name}")
async def execute_tool(tool_name: str, request: dict):
    if tool_name == "check_availability":
        return await check_availability(request)
    elif tool_name == "book_appointment":
        return await book_appointment(request) 
    elif tool_name == "get_services":
        return await get_services()
    else:
        raise HTTPException(status_code=404, detail="Tool not found")

# Tool implementations (same as before)
async def check_availability(params: dict):
    return {
        "available": True,
        "message": f"Appointment available with {params.get('provider')} on {params.get('date')} at {params.get('time')}",
        "available_slots": ["14:00", "15:00", "16:00"]
    }

async def book_appointment(params: dict):
    conn = sqlite3.connect('wellness.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO appointments (patient_name, phone_number, appointment_date, appointment_time, appointment_type, provider)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            params["patient_name"],
            params["phone_number"],
            params["appointment_date"], 
            params["appointment_time"],
            params["appointment_type"],
            params["provider"]
        ))
        appointment_id = cursor.lastrowid
        conn.commit()
        return {
            "success": True,
            "appointment_id": appointment_id,
            "message": f"Appointment booked for {params['patient_name']} with {params['provider']} on {params['appointment_date']} at {params['appointment_time']}"
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}
    finally:
        conn.close()

async def get_services():
    return {
        "services": [
            {"type": "Primary Care", "providers": ["Dr. Smith", "Dr. Johnson"]},
            {"type": "Dermatology", "providers": ["Dr. Brown"]},
            {"type": "Physical Therapy", "providers": ["Dr. Wilson"]}
        ]
    }

# Webhook endpoint
@app.post("/telnyx/webhook")
async def telnyx_webhook(request: dict):
    return {
        "session_id": request.get("call_session_id", "test"),
        "response": "Welcome to Wellness Partners! How can I help you today?",
        "dynamic_variables": {
            "patient_name": "Guest",
            "caller_number": request.get("from_number", "")
        }
    }

# Dynamic variables
@app.post("/dynamic-variables")
async def dynamic_variables(request: dict):
    return {
        "dynamic_variables": {
            "patient_name": request.get("patient_name", "Guest"),
            "last_interaction": datetime.now().isoformat()
        }
    }

@app.get("/")
async def root():
    return {"message": "Wellness MCP Server Running", "status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
