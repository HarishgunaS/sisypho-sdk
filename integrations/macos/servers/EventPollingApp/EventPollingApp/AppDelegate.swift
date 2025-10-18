import Cocoa
import os.log

class AppDelegate: NSObject, NSApplicationDelegate {
    private let logger = Logger(subsystem: "com.sisypho.eventpollingapp", category: "AppDelegate")
    private var eventQueue: EventQueue!
    private var pollingMonitor: EventPollingMonitor!
    private var eventServer: EventServer!

    func applicationDidFinishLaunching(_ aNotification: Notification) {
        // Configure logging
        logger.info("Event Polling App starting...")

        // Add system information for debugging
        print("DEBUG: macOS Version: \(ProcessInfo.processInfo.operatingSystemVersionString)")
        print("DEBUG: App Bundle ID: \(Bundle.main.bundleIdentifier ?? "Unknown")")
        print("DEBUG: App Path: \(Bundle.main.bundlePath)")
        print("DEBUG: Process ID: \(ProcessInfo.processInfo.processIdentifier)")

        // Check accessibility permissions at startup
        let trusted = AXIsProcessTrusted()
        print("DEBUG: Accessibility permissions status: \(trusted ? "GRANTED" : "NOT GRANTED")")

        if !trusted {
            logger.error(
                "Accessibility permissions not granted. Please enable accessibility access for this app in System Preferences > Security & Privacy > Privacy > Accessibility"
            )
            print(
                "ERROR: Accessibility permissions not granted. Please enable accessibility access for this app in System Preferences > Security & Privacy > Privacy > Accessibility"
            )

            // Show alert to user
            let alert = NSAlert()
            alert.messageText = "Accessibility Permission Required"
            alert.informativeText =
                "This app needs accessibility permissions to monitor system events. Please enable it in System Preferences > Security & Privacy > Privacy > Accessibility"
            alert.alertStyle = .warning
            alert.addButton(withTitle: "Open System Preferences")
            alert.addButton(withTitle: "Quit")

            let response = alert.runModal()
            if response == .alertFirstButtonReturn {
                NSWorkspace.shared.open(
                    URL(
                        string:
                            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
                    )!)
            }

            NSApplication.shared.terminate(nil)
            return
        } else {
            logger.info("Accessibility permissions granted")
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
            print("DEBUG: CGEventTap test creation FAILED - this indicates the breakpoint issue")
            print(
                "DEBUG: This usually means the app needs to be re-added to Accessibility permissions"
            )

            // Show specific error alert for CGEventTap failure
            let alert = NSAlert()
            alert.messageText = "CGEventTap Creation Failed"
            alert.informativeText =
                "The app cannot create event monitoring. This usually happens when:\n\n1. Accessibility permissions were reset\n2. The app was moved or rebuilt\n3. System security policies changed\n\nPlease remove this app from Accessibility permissions and re-add it."
            alert.alertStyle = .critical
            alert.addButton(withTitle: "Open System Preferences")
            alert.addButton(withTitle: "Quit")

            let response = alert.runModal()
            if response == .alertFirstButtonReturn {
                NSWorkspace.shared.open(
                    URL(
                        string:
                            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
                    )!)
            }

            NSApplication.shared.terminate(nil)
            return
        }

        // Create event queue and polling monitor
        eventQueue = EventQueue()
        pollingMonitor = EventPollingMonitor(eventQueue: eventQueue)

        // Create HTTP server
        do {
            eventServer = try EventServer(eventQueue: eventQueue)
        } catch {
            logger.error("Failed to create event server: \(error)")
            NSApplication.shared.terminate(nil)
            return
        }

        // Start polling and HTTP server
        pollingMonitor.startPolling()
        eventServer.start()

        logger.info("Event polling server started")
        logger.info("HTTP server available at http://localhost:8080")
        logger.info("Endpoints:")
        logger.info("  GET /events - Get all captured events")
        logger.info("  GET /count - Get event count")
        logger.info("  GET /stats - Get event statistics")
        logger.info("  DELETE /events - Clear all events")

        // Create status bar item
        createStatusBarItem()
    }

    func applicationWillTerminate(_ aNotification: Notification) {
        pollingMonitor?.stopPolling()
        eventServer?.stop()
        logger.info("Event polling server stopped")
    }

    func applicationSupportsSecureRestorableState(_ app: NSApplication) -> Bool {
        return true
    }

    private func createStatusBarItem() {
        let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)

        if let button = statusItem.button {
            button.title = "📊"
            button.toolTip = "Event Polling Server - Click to see status"
        }

        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "Server Status", action: nil, keyEquivalent: ""))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(
            NSMenuItem(
                title: "Open in Browser", action: #selector(openInBrowser), keyEquivalent: "o"))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(
            NSMenuItem(
                title: "Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))

        statusItem.menu = menu
    }

    @objc private func openInBrowser() {
        if let url = URL(string: "http://localhost:8080") {
            NSWorkspace.shared.open(url)
        }
    }
}
