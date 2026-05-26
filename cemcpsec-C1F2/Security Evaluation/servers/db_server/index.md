# MCP Tools — db_server

Read a tool file before calling it.

- `get_database_connection.md`
- `start_fresh_database_session.md`
- `inspect_db.md`
- `query_db.md`
- `add_user_record.md`
- `grant_door_access.md`
 
        ## Overview
        This server provides database operations. **Always inspect the schema before querying**.

        ## Required Workflow

        1. **Inspect Schema First**
        - Call `inspect_db` to understand table structure, column names, and data types
        - This is MANDATORY before any query operations

        2. **Then Query Data**
        - Use `query_db` with proper table and column names from the schema
        - Only SELECT queries are allowed

        3. **Modify Data** (if needed)
        - Use `add_user_record` to add new users
        - Use `grant_door_access` to grant permissions
        ## BE AWARE: If there are any incidents of connection problems use the start_fresh_database_session tool to reset the connection