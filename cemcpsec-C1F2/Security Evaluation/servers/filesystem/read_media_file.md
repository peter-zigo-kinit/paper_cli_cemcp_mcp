# filesystem.read_media_file

Read an image or audio file. Returns the base64 encoded data and MIME type. Only works within allowed directories.

## Input Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "path": {
      "type": "string"
    }
  },
  "required": [
    "path"
  ]
}
```

## Example Usage
```python
mcp_call_http(name="filesystem.read_media_file", args={"path": "<string>"})
```
