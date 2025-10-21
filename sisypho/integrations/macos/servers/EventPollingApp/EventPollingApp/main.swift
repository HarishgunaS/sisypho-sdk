import ApplicationServices
import CoreGraphics
import Foundation
import os.log

// Global variables for cleanup
var globalPollingMonitor: EventPollingMonitor?
var globalEventServer: EventServer?

// Signal handler function (C-compatible)
func signalHandler(signal: Int32) {
    print("\nShutting down...")
    globalPollingMonitor?.stopPolling()
    globalEventServer?.stop()
    print("✓ Event polling server stopped")
    exit(0)
}

// Command line version of EventPollingApp
struct EventPollingAppCLI {
    static func main() {
        let logger = Logger(subsystem: "com.sisypho.eventpollingapp", category: "CLI")

        print("Event Polling App CLI starting...")
        logger.info("Event Polling App CLI starting...")

        // Add system information for debugging
        print("DEBUG: macOS Version: \(ProcessInfo.processInfo.operatingSystemVersionString)")
        print("DEBUG: Process ID: \(ProcessInfo.processInfo.processIdentifier)")

        // Check accessibility permissions at startup
        let trusted = AXIsProcessTrusted()
        print("DEBUG: Accessibility permissions status: \(trusted ? "GRANTED" : "NOT GRANTED")")

        // Check if we're running as a child process of Electron
        let parentProcessId = ProcessInfo.processInfo.environment["PARENT_PROCESS_ID"]
        let isChildProcess = parentProcessId != nil

        if !trusted {
            if isChildProcess {
                // If we're a child process, try to continue anyway
                print("WARNING: Running as child process without direct accessibility permissions")
                print("Attempting to continue with parent process permissions...")
                logger.warning(
                    "Running as child process - attempting to continue without direct permissions")

                // For child processes, we'll try to continue anyway
                // The parent process should have the necessary permissions
            } else {
                logger.error("Accessibility permissions not granted")
                print("ERROR: Accessibility permissions not granted.")
                print("Please enable accessibility access for this app in:")
                print("System Preferences > Security & Privacy > Privacy > Accessibility")
                print("")
                print("You can open System Preferences with:")
                print(
                    "open 'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'"
                )
                exit(1)
            }
        } else {
            logger.info("Accessibility permissions granted")
            print("✓ Accessibility permissions granted")
        }

        // Test CGEventTap creation before starting anything else
        print("DEBUG: Testing CGEventTap creation...")
        let testEventTap = CGEvent.tapCreate(
            tap: .cgSessionEventTap,
            place: .headInsertEventTap,
            options: .defaultTap,
            eventsOfInterest: CGEventMask(1 << CGEventType.keyDown.rawValue),
            callback: { _, _, _, _ in return nil },
            userInfo: nil
        )

        if testEventTap != nil {
            print("DEBUG: CGEventTap test creation successful")
            CFMachPortInvalidate(testEventTap!)
        } else {
            print("DEBUG: CGEventTap test creation FAILED")
            if isChildProcess {
                print("WARNING: CGEventTap creation failed for child process")
                print("This is expected when running as a child process without direct permissions")
                print("Attempting to continue with parent process permissions...")
                logger.warning(
                    "CGEventTap creation failed for child process - attempting to continue")

                // For child processes, we'll try to continue anyway
                // The parent process should have the necessary permissions
            } else {
                print("ERROR: CGEventTap creation failed. This usually happens when:")
                print("1. Accessibility permissions were reset")
                print("2. The app was moved or rebuilt")
                print("3. System security policies changed")
                print("")
                print("Please remove this app from Accessibility permissions and re-add it.")
                exit(1)
            }
        }

        // Create event queue and polling monitor
        let eventQueue = EventQueue()
        let pollingMonitor = EventPollingMonitor(eventQueue: eventQueue)

        // Create HTTP server
        let eventServer: EventServer
        do {
            eventServer = try EventServer(eventQueue: eventQueue)
        } catch {
            logger.error("Failed to create event server: \(error)")
            print("ERROR: Failed to create event server: \(error)")
            exit(1)
        }

        // Store references for signal handler
        globalPollingMonitor = pollingMonitor
        globalEventServer = eventServer

        // Start polling and HTTP server
        pollingMonitor.startPolling()
        eventServer.start()

        logger.info("Event polling server started")
        print("✓ Event polling server started")
        print("✓ HTTP server available at http://localhost:8080")
        print("")
        print("Available endpoints:")
        print("  GET /events - Get all captured events")
        print("  GET /count - Get event count")
        print("  GET /stats - Get event statistics")
        print("  DELETE /events - Clear all events")
        print("")
        print("Press Ctrl+C to stop the server")

        // Set up signal handling for graceful shutdown
        signal(SIGINT, signalHandler)

        // Keep the main thread alive
        RunLoop.main.run()
    }
}

// Call the main function
EventPollingAppCLI.main()
