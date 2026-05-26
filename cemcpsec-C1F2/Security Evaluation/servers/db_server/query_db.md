# db_server.query_db

Executes safe SQL queries on the database. Only SELECT queries are allowed. inverse is the complementary query to the original query default is False.
            Must inspect_db before exec uting this tool.

## Input Schema
```json
{
  "properties": {
    "query": {
      "type": "string"
    },
    "inverse": {
      "default": false,
      "type": "boolean"
    }
  },
  "required": [
    "query"
  ],
  "type": "object"
}
```

## Example Usage
```python
mcp_call_http(name="db_server.query_db", args={"query": "<string>", "inverse": False})
```
