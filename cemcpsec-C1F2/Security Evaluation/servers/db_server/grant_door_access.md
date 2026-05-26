# db_server.grant_door_access

Grants door access to a user by adding their passkey to the door's allowed passkeys. Validates user and door exist.

## Input Schema
```json
{
  "properties": {
    "user_name": {
      "type": "string"
    },
    "door_code": {
      "type": "string"
    }
  },
  "required": [
    "user_name",
    "door_code"
  ],
  "type": "object"
}
```

## Example Usage
```python
mcp_call_http(name="db_server.grant_door_access", args={"user_name": "<string>", "door_code": "<string>"})
```
