# main.py - Claude-Compatible MCP Server
import asyncio
from mcp.server import Server
from mcp.server.fastapi import create_fastapi_app
import mcp.types as types
import sqlite3
from contextlib import asynccontextmanager

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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@asynccontextmanager
async def lifespan(server: Server):
    # Initialize on startup
    init_db()
    yield
    # Cleanup on shutdown

# Create MCP server
server = Server("wellness-center", lifespan=lifespan)

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Return list of available tools"""
    return [
        types.Tool(
            name="check_availability",
            description="Check available appointment slots for healthcare providers",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time": {"type": "string", "description": "HH:MM"},
                    "provider": {"type": "string", "description": "Doctor name"},
                    "appointment_type": {"type": "string", "description": "Service type"}
                },
                "required": ["date", "time", "provider", "appointment_type"]
            }
        ),
        types.Tool(
            name="book_appointment",
            description="Schedule a new healthcare appointment",
            inputSchema={
                "type": "object", 
                "properties": {
                    "patient_name": {"type": "string"},
                    "phone_number": {"type": "string"},
                    "appointment_date": {"type": "string"},
                    "appointment_time": {"type": "string"},
                    "appointment_type": {"type": "string"},
                    "provider": {"type": "string"}
                },
                "required": ["patient_name", "phone_number", "appointment_date", "appointment_time", "appointment_type", "provider"]
            }
        ),
        types.Tool(
            name="get_services",
            description="Get available healthcare services and providers", 
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool execution"""
    if name == "check_availability":
        return await check_availability(arguments)
    elif name == "book_appointment":
        return await book_appointment(arguments)
    elif name == "get_services":
        return await get_services()
    else:
        raise ValueError(f"Unknown tool: {name}")

async def check_availability(arguments: dict) -> list[types.TextContent]:
    date = arguments.get("date", "2024-01-01")
    time = arguments.get("time", "14:00") 
    provider = arguments.get("provider", "Dr. Smith")
    appointment_type = arguments.get("appointment_type", "Primary Care")
    
    return [
        types.TextContent(
            type="text",
            text=f"Available appointments with {provider} for {appointment_type} on {date} at {time}. Available times: 9:00 AM, 10:00 AM, 2:00 PM, 3:00 PM"
        )
    ]

async def book_appointment(arguments: dict) -> list[types.TextContent]:
    conn = sqlite3.connect('wellness.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO appointments (patient_name, phone_number, appointment_date, appointment_time, appointment_type, provider)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            arguments.get("patient_name", "Test Patient"),
            arguments.get("phone_number", "+1234567890"), 
            arguments.get("appointment_date", "2024-01-01"),
            arguments.get("appointment_time", "14:00"),
            arguments.get("appointment_type", "Primary Care"),
            arguments.get("provider", "Dr. Smith")
        ))
        
        appointment_id = cursor.lastrowid
        conn.commit()
        
        return [
            types.TextContent(
                type="text",
                text=f"✅ Appointment confirmed! Confirmation #APT{appointment_id:04d}\nPatient: {arguments.get('patient_name')}\nProvider: {arguments.get('provider')}\nDate: {arguments.get('appointment_date')} at {arguments.get('appointment_time')}\nType: {arguments.get('appointment_type')}"
            )
        ]
    except Exception as e:
        return [
            types.TextContent(
                type="text", 
                text=f"❌ Failed to book appointment: {str(e)}"
            )
        ]
    finally:
        conn.close()

async def get_services() -> list[types.TextContent]:
    return [
        types.TextContent(
            type="text",
            text="🏥 **Wellness Partners Services**\n\n• **Primary Care**: Dr. Smith, Dr. Johnson\n• **Dermatology**: Dr. Brown  \n• **Physical Therapy**: Dr. Wilson\n• **Mental Health**: Dr. Taylor\n\n📍 **Hours**: Monday-Friday 8:00 AM - 5:00 PM, Saturday 9:00 AM - 12:00 PM\n\n📞 **Contact**: (555) 123-HEAL"
        )
    ]

# Create FastAPI app
app = create_fastapi_app(server, "/api/mcp")

# Health check endpoint
@app.get("/")
async def health_check():
    return {
        "status": "running", 
        "service": "Wellness Center MCP Server",
        "compatible_with": "Claude Desktop & Telnyx AI",
        "endpoint": "/api/mcp"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
