import os
from costume_mcp_servers.db_init import get_shared_db
from costume_mcp_servers.threat_demo_server import (LegitimateDBHandler,
                                PhaseI_1DBHandler,
                                PhaseII_1DBHandler,
                                PhaseII_2DBHandler,
                                PhaseII_3DBHandler,
                                PhaseIII_1DBHandler,
                                PhaseIII_2DBHandler,
                                PhaseIV_1DBHandler)

enum_servers = [
    {"name": "Legitimate", "description": "Legitimate server", "value": "L"},
    {"name": "Phase I_1", "description": "Phase I_1 server", "value": "I_1"},
    {"name": "Phase II_1", "description": "Phase II_1 server", "value": "II_1"},
    {"name": "Phase II_2", "description": "Phase II_2 server", "value": "II_2"},
    {"name": "Phase II_3", "description": "Phase II_3 server", "value": "II_3"},
    {"name": "Phase III_1", "description": "Phase III_1 server", "value": "III_1"},
    {"name": "Phase III_2", "description": "Phase III_2 server", "value": "III_2"},
    {"name": "Phase IV_1", "description": "Phase IV_1 server", "value": "IV_1"},
]


def create_server(server_type: str = "L") -> LegitimateDBHandler:
    """Create a server with the given handler."""
    conn = get_shared_db()
    
    if server_type == "L":
        handler = LegitimateDBHandler(conn)
        handler.create_server()

    elif server_type == "I_1":
        handler = PhaseI_1DBHandler(conn)
        handler.create_server()

    elif server_type == "II_1":
        handler = PhaseII_1DBHandler(conn)
        handler.create_server()

    elif server_type == "II_2":
        handler = PhaseII_2DBHandler(conn)
        handler.create_server()

    elif server_type == "II_3":
        handler = PhaseII_3DBHandler(conn)
        handler.create_server()

    elif server_type == "III_1":
        handler = PhaseIII_1DBHandler(conn)
        handler.create_server()

    elif server_type == "III_2":
        handler = PhaseIII_2DBHandler(conn)
        handler.create_server()

    elif server_type == "IV_1":
        handler = PhaseIV_1DBHandler(conn)
        handler.create_server()

    else:
        raise ValueError(f"Invalid server type: {server_type}")
    
    return handler


HANDLER_SERVER = None
def get_handler_server():
    server_choice = os.getenv('SERVER_CHOICE', 'L')
    global HANDLER_SERVER
    if HANDLER_SERVER is None:
        HANDLER_SERVER = create_server(server_choice)
    return HANDLER_SERVER