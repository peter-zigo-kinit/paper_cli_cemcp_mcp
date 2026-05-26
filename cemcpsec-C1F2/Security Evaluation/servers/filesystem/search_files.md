# filesystem.search_files

Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you don't know their exact location. Only searches within allowed directories.

## Input Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "path": {
      "type": "string"
    },
    "pattern": {
      "type": "string"
    },
    "excludePatterns": {
      "default": [],
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "path",
    "pattern"
  ]
}
```

## Example Usage
```python
mcp_call_http(name="filesystem.search_files", args={"path": "<string>", "pattern": "<string>", "excludePatterns": []})
```
