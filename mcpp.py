from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import json
from datetime import datetime

app = FastAPI(title="Universal Wellness MCP Server")

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

# 🔥 MULTIPLE MCP ENDPOINT PATTERNS (Try them all)

# Pattern 1: Standard MCP
@app.get("/mcp/tools")
async def mcp_tools_standard():
    return await get_tools_data()

# Pattern 2: Telnyx-specific path
@app.get("/v2/ai/mcp_servers/list_tools")
async def mcp_tools_telnyx():
    return await get_tools_data()

# Pattern 3: Simple tools endpoint
@app.get("/tools")
async def mcp_tools_simple():
    return await get_tools_data()

# Pattern 4: Root tools
@app.get("/list_tools")
async def mcp_tools_root():
    return await get_tools_data()

# Common tools data
async def get_tools_data():
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

# 🔥 MULTIPLE TOOL EXECUTION ENDPOINTS

@app.post("/mcp/tools/{tool_name}")
async def execute_tool_standard(tool_name: str, request: dict):
    return await execute_tool_common(tool_name, request)

@app.post("/v2/ai/mcp_servers/execute_tool")
async def execute_tool_telnyx(request: dict):
    tool_name = request.get("name")
    arguments = request.get("arguments", {})
    return await execute_tool_common(tool_name, arguments)

@app.post("/tools/{tool_name}")
async def execute_tool_simple(tool_name: str, request: dict):
    return await execute_tool_common(tool_name, request)

# Common tool execution logic
async def execute_tool_common(tool_name: str, arguments: dict):
    if tool_name == "check_availability":
        return await check_availability(arguments)
    elif tool_name == "book_appointment":
        return await book_appointment(arguments)
    elif tool_name == "get_services":
        return await get_services()
    else:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")

# Your existing tool implementations
async def check_availability(params: dict):
    return {
        "content": [
            {
                "type": "text",
                "text": f"Available appointments with {params.get('provider')} on {params.get('date')}. Times: 2:00 PM, 3:00 PM, 4:00 PM"
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
                    "text": f"Appointment confirmed! Confirmation #APT{appointment_id:04d}"
                }
            ]
        }
    except Exception as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Booking failed: {str(e)}"
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
                "text": "Available services: Primary Care, Dermatology, Physical Therapy. Providers: Dr. Smith, Dr. Johnson, Dr. Brown, Dr. Wilson."
            }
        ]
    }

# Webhook endpoints (keep existing)
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
        "message": "Universal Wellness MCP Server is running!",
        "status": "healthy",
        "endpoints": {
            "health": "/",
            "mcp_tools_standard": "/mcp/tools",
            "mcp_tools_telnyx": "/v2/ai/mcp_servers/list_tools", 
            "mcp_tools_simple": "/tools",
            "mcp_tools_root": "/list_tools",
            "webhook": "/telnyx/webhook"
        },
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
