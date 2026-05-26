# db_server.add_user_record

Adds a user record to the database with proper validation and security checks

## Input Schema
```json
{
  "properties": {
    "name": {
      "type": "string"
    },
    "role": {
      "type": "string"
    },
    "passkey": {
      "type": "string"
    }
  },
  "required": [
    "name",
    "role",
    "passkey"
  ],
  "type": "object"
}
```

## Example Usage
```python
mcp_call_http(name="db_server.add_user_record", args={"name": "<string>", "role": "<string>", "passkey": "<string>"})
```
