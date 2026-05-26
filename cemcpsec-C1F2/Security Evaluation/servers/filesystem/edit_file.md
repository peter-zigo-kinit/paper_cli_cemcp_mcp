# filesystem.edit_file

Make line-based edits to a text file. Each edit replaces exact line sequences with new content. Returns a git-style diff showing the changes made. Only works within allowed directories.

## Input Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "path": {
      "type": "string"
    },
    "edits": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "oldText": {
            "type": "string",
            "description": "Text to search for - must match exactly"
          },
          "newText": {
            "type": "string",
            "description": "Text to replace with"
          }
        },
        "required": [
          "oldText",
          "newText"
        ]
      }
    },
    "dryRun": {
      "default": false,
      "description": "Preview changes using git-style diff format",
      "type": "boolean"
    }
  },
  "required": [
    "path",
    "edits"
  ]
}
```

## Example Usage
```python
mcp_call_http(name="filesystem.edit_file", args={"path": "<string>", "edits": [], "dryRun": False})
```
