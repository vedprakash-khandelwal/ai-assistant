from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sqlite3
import json
from datetime import datetime

app = FastAPI(title="Wellness Center MCP Server - Telnyx Integration")

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
    """Model for Telnyx webhook requests"""
    call_session_id: Optional[str] = None
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    user_input: Optional[str] = None
    dynamic_variables: Optional[Dict[str, Any]] = None

class AppointmentRequest(BaseModel):
    patient_name: str
    phone_number: str 
    appointment_date: str
    appointment_time: str
    appointment_type: str
    provider: str
    notes: Optional[str] = None

# 🔥 TELNYX WEBHOOK ENDPOINT - This is where Telnyx calls your server
@app.post("/telnyx/webhook")
async def telnyx_webhook(request: TelnyxWebhookRequest):
    """Main webhook endpoint that Telnyx AI Assistant calls"""
    
    print(f"Received call from: {request.from_number}")
    print(f"Call Session ID: {request.call_session_id}")
    
    # Extract dynamic variables from Telnyx
    dynamic_vars = request.dynamic_variables or {}
    patient_name = dynamic_vars.get("patient_name", "Guest")
    
    response = {
        "session_id": request.call_session_id,
        "from": request.from_number,
        "response": "Welcome to Wellness Partners! This is Erica, your scheduling assistant. How may I help you today?",
        "dynamic_variables": {
            "patient_name": patient_name,
            "caller_number": request.from_number
        }
    }
    
    return response

# 🔥 MCP TOOLS DISCOVERY - Telnyx discovers available tools here
@app.get("/mcp/tools")
async def get_tools():
    """MCP Tools Discovery Endpoint - Telnyx calls this to see what tools you offer"""
    tools = [
        {
            "name": "check_availability",
            "description": "Check available appointment slots for a given date, time and provider",
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
                    "provider": {"type": "string", "description": "Healthcare provider"},
                    "notes": {"type": "string", "description": "Any additional notes"}
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
        },
        {
            "name": "cancel_appointment",
            "description": "Cancel an existing appointment",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string", "description": "Patient's full name"},
                    "phone_number": {"type": "string", "description": "Patient's phone number"},
                    "appointment_date": {"type": "string", "description": "Appointment date to cancel"}
                },
                "required": ["patient_name", "phone_number", "appointment_date"]
            }
        }
    ]
    return {"tools": tools}

# 🔥 MCP TOOL EXECUTION - Telnyx calls specific tools here
@app.post("/mcp/tools/{tool_name}")
async def execute_tool(tool_name: str, parameters: dict):
    """Execute MCP Tools - Telnyx calls this when it needs to use a tool"""
    
    if tool_name == "check_availability":
        return await check_availability(parameters)
    
    elif tool_name == "book_appointment":
        return await book_appointment(parameters)
    
    elif tool_name == "get_services":
        return await get_services()
    
    elif tool_name == "cancel_appointment":
        return await cancel_appointment(parameters)
    
    else:
        raise HTTPException(status_code=404, detail="Tool not found")

# Tool implementations
async def check_availability(params: dict):
    """Check appointment availability"""
    date = params.get("date")
    time = params.get("time") 
    provider = params.get("provider")
    appointment_type = params.get("appointment_type")
    
    # Simple availability logic
    # In real app, check against existing appointments
    available_slots = [
        f"{time}",
        f"{int(time.split(':')[0])+1}:00",
        f"{int(time.split(':')[0])-1}:00"
    ]
    
    return {
        "available": True,
        "message": f"Appointment with {provider} for {appointment_type} is available on {date}",
        "available_slots": available_slots,
        "provider": provider,
        "appointment_type": appointment_type
    }

async def book_appointment(params: dict):
    """Book a new appointment"""
    conn = sqlite3.connect('wellness.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO appointments (patient_name, phone_number, appointment_date, appointment_time, appointment_type, provider, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            params["patient_name"],
            params["phone_number"], 
            params["appointment_date"],
            params["appointment_time"],
            params["appointment_type"],
            params["provider"],
            params.get("notes", "")
        ))
        
        appointment_id = cursor.lastrowid
        conn.commit()
        
        return {
            "success": True,
            "appointment_id": appointment_id,
            "message": f"Appointment confirmed for {params['patient_name']} with {params['provider']} on {params['appointment_date']} at {params['appointment_time']} for {params['appointment_type']}",
            "confirmation_number": f"APT{appointment_id:04d}"
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to book appointment: {str(e)}"
        }
    
    finally:
        conn.close()

async def get_services():
    """Get available services and providers"""
    services = {
        "services": [
            {
                "type": "Primary Care", 
                "providers": ["Dr. Smith", "Dr. Johnson", "Dr. Garcia"],
                "duration": "30-60 minutes",
                "description": "General health checkups, illness visits, follow-ups"
            },
            {
                "type": "Dermatology",
                "providers": ["Dr. Brown", "Dr. Davis"],
                "duration": "45 minutes", 
                "description": "Skin conditions, mole checks, cosmetic consultations"
            },
            {
                "type": "Physical Therapy",
                "providers": ["Dr. Wilson", "Dr. Miller"],
                "duration": "60 minutes",
                "description": "Rehabilitation, injury recovery, mobility improvement"
            },
            {
                "type": "Mental Health",
                "providers": ["Dr. Taylor", "Dr. Anderson"],
                "duration": "50 minutes",
                "description": "Counseling, therapy sessions, mental wellness"
            }
        ],
        "operating_hours": {
            "weekdays": "8:00 AM - 5:00 PM",
            "saturdays": "9:00 AM - 12:00 PM", 
            "sundays": "Closed"
        },
        "contact_info": {
            "address": "123 Wellness Drive, Health City, HC 12345",
            "phone": "(555) 123-HEAL"
        }
    }
    return services

async def cancel_appointment(params: dict):
    """Cancel an existing appointment"""
    conn = sqlite3.connect('wellness.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            DELETE FROM appointments 
            WHERE patient_name = ? AND phone_number = ? AND appointment_date = ?
        ''', (
            params["patient_name"],
            params["phone_number"],
            params["appointment_date"]
        ))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            return {
                "success": True,
                "message": f"Appointment for {params['patient_name']} on {params['appointment_date']} has been cancelled"
            }
        else:
            return {
                "success": False,
                "message": "No appointment found matching those details"
            }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to cancel appointment: {str(e)}"
        }
    
    finally:
        conn.close()

# 🔥 DYNAMIC VARIABLES ENDPOINT - Telnyx uses this for personalization
@app.post("/dynamic-variables")
async def update_dynamic_variables(variables: dict):
    """Update dynamic variables during a call session"""
    return {
        "dynamic_variables": {
            "patient_name": variables.get("patient_name", "Guest"),
            "last_interaction": datetime.now().isoformat(),
            "patient_preferences": variables.get("preferences", {}),
            "call_type": "wellness_booking"
        }
    }

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "Wellness Partners MCP Server is running!",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "mcp_tools": "/mcp/tools",
            "telnyx_webhook": "/telnyx/webhook", 
            "dynamic_variables": "/dynamic-variables"
        }
    }

# Get all appointments (for testing/admin)
@app.get("/appointments")
async def get_all_appointments():
    conn = sqlite3.connect('wellness.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM appointments ORDER BY appointment_date, appointment_time')
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
