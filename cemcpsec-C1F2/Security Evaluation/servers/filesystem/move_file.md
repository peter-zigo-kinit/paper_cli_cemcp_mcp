# filesystem.move_file

Move or rename files and directories. Can move files between directories and rename them in a single operation. If the destination exists, the operation will fail. Works across different directories and can be used for simple renaming within the same directory. Both source and destination must be within allowed directories.

## Input Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "source": {
      "type": "string"
    },
    "destination": {
      "type": "string"
    }
  },
  "required": [
    "source",
    "destination"
  ]
}
```

## Example Usage
```python
mcp_call_http(name="filesystem.move_file", args={"source": "<string>", "destination": "<string>"})
```
