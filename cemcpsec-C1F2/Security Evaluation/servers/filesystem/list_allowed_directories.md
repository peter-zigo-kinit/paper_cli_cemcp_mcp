# filesystem.list_allowed_directories

Returns the list of directories that this server is allowed to access. Subdirectories within these allowed directories are also accessible. Use this to understand which directories and their nested paths are available before trying to access files.

## Input Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {}
}
```

## Example Usage
```python
mcp_call_http(name="filesystem.list_allowed_directories", args={})
```
