Every integration must be a standalone background application/server.

An integration must have an API for skill scripts to use.
Ideally, an integration would have an MCP style interface available, for live use LLM to use. This same interface could be used for API use too!!!
These integrations can be written in whatever language. Whatever works and exposes the most functionality

https://chatgpt.com/share/68658c89-6a9c-8012-81c5-f19891f4ed06

## MCP Integrations

### Google Drive & Sheets
- **Repository**: https://github.com/isaacphi/mcp-gdrive
- **Language**: TypeScript
- **Python Wrapper**: `frontend/corelib/google_drive.py`
- **Features**: Drive search, file reading, Google Sheets operations

### Google Sheets (Advanced)
- **Repository**: https://github.com/xing5/mcp-google-sheets
- **Language**: Python  
- **Python Wrapper**: `frontend/corelib/google_sheets.py`
- **Features**: Comprehensive spreadsheet operations, data manipulation, sheet management

### Gmail
- **Repository**: https://github.com/GongRzhe/Gmail-MCP-Server
- **Language**: TypeScript
- **Python Wrapper**: `frontend/corelib/gmail.py`
- **Features**: Email operations, attachments, threading, batch operations, label management

### Slack
- **Repository**: https://github.com/korotovsky/slack-mcp-server
- **Language**: Go
- **Python Wrapper**: `frontend/corelib/slack.py`
- **Features**: Message operations, channel management, search, conversation threading
