# macOS Accessibility MCP Server with EventPollingApp Integration

This setup provides HTTP-based communication between the MCP server and the EventPollingApp for capturing user events (mouse clicks, keyboard presses, scroll events).

## Architecture

- **EventPollingApp**: A macOS app that polls for user events and exposes them via HTTP API
- **MCP Server**: The accessibility server that communicates with EventPollingApp via HTTP to get captured events (no local event storage)

## Setup Instructions

### 1. Build and Run EventPollingApp

```bash
cd integrations/macos/servers/EventPollingApp
xcodebuild -project EventPollingApp.xcodeproj -scheme EventPollingApp -configuration Release build
```

Or open the project in Xcode and run it directly.

### 2. Grant Accessibility Permissions

When EventPollingApp starts, it will check for accessibility permissions. If not granted:

1. Go to System Preferences > Security & Privacy > Privacy > Accessibility
2. Add EventPollingApp to the list of allowed apps
3. Restart EventPollingApp

### 3. Verify EventPollingApp is Running

The app will show a status bar icon (📊) when running. You can also test the HTTP server:

```bash
# Test the HTTP endpoints
curl http://localhost:8080/count
curl http://localhost:8080/events
```

Or use the provided test script:

```bash
python3 test_polling_server.py
```

### 4. Build and Run MCP Server

```bash
cd integrations/macos/servers
swift build -c release
.build/release/AccessibilityMCPServer
```

### 5. Test the Integration

Use the MCP tools to test the communication:

- `test_polling_server_connection`: Test if MCP server can connect to EventPollingApp
- `get_captured_events`: Get events from EventPollingApp
- `get_event_count`: Get event count from EventPollingApp
- `clear_captured_events`: Clear events from EventPollingApp

## HTTP API Endpoints

EventPollingApp exposes these endpoints on `http://localhost:8080`:

- `GET /count` - Get the number of captured events
- `GET /events` - Get all captured events as JSON
- `DELETE /events` - Clear all captured events

## Event Types

The system captures these event types:

- **click**: Mouse clicks with element information
- **keyboard**: Keyboard presses with key details
- **scroll**: Mouse scroll events
- **keyboard_modifier**: Modifier key changes (cmd, ctrl, alt, shift)

## Troubleshooting

### EventPollingApp not starting

- Check accessibility permissions
- Look for error messages in Console.app
- Verify the app is in the Applications folder

### MCP server can't connect to EventPollingApp

- Ensure EventPollingApp is running (check status bar icon)
- Test HTTP endpoints directly with curl
- Check firewall settings
- Verify port 8080 is not blocked

### No events being captured

- Ensure accessibility permissions are granted
- Check that EventPollingApp is actively polling (should see debug output)
- Try interacting with different apps to generate events

## Debug Information

Both apps provide debug output:

- EventPollingApp prints to console when events are captured
- MCP server logs HTTP communication attempts
- Use `test_event_monitoring` tool to check connection status

## Performance Notes

- EventPollingApp polls at 10Hz (every 0.1 seconds)
- HTTP requests have 2-second timeouts
- Events are stored in memory with a limit of 1000 events
- The MCP server relies entirely on EventPollingApp for event capture
