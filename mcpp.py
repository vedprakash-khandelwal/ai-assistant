from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sqlite3
import json
from datetime import datetime

app = FastAPI(title="Wellness Center - Telnyx MCP Server")

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

# Telnyx MCP Tools Discovery - TELNYX SPECIFIC FORMAT
@app.get("/v2/ai/mcp_servers/list_tools")
async def list_tools():
    """Telnyx-specific MCP tools endpoint"""
    return {
        "tools": [
            {
                "name": "check_availability",
                "description": "Check available appointment slots for healthcare providers",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Appointment date in YYYY-MM-DD format"},
                        "time": {"type": "string", "description": "Appointment time in HH:MM format"},
                        "provider": {"type": "string", "description": "Healthcare provider name"},
                        "appointment_type": {"type": "string", "description": "Type of appointment (Primary Care, Dermatology, etc)"}
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
                        "appointment_date": {"type": "string", "description": "Appointment date in YYYY-MM-DD format"},
                        "appointment_time": {"type": "string", "description": "Appointment time in HH:MM format"},
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

# Telnyx MCP Tool Execution - TELNYX SPECIFIC FORMAT
@app.post("/v2/ai/mcp_servers/execute_tool")
async def execute_tool(request: dict):
    """Telnyx-specific tool execution endpoint"""
    tool_name = request.get("name")
    arguments = request.get("arguments", {})
    
    if tool_name == "check_availability":
        return await check_availability(arguments)
    elif tool_name == "book_appointment":
        return await book_appointment(arguments)
    elif tool_name == "get_services":
        return await get_services()
    else:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")

# Keep your existing tool implementations
async def check_availability(params: dict):
    date = params.get("date", "2024-01-01")
    time = params.get("time", "14:00")
    provider = params.get("provider", "Dr. Smith")
    appointment_type = params.get("appointment_type", "Primary Care")
    
    return {
        "content": [
            {
                "type": "text",
                "text": f"Available appointments with {provider} for {appointment_type} on {date} at {time}. I have slots at 2:00 PM, 3:00 PM, and 4:00 PM."
            }
        ]
    }

async def book_appointment(params: dict):
    conn = sqlite3.connect('wellness.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO appointments (patient_name, phone_number, appointment_date, appointment_time, appointment_type, provider)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            params.get("patient_name", "Test Patient"),
            params.get("phone_number", "+1234567890"),
            params.get("appointment_date", "2024-01-01"),
            params.get("appointment_time", "14:00"),
            params.get("appointment_type", "Primary Care"),
            params.get("provider", "Dr. Smith")
        ))
        
        appointment_id = cursor.lastrowid
        conn.commit()
        
        return {
            "content": [
                {
                    "type": "text", 
                    "text": f"Appointment confirmed for {params.get('patient_name')} with {params.get('provider')} on {params.get('appointment_date')} at {params.get('appointment_time')}. Confirmation number: APT{appointment_id:04d}"
                }
            ]
        }
    except Exception as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Failed to book appointment: {str(e)}"
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
                "text": "We offer the following services: Primary Care with Dr. Smith and Dr. Johnson, Dermatology with Dr. Brown, and Physical Therapy with Dr. Wilson. Our hours are Monday-Friday 8AM-5PM."
            }
        ]
    }

# Keep your existing webhook endpoints (they should work fine)
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

@app.get("/")
async def root():
    return {
        "message": "Wellness Center Telnyx MCP Server is running!",
        "endpoints": {
            "telnyx_mcp_tools": "/v2/ai/mcp_servers/list_tools",
            "telnyx_mcp_execute": "/v2/ai/mcp_servers/execute_tool",
            "webhook": "/telnyx/webhook",
            "dynamic_vars": "/dynamic-variables"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
