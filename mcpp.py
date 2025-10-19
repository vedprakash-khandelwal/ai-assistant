from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sqlite3
import json
from datetime import datetime

app = FastAPI(title="Wellness Center MCP Server")

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
    return {
        "tools": [
            {
                "name": "check_availability",
                "description": "Check available appointment slots for healthcare providers",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Appointment date (YYYY-MM-DD)"},
                        "time": {"type": "string", "description": "Appointment time (HH:MM)"},
                        "provider": {"type": "string", "description": "Healthcare provider name"},
                        "appointment_type": {"type": "string", "description": "Type of appointment"}
                    },
                    "required": ["date", "time", "provider", "appointment_type"]
                }
            },
            {
                "name": "book_appointment",
                "description": "Schedule a new healthcare appointment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_name": {"type": "string", "description": "Patient's full name"},
                        "phone_number": {"type": "string", "description": "Patient's phone number"},
                        "appointment_date": {"type": "string", "description": "Appointment date (YYYY-MM-DD)"},
                        "appointment_time": {"type": "string", "description": "Appointment time (HH:MM)"},
                        "appointment_type": {"type": "string", "description": "Type of appointment"},
                        "provider": {"type": "string", "description": "Healthcare provider name"}
                    },
                    "required": ["patient_name", "phone_number", "appointment_date", "appointment_time", "appointment_type", "provider"]
                }
            },
            {
                "name": "get_services",
                "description": "Get available healthcare services and providers",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    }

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

# Tool implementations
async def check_availability(params: dict):
    date = params.get("date", "2024-01-01")
    time = params.get("time", "14:00")
    provider = params.get("provider", "Dr. Smith")
    appointment_type = params.get("appointment_type", "Primary Care")
    
    return {
        "content": [
            {
                "type": "text",
                "text": f"Available appointments with {provider} for {appointment_type} on {date} at {time}. Available times: 9:00 AM, 10:00 AM, 2:00 PM, 3:00 PM"
            }
        ]
    }

async def book_appointment(params: dict):
    conn = sqlite3.connect('wellness.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO appointments (patient_name, phone_number, appointment_date, appointment_time, appointment_type, provider, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            params.get("patient_name", "Test Patient"),
            params.get("phone_number", "+1234567890"),
            params.get("appointment_date", "2024-01-01"),
            params.get("appointment_time", "14:00"),
            params.get("appointment_type", "Primary Care"),
            params.get("provider", "Dr. Smith"),
            params.get("notes", "")
        ))
        
        appointment_id = cursor.lastrowid
        conn.commit()
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"✅ Appointment confirmed for {params.get('patient_name')} with {params.get('provider')} on {params.get('appointment_date')} at {params.get('appointment_time')}. Confirmation number: APT{appointment_id:04d}"
                }
            ]
        }
    except Exception as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"❌ Failed to book appointment: {str(e)}"
                }
            ]
        }
    finally:
        conn.close()

async def get_services():
    return {
        "content": [
            {
                "type": "text",
                "text": "🏥 **Wellness Partners Services:**\n• Primary Care: Dr. Smith, Dr. Johnson\n• Dermatology: Dr. Brown\n• Physical Therapy: Dr. Wilson\n• Mental Health: Dr. Taylor\n\n📍 Hours: Mon-Fri 8AM-5PM, Sat 9AM-12PM"
            }
        ]
    }

# Webhook endpoints
@app.post("/telnyx/webhook")
async def telnyx_webhook(request: dict):
    return {
        "session_id": request.get("call_session_id", "test"),
        "response": "Welcome to Wellness Partners! This is Erica, your scheduling assistant. How may I help you today?",
        "dynamic_variables": {
            "patient_name": "Guest",
            "caller_number": request.get("from_number", "")
        }
    }

@app.post("/dynamic-variables")
async def dynamic_variables(request: dict):
    return {
        "dynamic_variables": {
            "patient_name": request.get("patient_name", "Guest"),
            "last_interaction": datetime.now().isoformat()
        }
    }

# View appointments (for testing)
@app.get("/appointments")
async def get_appointments():
    conn = sqlite3.connect('wellness.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM appointments ORDER BY created_at DESC')
    appointments = cursor.fetchall()
    conn.close()
    
    return {
        "appointments": [
            {
                "id": apt[0],
                "patient_name": apt[1],
                "phone_number": apt[2],
                "appointment_date": apt[3],
                "appointment_time": apt[4],
                "appointment_type": apt[5],
                "provider": apt[6],
                "notes": apt[7],
                "created_at": apt[8]
            }
            for apt in appointments
        ]
    }

@app.get("/")
async def root():
    return {
        "message": "Wellness Center MCP Server is running!",
        "status": "healthy",
        "endpoints": {
            "mcp_tools": "/mcp/tools",
            "telnyx_webhook": "/telnyx/webhook",
            "dynamic_variables": "/dynamic-variables",
            "appointments": "/appointments"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
