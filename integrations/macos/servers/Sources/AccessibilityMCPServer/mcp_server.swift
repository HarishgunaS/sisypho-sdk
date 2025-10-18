import AppKit
import ApplicationServices
import Carbon
import CoreGraphics
import Foundation
import Logging
import MCP
import ServiceLifecycle

// MARK: - Event Queue System
struct UserEvent: Codable {
    let timestamp: Date
    let type: String  // "click", "keyboard", "scroll", or "keyboard_modifier"
    let details: [String: String]  // Simplified to avoid Codable issues with Any

    init(timestamp: Date, type: String, details: [String: String]) {
        self.timestamp = timestamp
        self.type = type
        self.details = details
    }

    // Custom Codable implementation for [String: String]
    enum CodingKeys: String, CodingKey {
        case timestamp, type, details
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        timestamp = try container.decode(Date.self, forKey: .timestamp)
        type = try container.decode(String.self, forKey: .type)
        details = try container.decode([String: String].self, forKey: .details)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(timestamp, forKey: .timestamp)
        try container.encode(type, forKey: .type)
        try container.encode(details, forKey: .details)
    }
}

// MARK: - Event Monitoring
final class EventMonitor: @unchecked Sendable {
    private var mouseMonitor: Any?
    private var keyboardMonitor: Any?
    private var axObserver: AXObserver?
    private let logger = Logger(label: "com.sisypho.eventmonitor")
    private var lastMouseLocation: NSPoint = NSEvent.mouseLocation
    private var lastElementInfo: ElementInfo = getElementAtLocation()
    private var lastMouseButtonState: UInt = 0
    private var lastKeyState: UInt = 0

    func startMonitoring() {
        logger.info("DEBUG: Starting event monitoring...")

        // Set up AXObserver for accessibility events
        setupAXObserver()

        // Monitor mouse clicks
        logger.info("DEBUG: Creating mouse monitor...")
        mouseMonitor = NSEvent.addGlobalMonitorForEvents(matching: [
            .leftMouseDown, .rightMouseDown, .otherMouseDown, .leftMouseUp, .rightMouseUp,
            .otherMouseUp,
        ]) { event in
            self.logger.info("DEBUG: MOUSE CLICK DETECTED!")
            // Get the element at the click location
            // let clickLocation = event.locationInWindow
            // currently using the current mouse location instead of click coordinates
            let elementInfo = getElementAtLocation()

            let eventDetails: [String: String] = [
                "button": String(event.buttonNumber),
                "clickCount": String(event.clickCount),
                "location_x": String(format: "%.2f", NSEvent.mouseLocation.x),
                "location_y": String(format: "%.2f", NSEvent.mouseLocation.y),
                "modifierFlags": String(event.modifierFlags.rawValue),
                "windowNumber": String(event.windowNumber),
                "element_type": elementInfo.type,
                "element_title": elementInfo.title,
                "element_label": elementInfo.label,
                "element_value": elementInfo.value,
                "element_pressable": String(elementInfo.pressable),
                "element_identifier": elementInfo.identifier ?? "None",
            ]

            let userEvent = UserEvent(
                timestamp: Date(),
                type: "click",
                details: eventDetails
            )

            self.logger.info("Mouse click captured: \(eventDetails)")
            self.logger.info(
                "DEBUG: Mouse click captured - Button: \(event.buttonNumber), Location: (\(NSEvent.mouseLocation.x), \(NSEvent.mouseLocation.y))"
            )
        }

        logger.info("DEBUG: Mouse monitor created: \(mouseMonitor != nil)")

        // Monitor keyboard events
        logger.info("DEBUG: Creating keyboard monitor...")
        keyboardMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.keyDown, .keyUp]) { event in
            self.logger.info("DEBUG: KEYBOARD PRESS DETECTED!")
            let eventDetails: [String: String] = [
                "keyCode": String(event.keyCode),
                "characters": event.characters ?? "",
                "charactersIgnoringModifiers": event.charactersIgnoringModifiers ?? "",
                "modifierFlags": String(event.modifierFlags.rawValue),
                "isARepeat": String(event.isARepeat),
                "windowNumber": String(event.windowNumber),
            ]

            let userEvent = UserEvent(
                timestamp: Date(),
                type: "keyboard",
                details: eventDetails
            )

            self.logger.info("Keyboard press captured: \(eventDetails)")
            self.logger.info(
                "DEBUG: Keyboard press captured - Key: \(event.characters ?? "unknown"), KeyCode: \(event.keyCode)"
            )
        }

        logger.info("DEBUG: Keyboard monitor created: \(keyboardMonitor != nil)")

        // Also try monitoring mouse movement as a test
        let mouseMoveMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.mouseMoved]) { event in
            self.logger.info(
                "DEBUG: Mouse moved to: (\(event.locationInWindow.x), \(event.locationInWindow.y))")
        }
        logger.info("DEBUG: Mouse move monitor created: \(mouseMoveMonitor != nil)")

        // Also try a local monitor as a test
        let localMouseMonitor = NSEvent.addLocalMonitorForEvents(matching: [.leftMouseDown]) {
            event in
            self.logger.info("DEBUG: LOCAL MOUSE CLICK DETECTED!")
            return event
        }
        logger.info("DEBUG: Local mouse monitor created: \(localMouseMonitor != nil)")

        // Test if app is active
        Task { @MainActor in
            logger.info("DEBUG: App is active: \(NSApplication.shared.isActive)")
            logger.info("DEBUG: App is running: \(NSApplication.shared.isRunning)")
        }

        // EventPollingApp handles all event capture via HTTP

        logger.info("Event monitoring started")
    }

    func stopMonitoring() {
        if let mouseMonitor = mouseMonitor {
            NSEvent.removeMonitor(mouseMonitor)
            self.mouseMonitor = nil
        }

        if let keyboardMonitor = keyboardMonitor {
            NSEvent.removeMonitor(keyboardMonitor)
            self.keyboardMonitor = nil
        }

        logger.info("Event monitoring stopped")
    }

    private func setupAXObserver() {
        logger.info("DEBUG: Setting up AXObserver...")

        // For now, just log that we're setting up AXObserver
        // The complex callback setup can be implemented later
        logger.info("DEBUG: AXObserver setup - callback implementation pending")
    }

    func handleAXEvent(element: AXUIElement, notification: CFString) {
        logger.info("DEBUG: AX Event detected: \(notification)")

        let elementInfo = getElementInfo(element: element)
        let eventDetails: [String: String] = [
            "notification": notification as String,
            "element_type": elementInfo.type,
            "element_title": elementInfo.title,
            "element_label": elementInfo.label,
            "element_value": elementInfo.value,
            "element_pressable": String(elementInfo.pressable),
            "element_identifier": elementInfo.identifier ?? "None",
            "location_x": String(format: "%.2f", NSEvent.mouseLocation.x),
            "location_y": String(format: "%.2f", NSEvent.mouseLocation.y),
        ]

        let userEvent = UserEvent(
            timestamp: Date(),
            type: "accessibility",
            details: eventDetails
        )

        logger.info("Accessibility event captured: \(eventDetails)")
    }

}

// Global event monitor instance
let globalEventMonitor = EventMonitor()

// MARK: - Data Models
struct ElementInfo: Codable {
    let index: Int?
    let label: String
    let title: String
    let value: String
    let type: String
    let text: String?
    let description: String?
    let pressable: Bool
    let availableActions: [String]
    let hasMenu: Bool
    let menuItems: [MenuItem]?
    let identifier: String?
}

struct MenuItem: Codable {
    let index: Int
    let title: String
}

// MARK: - Helper Functions
func getString(_ value: CFTypeRef?) -> String? {
    guard let value = value else { return nil }
    if CFGetTypeID(value) == CFStringGetTypeID() {
        return value as? String
    }
    return nil
}

func getGroupTransparentChildrenWithInfo(element: AXUIElement) -> [(AXUIElement, ElementInfo)] {
    var childrenValue: CFTypeRef?
    let result = AXUIElementCopyAttributeValue(
        element, kAXChildrenAttribute as CFString, &childrenValue)
    if result == .success, let children = childrenValue as? [AXUIElement] {
        var results: [(AXUIElement, ElementInfo)] = []
        for child in children {
            let childInfo = getElementInfo(element: child)
            fputs("Found child \(childInfo), of type \(childInfo.type)", stderr)
            if childInfo.type == "AXGroup" {
                fputs("Recursing down group", stderr)
                let recursiveResults = getGroupTransparentChildrenWithInfo(element: child)
                results.append(contentsOf: recursiveResults)
                continue
            }
            results.append((child, childInfo))
        }
        return results
    }
    return []
}
func getChildren(element: AXUIElement) -> [AXUIElement] {
    var childrenValue: CFTypeRef?
    let result = AXUIElementCopyAttributeValue(
        element, kAXChildrenAttribute as CFString, &childrenValue)
    if result == .success, let children = childrenValue as? [AXUIElement] {
        return children
    }
    return []
}

func getParent(element: AXUIElement) -> AXUIElement? {
    var parentValue: CFTypeRef?
    let result = AXUIElementCopyAttributeValue(
        element, kAXParentAttribute as CFString, &parentValue)
    if result == .success, let parent = parentValue {
        if CFGetTypeID(parent) == AXUIElementGetTypeID() {
            return parent as! AXUIElement
        }
    }
    return nil
}

func hasAction(element: AXUIElement, actionName: String) -> Bool {
    var actionNamesCFArray: CFArray?
    let actionNamesResult = AXUIElementCopyActionNames(element, &actionNamesCFArray)
    if actionNamesResult == .success, let actionNamesCFArray = actionNamesCFArray as? [String] {
        return actionNamesCFArray.contains(actionName)
    }
    return false
}

func getElementInfo(element: AXUIElement, index: Int? = nil) -> ElementInfo {
    var roleValue: CFTypeRef?
    AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &roleValue)
    let role = getString(roleValue) ?? "Unknown"

    var titleValue: CFTypeRef?
    AXUIElementCopyAttributeValue(element, kAXTitleAttribute as CFString, &titleValue)
    let title = getString(titleValue) ?? ""

    var descriptionValue: CFTypeRef?
    AXUIElementCopyAttributeValue(element, kAXDescriptionAttribute as CFString, &descriptionValue)
    let description = getString(descriptionValue) ?? "None"

    var valueValue: CFTypeRef?
    AXUIElementCopyAttributeValue(element, kAXValueAttribute as CFString, &valueValue)
    let value = getString(valueValue) ?? "None"

    var identifierValue: CFTypeRef?
    AXUIElementCopyAttributeValue(element, kAXIdentifierAttribute as CFString, &identifierValue)
    let identifier = getString(identifierValue) ?? "None"

    // Get additional text for specific roles
    var text: String? = nil
    switch role {
    case "AXStaticText":
        var textValue: CFTypeRef?
        if AXUIElementCopyAttributeValue(element, kAXValueAttribute as CFString, &textValue)
            == .success
        {
            text = getString(textValue)
        }
    case "AXTextField", "AXTextArea":
        var textValue: CFTypeRef?
        if AXUIElementCopyAttributeValue(element, kAXValueAttribute as CFString, &textValue)
            == .success
        {
            text = getString(textValue)
        }
    default:
        break
    }

    // Check if element is pressable
    var actionNamesCFArray: CFArray?
    let actionNamesResult = AXUIElementCopyActionNames(element, &actionNamesCFArray)
    var availableActions: [String] = []
    var isPressable = false
    if actionNamesResult == .success, let actionNamesCFArray = actionNamesCFArray as? [String] {
        availableActions = actionNamesCFArray
        let pressableActions = ["AXPress", "AXClick", "AXTap"]
        isPressable = actionNamesCFArray.contains { pressableActions.contains($0) }
    }

    // Check for menu options
    var hasMenu = false
    var menuItems: [MenuItem]? = nil
    var menuValue: CFTypeRef?
    if AXUIElementCopyAttributeValue(element, "AXMenu" as CFString, &menuValue) == .success {
        if CFGetTypeID(menuValue!) == AXUIElementGetTypeID() {
            hasMenu = true
            let menu = menuValue as! AXUIElement
            var menuItemsValue: CFTypeRef?
            if AXUIElementCopyAttributeValue(
                menu, kAXChildrenAttribute as CFString, &menuItemsValue) == .success,
                let menuItemsArray = menuItemsValue as? [AXUIElement]
            {
                menuItems = []
                for (menuIndex, menuItem) in menuItemsArray.enumerated() {
                    var menuItemTitleValue: CFTypeRef?
                    if AXUIElementCopyAttributeValue(
                        menuItem, kAXTitleAttribute as CFString, &menuItemTitleValue) == .success
                    {
                        let menuItemTitle = getString(menuItemTitleValue) ?? "Unknown"
                        menuItems!.append(MenuItem(index: menuIndex, title: menuItemTitle))
                    }
                }
            }
        }
    }

    return ElementInfo(
        index: index,
        label: description,
        title: title,
        value: value,
        type: role,
        text: text,
        description: description,
        pressable: isPressable,
        availableActions: availableActions,
        hasMenu: hasMenu,
        menuItems: menuItems,
        identifier: identifier
    )
}

func navigateToElement(startElement: AXUIElement, path: [String]) -> AXUIElement? {
    var currentElement = startElement
    for pathComponent in path {
        guard let index = Int(pathComponent) else { return nil }
        let children = getChildren(element: currentElement)
        guard index >= 0 && index < children.count else { return nil }
        currentElement = children[index]
    }
    return currentElement
}

func performAction(element: AXUIElement, actionName: String) -> Bool {
    // First try to perform the action on the target element
    let result = AXUIElementPerformAction(element, actionName as CFString)
    if result == .success {
        return true
    }

    // Iteratively check up to 10 parents for the required action
    var currentElement = element
    var depth = 0
    let maxDepth = 10
    while depth < maxDepth {
        if let parent = getParent(element: currentElement) {
            if hasAction(element: parent, actionName: actionName) {
                let parentResult = AXUIElementPerformAction(parent, actionName as CFString)
                if parentResult == .success {
                    return true
                }
            }
            currentElement = parent
            depth += 1
        } else {
            break
        }
    }

    return false
}

func findElementWithAction(element: AXUIElement, actionName: String, searchChildren: Bool)
    -> AXUIElement?
{
    if searchChildren {
        // Search recursively through children
        return findElementWithActionInChildren(element: element, actionName: actionName)
    } else {
        // Search recursively through parents
        return findElementWithActionInParents(element: element, actionName: actionName)
    }
}

func findElementWithActionInChildren(element: AXUIElement, actionName: String) -> AXUIElement? {
    // Check if current element has the action
    if hasAction(element: element, actionName: actionName) {
        return element
    }

    // Search through children
    let children = getChildren(element: element)
    for child in children {
        if let foundElement = findElementWithActionInChildren(
            element: child, actionName: actionName)
        {
            return foundElement
        }
    }

    return nil
}

func findElementWithActionInParents(element: AXUIElement, actionName: String) -> AXUIElement? {
    // Check if current element has the action
    if hasAction(element: element, actionName: actionName) {
        return element
    }

    // Search through parents
    if let parent = getParent(element: element) {
        return findElementWithActionInParents(element: parent, actionName: actionName)
    }

    return nil
}

func getFrontmostAppElement() -> (AXUIElement, String)? {
    guard let frontmostApp = NSWorkspace.shared.frontmostApplication else { return nil }
    let pid = frontmostApp.processIdentifier
    let appElement = AXUIElementCreateApplication(pid)
    let result = AXUIElementSetAttributeValue(
        appElement, "AXManualAccessibility" as CFString, true as CFTypeRef)
    fputs(
        "Setting 'AXManualAccessibility' \(result.rawValue == 0 ? "succeeded" : "failed")", stderr)

    // Check if we have accessibility permissions
    let trusted = AXIsProcessTrusted()
    if !trusted {
        print(
            "ERROR: Accessibility permissions not granted. Please enable accessibility access for this app in System Preferences > Security & Privacy > Privacy > Accessibility"
        )
        return nil
    }

    var mainWindow: CFTypeRef?
    guard
        AXUIElementCopyAttributeValue(appElement, kAXMainWindowAttribute as CFString, &mainWindow)
            == .success,
        let main = mainWindow
    else { return nil }
    let mainWindowElement = main as! AXUIElement
    let appName = frontmostApp.localizedName ?? "Unknown App"
    return (mainWindowElement, appName)
}

func getAppElement(appName: String? = nil, bundleId: String? = nil) -> (AXUIElement, String)? {
    fputs("DEBUG: Getting app element!", stderr)
    // Check if we have accessibility permissions
    let trusted = AXIsProcessTrusted()
    if !trusted {
        print(
            "ERROR: Accessibility permissions not granted. Please enable accessibility access for this app in System Preferences > Security & Privacy > Privacy > Accessibility"
        )
        return nil
    }

    let runningApps = NSWorkspace.shared.runningApplications
    var targetApp: NSRunningApplication?

    if let bundleId = bundleId {
        // Find app by bundle identifier
        targetApp = runningApps.first { app in
            app.bundleIdentifier?.lowercased() == bundleId.lowercased()
        }
    } else if let appName = appName {
        // Find app by name (case-insensitive)
        targetApp = runningApps.first { app in
            app.localizedName?.lowercased() == appName.lowercased()
        }
    } else {
        // Fall back to frontmost app
        targetApp = NSWorkspace.shared.frontmostApplication
    }

    guard let app = targetApp else { return nil }

    let pid = app.processIdentifier
    let appElement = AXUIElementCreateApplication(pid)
    let result = AXUIElementSetAttributeValue(
        appElement, "AXManualAccessibility" as CFString, true as CFTypeRef)
    fputs(
        "Setting 'AXManualAccessibility' \(result == AXError.success ? "succeeded" : "failed")",
        stderr)

    var mainWindow: CFTypeRef?
    guard
        AXUIElementCopyAttributeValue(appElement, kAXMainWindowAttribute as CFString, &mainWindow)
            == .success,
        let main = mainWindow
    else { return nil }
    let mainWindowElement = main as! AXUIElement
    let appName = app.localizedName ?? "Unknown App"
    return (mainWindowElement, appName)
}

func switchToApp(appName: String) -> Bool {
    let runningApps = NSWorkspace.shared.runningApplications

    // Find the app by name (case-insensitive)
    guard
        let targetApp = runningApps.first(where: { app in
            app.localizedName?.lowercased() == appName.lowercased()
        })
    else {
        return false
    }

    // Activate the app
    let success = targetApp.activate(options: .activateIgnoringOtherApps)
    return success
}

func getAvailableApps() -> [[String: Any]] {
    let runningApps = NSWorkspace.shared.runningApplications
    var apps: [[String: Any]] = []

    for app in runningApps {
        if let appName = app.localizedName {
            apps.append([
                "name": appName,
                "bundleIdentifier": app.bundleIdentifier ?? "Unknown",
                "processIdentifier": app.processIdentifier,
                "isActive": app.isActive,
            ])
        }
    }

    // Sort by name for easier browsing
    apps.sort { (app1, app2) in
        let name1 = app1["name"] as? String ?? ""
        let name2 = app2["name"] as? String ?? ""
        return name1.lowercased() < name2.lowercased()
    }

    return apps
}

func getElementAtLocation() -> ElementInfo {
    // For click events, we can use the current mouse location since it's at the click point
    // For manual coordinate lookup, we'd need proper window-to-screen conversion
    let screenLocation = NSEvent.mouseLocation

    // Get the element at the specified location
    var elementRef: AXUIElement?
    let result = AXUIElementCopyElementAtPosition(
        AXUIElementCreateSystemWide(),
        Float(screenLocation.x),
        Float(screenLocation.y),
        &elementRef
    )

    if result == .success, let element = elementRef {
        return getElementInfo(element: element)
    }

    // Return a default element info if we can't find the element
    return ElementInfo(
        index: nil,
        label: "Unknown",
        title: "Unknown",
        value: "None",
        type: "Unknown",
        text: nil,
        description: "Unknown",
        pressable: false,
        availableActions: [],
        hasMenu: false,
        menuItems: nil,
        identifier: "None"
    )
}

func getElementTextContent(element: AXUIElement, maxDepth: Int? = nil, currentDepth: Int = 0) -> (
    textContent: String, elementCount: Int
) {
    var textContent = ""
    var elementCount = 0

    // Check if we've reached the maximum depth
    if let maxDepth = maxDepth, currentDepth >= maxDepth {
        return (textContent, elementCount)
    }

    // Get current element's text content
    let elementInfo = getElementInfo(element: element)
    elementCount += 1

    // Create indentation based on depth
    let indent = String(repeating: "  ", count: currentDepth)

    // Collect and organize text from various sources
    var elementTexts: [String] = []
    var elementDetails: [String] = []

    // Add text content (highest priority)
    if let text = elementInfo.text, !text.isEmpty {
        elementTexts.append(text)
    }

    // Add title if different from text
    if !elementInfo.title.isEmpty && elementInfo.title != "None"
        && (elementInfo.text == nil || elementInfo.text != elementInfo.title)
    {
        elementTexts.append(elementInfo.title)
    }

    // Add label if different from text and title
    if !elementInfo.label.isEmpty && elementInfo.label != "None"
        && !elementTexts.contains(elementInfo.label)
    {
        elementTexts.append(elementInfo.label)
    }

    // Add value if different from other text
    if !elementInfo.value.isEmpty && elementInfo.value != "None"
        && !elementTexts.contains(elementInfo.value)
    {
        elementTexts.append(elementInfo.value)
    }

    // Add element type information for context
    if elementInfo.type != "AXWindow" && elementInfo.type != "AXGroup" {
        elementDetails.append("Type: \(elementInfo.type)")
    }

    // Add pressable information
    if elementInfo.pressable {
        elementDetails.append("Pressable")
    }

    // Add available actions if any
    if !elementInfo.availableActions.isEmpty {
        elementDetails.append("Actions: \(elementInfo.availableActions.joined(separator: ", "))")
    }

    // Add menu information
    if elementInfo.hasMenu, let menuItems = elementInfo.menuItems, !menuItems.isEmpty {
        let menuText = menuItems.map { "\($0.title)" }.joined(separator: ", ")
        elementDetails.append("Menu: \(menuText)")
    }

    // Format the element content
    if !elementTexts.isEmpty {
        // Join text with proper spacing
        let mainText = elementTexts.joined(separator: " ").trimmingCharacters(
            in: .whitespacesAndNewlines)
        if !mainText.isEmpty {
            textContent += "\(indent)• \(mainText)\n"
        }
    }

    // Add element details if any
    if !elementDetails.isEmpty {
        textContent += "\(indent)  (\(elementDetails.joined(separator: ", ")))\n"
    }

    // Recursively process children
    let children = getChildren(element: element)
    for child in children {
        let (childText, childCount) = getElementTextContent(
            element: child,
            maxDepth: maxDepth,
            currentDepth: currentDepth + 1
        )
        textContent += childText
        elementCount += childCount
    }

    return (textContent, elementCount)
}

// MARK: - Keystroke Functions
func sendKeystroke(_ key: String, modifiers: [String] = []) -> Bool {
    let keyCode = getKeyCode(for: key)
    var modifierFlags = getModifierFlags(for: modifiers)

    // Automatically add shift for symbols that require it
    let symbolsRequiringShift = [
        "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+", "{", "}", "|", ":", "\"", "<",
        ">", "?", "~",
    ]
    if symbolsRequiringShift.contains(key) {
        modifierFlags.insert(.maskShift)
    }

    // Press down
    let downEvent = CGEvent(keyboardEventSource: nil, virtualKey: keyCode, keyDown: true)
    downEvent?.flags = modifierFlags
    downEvent?.post(tap: .cghidEventTap)

    // Release
    let upEvent = CGEvent(keyboardEventSource: nil, virtualKey: keyCode, keyDown: false)
    upEvent?.flags = modifierFlags
    upEvent?.post(tap: .cghidEventTap)

    return true
}

func getKeyCode(for key: String) -> CGKeyCode {
    switch key.lowercased() {
    // Letters
    case "a": return 0x00
    case "b": return 0x0B
    case "c": return 0x08
    case "d": return 0x02
    case "e": return 0x0E
    case "f": return 0x03
    case "g": return 0x05
    case "h": return 0x04
    case "i": return 0x22
    case "j": return 0x26
    case "k": return 0x28
    case "l": return 0x25
    case "m": return 0x2E
    case "n": return 0x2D
    case "o": return 0x1F
    case "p": return 0x23
    case "q": return 0x0C
    case "r": return 0x0F
    case "s": return 0x01
    case "t": return 0x11
    case "u": return 0x20
    case "v": return 0x09
    case "w": return 0x0D
    case "x": return 0x07
    case "y": return 0x10
    case "z": return 0x06

    // Numbers

    // Special keys
    case "space": return 0x31
    case " ": return 0x31
    case "return": return 0x24
    case "enter": return 0x24
    case "tab": return 0x30
    case "escape": return 0x35
    case "esc": return 0x35
    case "delete": return 0x33
    case "backspace": return 0x33

    // Arrow keys
    case "up": return 0x7E
    case "down": return 0x7D
    case "left": return 0x7B
    case "right": return 0x7C

    // Navigation
    case "home": return 0x73
    case "end": return 0x77
    case "pageup": return 0x74
    case "pagedown": return 0x79

    // Function keys
    case "f1": return 0x3A
    case "f2": return 0x3B
    case "f3": return 0x3C
    case "f4": return 0x3D
    case "f5": return 0x3E
    case "f6": return 0x3F
    case "f7": return 0x40
    case "f8": return 0x41
    case "f9": return 0x42
    case "f10": return 0x43
    case "f11": return 0x44
    case "f12": return 0x45

    // Symbols and punctuation
    case "`", "~": return 0x32
    case "-", "_": return 0x1B
    case "=", "+": return 0x18
    case "[", "{": return 0x21
    case "]", "}": return 0x1E
    case "\\", "|": return 0x2A
    case ";", ":": return 0x29
    case "'", "\"": return 0x27
    case ",", "<": return 0x2B
    case ".", ">": return 0x2F
    case "/", "?": return 0x2C

    // Additional symbols
    case "!", "1": return 0x12  // Same as 1, but with shift
    case "@", "2": return 0x13  // Same as 2, but with shift
    case "#", "3": return 0x14  // Same as 3, but with shift
    case "$", "4": return 0x15  // Same as 4, but with shift
    case "%", "5": return 0x17  // Same as 5, but with shift
    case "^", "6": return 0x16  // Same as 6, but with shift
    case "&", "7": return 0x1A  // Same as 7, but with shift
    case "*", "8": return 0x1C  // Same as 8, but with shift
    case "(", "9": return 0x19  // Same as 9, but with shift
    case ")", "0": return 0x1D  // Same as 0, but with shift

    default: return 0x00
    }
}

func getModifierFlags(for modifiers: [String]) -> CGEventFlags {
    var flags: CGEventFlags = []

    for modifier in modifiers {
        switch modifier.lowercased() {
        case "cmd", "command": flags.insert(.maskCommand)
        case "ctrl", "control": flags.insert(.maskControl)
        case "alt", "option": flags.insert(.maskAlternate)
        case "shift": flags.insert(.maskShift)
        case "fn": flags.insert(.maskSecondaryFn)
        default: break
        }
    }

    return flags
}

func sendString(_ text: String) -> Bool {
    for character in text {
        let key: String

        // Handle special characters that need special treatment
        switch character {
        case "\n":
            key = "return"
        case "\t":
            key = "tab"
        case "\r":
            key = "return"
        default:
            key = String(character)
        }

        if !sendKeystroke(key) {
            return false
        }

        // Small delay between characters for natural typing
        Thread.sleep(forTimeInterval: 0.05)
    }

    return true
}

// MARK: - MCP Service
struct AccessibilityMCPService: Service {
    let server: Server
    let transport: Transport

    init(server: Server, transport: Transport) {
        self.server = server
        self.transport = transport
    }

    func run() async throws {
        try await server.start(transport: transport)
        try await Task.sleep(for: .seconds(365 * 24 * 60 * 60 * 100))  // Effectively forever
    }

    func shutdown() async throws {
        await server.stop()
    }
}

// MARK: - Tool Definitions
func createTools() -> [Tool] {
    return [
        Tool(
            name: "get_current_app",
            description:
                "Get information about the current frontmost application and its main window. Returns JSON object: {appName: string, index: number|null, label: string, title: string, value: string, type: string, text: string|null, description: string, pressable: boolean, availableActions: string[], hasMenu: boolean, menuItems: [{index: number, title: string}]|null}",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([:]),
            ])
        ),
        Tool(
            name: "get_element",
            description:
                "Get detailed information about an element at the specified path. Returns JSON object: {index: number|null, label: string, title: string, value: string, type: string, text: string|null, description: string, pressable: boolean, availableActions: string[], hasMenu: boolean, menuItems: [{index: number, title: string}]|null}",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([
                    "path": .object([
                        "type": .string("string"),
                        "description": .string(
                            "Descriptive path with element types and attributes (e.g., 'AXWindow[title=\"WindowTitle\"] > AXGroup > AXButton[title=\"Click Me\"]') or comma-separated indices (e.g., '0,1,2')"
                        ),
                    ])
                ]),
                "required": .array([.string("path")]),
            ])
        ),
        Tool(
            name: "get_children",
            description:
                "Get all children of an element at the specified path. Returns JSON array of objects: [{index: number, label: string, title: string, value: string, type: string, text: string|null, description: string, pressable: boolean, availableActions: string[], hasMenu: boolean, menuItems: [{index: number, title: string}]|null}]",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([
                    "path": .object([
                        "type": .string("string"),
                        "description": .string(
                            "Descriptive path with element types and attributes (e.g., 'AXWindow[title=\"WindowTitle\"] > AXGroup > AXButton[title=\"Click Me\"]') or comma-separated indices (e.g., '0,1,2')"
                        ),
                    ])
                ]),
                "required": .array([.string("path")]),
            ])
        ),
        Tool(
            name: "perform_action",
            description:
                "Perform an action on an element at the specified path. Returns JSON object: {success: boolean, message: string}",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([
                    "path": .object([
                        "type": .string("string"),
                        "description": .string(
                            "Descriptive path with element types and attributes (e.g., 'AXWindow[title=\"WindowTitle\"] > AXGroup > AXButton[title=\"Click Me\"]') or comma-separated indices (e.g., '0,1,2')"
                        ),
                    ]),
                    "action": .object([
                        "type": .string("string"),
                        "description": .string("Action to perform (e.g., 'AXPress', 'AXClick')"),
                    ]),
                ]),
                "required": .array([.string("path"), .string("action")]),
            ])
        ),
        Tool(
            name: "search_elements",
            description:
                "Search for elements whose title, label, value, or type contains the query string. Returns JSON array of objects: [{path: string, descriptivePath: string, semanticPath: string, element: {index: number|null, label: string, title: string, value: string, type: string, text: string|null, description: string, pressable: boolean, availableActions: string[], hasMenu: boolean, menuItems: [{index: number, title: string}]|null}}]",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([
                    "query": .object([
                        "type": .string("string"),
                        "description": .string("Search query (case-insensitive)"),
                    ]),
                    "path": .object([
                        "type": .string("string"),
                        "description": .string(
                            "Optional descriptive path with element types and attributes (e.g., 'AXWindow[title=\"WindowTitle\"] > AXGroup') or comma-separated indices (e.g., '0,1,2') to start search from"
                        ),
                    ]),
                ]),
                "required": .array([.string("query")]),
            ])
        ),
        Tool(
            name: "send_keystroke",
            description:
                "Send a single keystroke with optional modifiers. Returns JSON object: {success: boolean, message: string}",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([
                    "key": .object([
                        "type": .string("string"),
                        "description": .string("Key to press (e.g., 'a', 'space', 'c')"),
                    ]),
                    "modifiers": .object([
                        "type": .string("array"),
                        "items": .object([
                            "type": .string("string")
                        ]),
                        "description": .string("Modifier keys (e.g., ['cmd', 'shift'])"),
                    ]),
                ]),
                "required": .array([.string("key")]),
            ])
        ),
        Tool(
            name: "send_string",
            description:
                "Type out a string character by character. Returns JSON object: {success: boolean, message: string}",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([
                    "text": .object([
                        "type": .string("string"),
                        "description": .string("The string to type out"),
                    ])
                ]),
                "required": .array([.string("text")]),
            ])
        ),
        Tool(
            name: "switch_to_app",
            description:
                "Switch focus to a running application by name. Returns JSON object: {success: boolean, message: string}",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([
                    "app_name": .object([
                        "type": .string("string"),
                        "description": .string(
                            "Name of the application to switch to (e.g., 'Chrome', 'Safari', 'Terminal')"
                        ),
                    ])
                ]),
                "required": .array([.string("app_name")]),
            ])
        ),
        Tool(
            name: "list_available_apps",
            description:
                "List all running applications that can be switched to. Returns JSON array of objects: [{name: string, bundleIdentifier: string, processIdentifier: number, isActive: boolean}]",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([:]),
            ])
        ),
        Tool(
            name: "get_element_text_content",
            description:
                "Recursively traverse an element's children and collect all text content with improved formatting. Returns JSON object: {textContent: string, elementCount: number}. The textContent includes hierarchical structure with bullet points, indentation, element types, and interactive properties.",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([
                    "path": .object([
                        "type": .string("string"),
                        "description": .string(
                            "Descriptive path with element types and attributes (e.g., 'AXWindow[title=\"WindowTitle\"] > AXGroup') or comma-separated indices (e.g., '0,1,2'). If empty, uses the main window element."
                        ),
                    ]),
                    "maxDepth": .object([
                        "type": .string("number"),
                        "description": .string(
                            "Maximum recursion depth (optional, defaults to unlimited)"),
                    ]),
                ]),
                "required": .array([]),
            ])
        ),
        Tool(
            name: "get_captured_events",
            description:
                "Get all captured user events (clicks and keyboard presses) from the event queue. Returns JSON array of objects: [{timestamp: string, type: string, details: object}]",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([:]),
            ])
        ),
        Tool(
            name: "clear_captured_events",
            description:
                "Clear all captured events from the event queue. Returns JSON object: {success: boolean, message: string}",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([:]),
            ])
        ),
        Tool(
            name: "get_event_count",
            description:
                "Get the current number of captured events in the queue. Returns JSON object: {count: number}",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([:]),
            ])
        ),
        Tool(
            name: "start_event_monitoring",
            description:
                "Start monitoring for user events (clicks and keyboard presses). Returns JSON object: {success: boolean, message: string}",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([:]),
            ])
        ),
        Tool(
            name: "stop_event_monitoring",
            description:
                "Stop monitoring for user events. Returns JSON object: {success: boolean, message: string}",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([:]),
            ])
        ),
        Tool(
            name: "get_element_at_location",
            description:
                "Get information about the UI element at a specific screen location. Returns JSON object: {index: number|null, label: string, title: string, value: string, type: string, text: string|null, description: string, pressable: boolean, availableActions: string[], hasMenu: boolean, menuItems: [{index: number, title: string}]|null, identifier: string|null}",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([
                    "x": .object([
                        "type": .string("number"),
                        "description": .string("X coordinate on screen"),
                    ]),
                    "y": .object([
                        "type": .string("number"),
                        "description": .string("Y coordinate on screen"),
                    ]),
                ]),
                "required": .array([.string("x"), .string("y")]),
            ])
        ),
        Tool(
            name: "test_event_monitoring",
            description:
                "Test if event monitoring is working by checking current mouse position and element. Returns JSON object: {success: boolean, mouseLocation: {x: number, y: number}, elementInfo: object}",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([:]),
            ])
        ),

        Tool(
            name: "test_polling_server_connection",
            description:
                "Test the connection to the EventPollingApp HTTP server. Returns JSON object: {success: boolean, connected: boolean, eventCount: number, message: string}",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([:]),
            ])
        ),
        Tool(
            name: "generate_descriptive_path",
            description:
                "Generate a descriptive path to an element at the specified location or path. Returns JSON object: {path: string, success: boolean, message: string}",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([
                    "x": .object([
                        "type": .string("number"),
                        "description": .string(
                            "X coordinate on screen (optional, uses current mouse position if not provided)"
                        ),
                    ]),
                    "y": .object([
                        "type": .string("number"),
                        "description": .string(
                            "Y coordinate on screen (optional, uses current mouse position if not provided)"
                        ),
                    ]),
                    "path": .object([
                        "type": .string("string"),
                        "description": .string(
                            "Optional path to element (descriptive or index-based)"),
                    ]),
                ]),
                "required": .array([]),
            ])
        ),
        Tool(
            name: "get_app_element",
            description:
                "Get the main window element for a specific application by name or bundle identifier. Returns JSON object: {appName: string, index: number|null, label: string, title: string, value: string, type: string, text: string|null, description: string, pressable: boolean, availableActions: string[], hasMenu: boolean, menuItems: [{index: number, title: string}]|null}",
            inputSchema: .object([
                "type": .string("object"),
                "properties": .object([
                    "app_name": .object([
                        "type": .string("string"),
                        "description": .string(
                            "Name of the application (e.g., 'Chrome', 'Safari', 'Terminal'). If not provided, uses the frontmost app."
                        ),
                    ]),
                    "bundle_id": .object([
                        "type": .string("string"),
                        "description": .string(
                            "Bundle identifier of the application (e.g., 'com.google.Chrome', 'com.apple.Safari'). If not provided, uses app_name or frontmost app."
                        ),
                    ]),
                ]),
                "required": .array([]),
            ])
        ),
    ]
}

// MARK: - Main
@main
struct AccessibilityMCPServer {
    static func main() async throws {
        // Initialize the application
        let app = NSApplication.shared
        app.setActivationPolicy(.accessory)

        // Configure logging
        LoggingSystem.bootstrap { label in
            var handler = StreamLogHandler.standardError(label: label)
            handler.logLevel = .info
            return handler
        }

        let logger = Logger(label: "com.sisypho.accessibility-mcp")

        // Create the MCP server
        let server = Server(
            name: "macOS Accessibility Server",
            version: "1.0.0",
            capabilities: .init(
                tools: .init(listChanged: true)
            )
        )

        // Check accessibility permissions at startup
        let trusted = AXIsProcessTrusted()

        if !trusted {
            logger.error(
                "Accessibility permissions not granted. Please enable accessibility access for this app in System Preferences > Security & Privacy > Privacy > Accessibility"
            )
            print(
                "ERROR: Accessibility permissions not granted. Please enable accessibility access for this app in System Preferences > Security & Privacy > Privacy > Accessibility"
            )
        } else {
            logger.info("Accessibility permissions granted")
        }

        // Start event monitoring
        globalEventMonitor.startMonitoring()
        logger.info("Event monitoring started")
        logger.info("DEBUG: Event monitoring started in main function")
        logger.info(
            "DEBUG: Accessibility permissions status: \(AXIsProcessTrusted() ? "Granted" : "Not granted")"
        )

        // Add some debug logging to verify monitoring is working
        logger.info("Event monitoring initialized")

        // Add tool handlers
        await server.withMethodHandler(ListTools.self) { _ in
            return ListTools.Result(tools: createTools())
        }

        logger.info("added tool handlers")

        await server.withMethodHandler(CallTool.self) { params in
            // Add 5 second delay before every tool execution
            try? await Task.sleep(for: .milliseconds(50))

            switch params.name {
            case "get_current_app":
                guard let (mainWindowElement, appName) = getFrontmostAppElement() else {
                    let errorMessage =
                        "No frontmost app found or accessibility permissions not granted"
                    let result = ["success": false, "message": errorMessage]
                    let jsonData = try! JSONSerialization.data(
                        withJSONObject: result, options: [.prettyPrinted])
                    let jsonString = String(data: jsonData, encoding: .utf8)!
                    return CallTool.Result(content: [.text(jsonString)], isError: true)
                }
                let elementInfo = getElementInfo(element: mainWindowElement)
                let encoder = JSONEncoder()
                encoder.outputFormatting = .prettyPrinted
                let jsonData = try! encoder.encode(elementInfo)
                var jsonObject = try! JSONSerialization.jsonObject(with: jsonData) as! [String: Any]
                jsonObject["appName"] = appName
                let updatedJsonData = try! JSONSerialization.data(withJSONObject: jsonObject)
                let jsonString = String(data: updatedJsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)])

            case "get_element":
                guard let (mainWindowElement, _) = getFrontmostAppElement() else {
                    let errorMessage =
                        "No frontmost app found or accessibility permissions not granted"
                    let result = ["success": false, "message": errorMessage]
                    let jsonData = try! JSONSerialization.data(
                        withJSONObject: result, options: [.prettyPrinted])
                    let jsonString = String(data: jsonData, encoding: .utf8)!
                    return CallTool.Result(content: [.text(jsonString)], isError: true)
                }
                let pathString = params.arguments?["path"]?.stringValue ?? ""
                let targetElement: AXUIElement
                if pathString.isEmpty {
                    targetElement = mainWindowElement
                } else {
                    print("navigateToElementWithPath get_element")
                    guard
                        let element = navigateToElementWithPath(
                            startElement: mainWindowElement, pathString: pathString)
                    else {
                        let result = [
                            "success": false,
                            "message": "harish 1 Invalid path: \(pathString)",
                        ]
                        let jsonData = try! JSONSerialization.data(
                            withJSONObject: result, options: [.prettyPrinted])
                        let jsonString = String(data: jsonData, encoding: .utf8)!
                        return CallTool.Result(content: [.text(jsonString)], isError: true)
                    }
                    targetElement = element
                }
                let elementInfo = getElementInfo(element: targetElement)
                let encoder = JSONEncoder()
                encoder.outputFormatting = .prettyPrinted
                let jsonData = try! encoder.encode(elementInfo)
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)])

            case "get_children":
                guard let (mainWindowElement, _) = getFrontmostAppElement() else {
                    let errorMessage =
                        "No frontmost app found or accessibility permissions not granted"
                    let result = ["success": false, "message": errorMessage]
                    let jsonData = try! JSONSerialization.data(
                        withJSONObject: result, options: [.prettyPrinted])
                    let jsonString = String(data: jsonData, encoding: .utf8)!
                    return CallTool.Result(content: [.text(jsonString)], isError: true)
                }
                let pathString = params.arguments?["path"]?.stringValue ?? ""
                let targetElement: AXUIElement
                if pathString.isEmpty {
                    targetElement = mainWindowElement
                } else {
                    fputs("navigateToElementWithPath get_children", stderr)
                    guard
                        let element = navigateToElementWithPath(
                            startElement: mainWindowElement, pathString: pathString)
                    else {
                        let result = [
                            "success": false,
                            "message": "harish 2 Invalid path: \(pathString)",
                        ]
                        let jsonData = try! JSONSerialization.data(
                            withJSONObject: result, options: [.prettyPrinted])
                        let jsonString = String(data: jsonData, encoding: .utf8)!
                        return CallTool.Result(content: [.text(jsonString)], isError: true)
                    }
                    targetElement = element
                }
                let children = getChildren(element: targetElement)
                let childrenInfo = children.enumerated().map { index, child in
                    getElementInfo(element: child, index: index)
                }
                let encoder = JSONEncoder()
                encoder.outputFormatting = .prettyPrinted
                let jsonData = try! encoder.encode(childrenInfo)
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)])

            case "perform_action":
                fputs("going to get app element", stderr)
                guard
                    let (mainWindowElement, appName) = getAppElement(
                        appName: params.arguments?["app_name"]?.stringValue,
                        bundleId: params.arguments?["bundle_id"]?.stringValue)
                else {
                    let errorMessage =
                        "No frontmost app found or accessibility permissions not granted"
                    let result = ["success": false, "message": errorMessage]
                    let jsonData = try! JSONSerialization.data(
                        withJSONObject: result, options: [.prettyPrinted])
                    let jsonString = String(data: jsonData, encoding: .utf8)!
                    return CallTool.Result(content: [.text(jsonString)], isError: true)
                }
                let pathString = params.arguments?["path"]?.stringValue ?? ""
                let action = params.arguments?["action"]?.stringValue ?? ""
                let targetElement: AXUIElement
                if pathString.isEmpty {
                    targetElement = mainWindowElement
                } else {
                    fputs("navigateToElementWithPath perform action", stderr)
                    guard
                        let element = navigateToElementWithPath(
                            startElement: mainWindowElement, pathString: pathString)
                    else {
                        let result = [
                            "success": false,
                            "message": "harish 3 Invalid path: \(pathString)\n\(appName)",
                        ]
                        let jsonData = try! JSONSerialization.data(
                            withJSONObject: result, options: [.prettyPrinted])
                        let jsonString = String(data: jsonData, encoding: .utf8)!
                        return CallTool.Result(content: [.text(jsonString)], isError: true)
                    }
                    targetElement = element
                }
                let success = performAction(element: targetElement, actionName: action)
                let message = success ? "Action performed successfully" : "Failed to perform action"
                let result = ["success": success, "message": message]
                let jsonData = try! JSONSerialization.data(
                    withJSONObject: result, options: [.prettyPrinted])
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)], isError: !success)

            case "search_elements":
                guard let (mainWindowElement, _) = getFrontmostAppElement() else {
                    let errorMessage =
                        "No frontmost app found or accessibility permissions not granted"
                    let result = ["success": false, "message": errorMessage]
                    let jsonData = try! JSONSerialization.data(
                        withJSONObject: result, options: [.prettyPrinted])
                    let jsonString = String(data: jsonData, encoding: .utf8)!
                    return CallTool.Result(content: [.text(jsonString)], isError: true)
                }
                let query = params.arguments?["query"]?.stringValue ?? ""
                let pathString = params.arguments?["path"]?.stringValue ?? ""
                var currentElement = mainWindowElement
                var currentPath: [Int] = []
                if !pathString.isEmpty {
                    fputs("navigateToElementWithPath search_elements", stderr)
                    guard
                        let element = navigateToElementWithPath(
                            startElement: mainWindowElement, pathString: pathString)
                    else {
                        let result = [
                            "success": false,
                            "message": "harish 4 Invalid path: \(pathString)",
                        ]
                        let jsonData = try! JSONSerialization.data(
                            withJSONObject: result, options: [.prettyPrinted])
                        let jsonString = String(data: jsonData, encoding: .utf8)!
                        return CallTool.Result(content: [.text(jsonString)], isError: true)
                    }
                    currentElement = element

                    // For backward compatibility, try to build a numeric path if possible
                    if !isDescriptivePath(pathString) {
                        let pathComponents = pathString.split(separator: ",").map(String.init)
                        for comp in pathComponents {
                            if let idx = Int(comp) {
                                currentPath.append(idx)
                            }
                        }
                    }
                }

                func searchElements(
                    element: AXUIElement, query: String, currentPath: [Int],
                    currentSemanticPath: [String],
                    results: inout [[String: Any]]
                ) {
                    let info = getElementInfo(element: element)
                    let q = query.lowercased()
                    let title = info.title.lowercased()
                    let label = info.label.lowercased()
                    let value = info.value.lowercased()
                    let type = info.type.lowercased()
                    if title.contains(q) || label.contains(q) || value.contains(q)
                        || type.contains(q)
                    {
                        let encoder = JSONEncoder()
                        encoder.outputFormatting = .prettyPrinted
                        if let data = try? encoder.encode(info),
                            let dict = try? JSONSerialization.jsonObject(with: data)
                                as? [String: Any]
                        {
                            // Generate descriptive path for this element
                            let descriptivePath = generateDescriptivePath(
                                to: element, from: mainWindowElement)

                            results.append([
                                "path": currentPath.map { String($0) }.joined(separator: ","),
                                "descriptivePath": descriptivePath,
                                "semanticPath": currentSemanticPath.joined(separator: " > "),
                                "element": dict,
                            ])
                        }
                    }
                    let children = getChildren(element: element)
                    for (idx, child) in children.enumerated() {
                        var nextPath = currentPath
                        nextPath.append(idx)
                        var nextSemanticPath = currentSemanticPath
                        // Create semantic path component from title, label, value, and type
                        let semanticComponent =
                            [info.title, info.label, info.value, info.type]
                            .filter { !$0.isEmpty && $0 != "None" }
                            .first ?? "element"
                        nextSemanticPath.append(semanticComponent)
                        searchElements(
                            element: child, query: query, currentPath: nextPath,
                            currentSemanticPath: nextSemanticPath, results: &results)
                    }
                }

                var results: [[String: Any]] = []
                searchElements(
                    element: currentElement, query: query, currentPath: currentPath,
                    currentSemanticPath: [],
                    results: &results)
                results.sort { (a, b) in
                    let pathA = a["path"] as? String ?? ""
                    let pathB = b["path"] as? String ?? ""
                    let countA = pathA.isEmpty ? 0 : pathA.components(separatedBy: ",").count
                    let countB = pathB.isEmpty ? 0 : pathB.components(separatedBy: ",").count
                    return countA < countB
                }
                let jsonData = try! JSONSerialization.data(
                    withJSONObject: results, options: [.prettyPrinted])
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)])

            case "send_keystroke":
                let key = params.arguments?["key"]?.stringValue ?? ""
                let modifiers =
                    params.arguments?["modifiers"]?.arrayValue?.compactMap { $0.stringValue } ?? []
                let success = sendKeystroke(key, modifiers: modifiers)
                let message = success ? "Keystroke sent successfully" : "Failed to send keystroke"
                let result = ["success": success, "message": message]
                let jsonData = try! JSONSerialization.data(
                    withJSONObject: result, options: [.prettyPrinted])
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)], isError: !success)

            case "send_string":
                let text = params.arguments?["text"]?.stringValue ?? ""
                let success = sendString(text)
                let message = success ? "String typed successfully" : "Failed to type string"
                let result = ["success": success, "message": message]
                let jsonData = try! JSONSerialization.data(
                    withJSONObject: result, options: [.prettyPrinted])
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)], isError: !success)

            case "switch_to_app":
                let appName = params.arguments?["app_name"]?.stringValue ?? ""
                let success = switchToApp(appName: appName)
                let message =
                    success
                    ? "Successfully switched to \(appName)"
                    : "Failed to switch to \(appName) (app may not be running, or app name may be wrong. check using the list_available_apps tool)"
                let result = ["success": success, "message": message]
                let jsonData = try! JSONSerialization.data(
                    withJSONObject: result, options: [.prettyPrinted])
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)], isError: !success)

            case "list_available_apps":
                let apps = getAvailableApps()
                let jsonData = try! JSONSerialization.data(
                    withJSONObject: apps, options: [.prettyPrinted])
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)])

            case "get_element_text_content":
                guard let (mainWindowElement, _) = getFrontmostAppElement() else {
                    let errorMessage =
                        "No frontmost app found or accessibility permissions not granted"
                    let result = ["success": false, "message": errorMessage]
                    let jsonData = try! JSONSerialization.data(
                        withJSONObject: result, options: [.prettyPrinted])
                    let jsonString = String(data: jsonData, encoding: .utf8)!
                    return CallTool.Result(content: [.text(jsonString)], isError: true)
                }

                let pathString = params.arguments?["path"]?.stringValue ?? ""
                let maxDepth = params.arguments?["maxDepth"]?.intValue

                let targetElement: AXUIElement
                if pathString.isEmpty {
                    targetElement = mainWindowElement
                } else {
                    fputs("navigateToElementWithPath get_element_text_content", stderr)
                    guard
                        let element = navigateToElementWithPath(
                            startElement: mainWindowElement, pathString: pathString)
                    else {
                        let result = [
                            "success": false,
                            "message": "harish 5 Invalid path: \(pathString)",
                        ]
                        let jsonData = try! JSONSerialization.data(
                            withJSONObject: result, options: [.prettyPrinted])
                        let jsonString = String(data: jsonData, encoding: .utf8)!
                        return CallTool.Result(content: [.text(jsonString)], isError: true)
                    }
                    targetElement = element
                }

                let (textContent, elementCount) = getElementTextContent(
                    element: targetElement,
                    maxDepth: maxDepth
                )

                let result = [
                    "textContent": textContent.trimmingCharacters(in: .whitespacesAndNewlines),
                    "elementCount": elementCount,
                ]
                let jsonData = try! JSONSerialization.data(
                    withJSONObject: result, options: [.prettyPrinted])
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)])

            case "get_captured_events":
                // Get events from polling server
                if let events = getEventsFromPollingServer() {
                    let encoder = JSONEncoder()
                    encoder.dateEncodingStrategy = .iso8601
                    encoder.outputFormatting = .prettyPrinted
                    let jsonData = try! encoder.encode(events)
                    let jsonString = String(data: jsonData, encoding: .utf8)!
                    return CallTool.Result(content: [.text(jsonString)])
                } else {
                    // No events available from polling server
                    let result = [
                        "success": false,
                        "message":
                            "No events available from EventPollingApp. Make sure it's running on port 8080.",
                    ]
                    let jsonData = try! JSONSerialization.data(
                        withJSONObject: result, options: [.prettyPrinted])
                    let jsonString = String(data: jsonData, encoding: .utf8)!
                    return CallTool.Result(content: [.text(jsonString)], isError: true)
                }

            case "clear_captured_events":
                // Clear events from polling server
                let pollingSuccess = clearEventsFromPollingServer()
                let result = [
                    "success": pollingSuccess,
                    "message": pollingSuccess
                        ? "All captured events cleared from EventPollingApp"
                        : "Failed to clear events from EventPollingApp. Make sure it's running on port 8080."
                        ,
                ]
                let jsonData = try! JSONSerialization.data(
                    withJSONObject: result, options: [.prettyPrinted])
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)], isError: !pollingSuccess)

            case "get_event_count":
                // Get count from polling server
                if let count = getEventCountFromPollingServer() {
                    let result = ["count": count]
                    let jsonData = try! JSONSerialization.data(
                        withJSONObject: result, options: [.prettyPrinted])
                    let jsonString = String(data: jsonData, encoding: .utf8)!
                    return CallTool.Result(content: [.text(jsonString)])
                } else {
                    // No count available from polling server
                    let result = [
                        "success": false,
                        "message":
                            "No event count available from EventPollingApp. Make sure it's running on port 8080.",
                    ]
                    let jsonData = try! JSONSerialization.data(
                        withJSONObject: result, options: [.prettyPrinted])
                    let jsonString = String(data: jsonData, encoding: .utf8)!
                    return CallTool.Result(content: [.text(jsonString)], isError: true)
                }

            case "start_event_monitoring":
                globalEventMonitor.startMonitoring()
                let result = ["success": true, "message": "Event monitoring started"]
                let jsonData = try! JSONSerialization.data(
                    withJSONObject: result, options: [.prettyPrinted])
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)])

            case "stop_event_monitoring":
                globalEventMonitor.stopMonitoring()
                let result = ["success": true, "message": "Event monitoring stopped"]
                let jsonData = try! JSONSerialization.data(
                    withJSONObject: result, options: [.prettyPrinted])
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)])

            case "get_element_at_location":
                // using the current mouse location instead of click coordinates
                let elementInfo = getElementAtLocation()

                let encoder = JSONEncoder()
                encoder.outputFormatting = .prettyPrinted
                let jsonData = try! encoder.encode(elementInfo)
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)])

            case "test_event_monitoring":
                let mouseLocation = NSEvent.mouseLocation
                let elementInfo = getElementAtLocation()

                // Test polling server connection
                let pollingEventCount = getEventCountFromPollingServer()
                let pollingEvents = getEventsFromPollingServer()

                let result = [
                    "success": true,
                    "mouseLocation": [
                        "x": mouseLocation.x,
                        "y": mouseLocation.y,
                    ],
                    "elementInfo": [
                        "type": elementInfo.type,
                        "title": elementInfo.title,
                        "label": elementInfo.label,
                        "pressable": elementInfo.pressable,
                    ],
                    "localEventCount": 0,
                    "pollingServerEventCount": pollingEventCount,
                    "pollingServerConnected": pollingEventCount != nil,
                    "pollingServerEvents": pollingEvents?.count ?? 0,
                    "accessibilityGranted": AXIsProcessTrusted(),
                ]

                let jsonData = try! JSONSerialization.data(
                    withJSONObject: result, options: [.prettyPrinted])
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)])

            case "test_polling_server_connection":
                let eventCount = getEventCountFromPollingServer()
                let connected = eventCount != nil
                let message =
                    connected
                    ? "Successfully connected to EventPollingApp HTTP server"
                    : "Failed to connect to EventPollingApp HTTP server. Make sure the app is running on port 8080"
                let result = [
                    "success": true,
                    "connected": connected,
                    "eventCount": eventCount ?? 0,
                    "message": message,
                ]
                let jsonData = try! JSONSerialization.data(
                    withJSONObject: result, options: [.prettyPrinted])
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)])

            case "get_app_element":
                let appName = params.arguments?["app_name"]?.stringValue
                let bundleId = params.arguments?["bundle_id"]?.stringValue

                guard
                    let (mainWindowElement, appName) = getAppElement(
                        appName: appName, bundleId: bundleId)
                else {
                    let errorMessage: String
                    if let appName = appName {
                        errorMessage =
                            "App '\(appName)' not found or accessibility permissions not granted"
                    } else if let bundleId = bundleId {
                        errorMessage =
                            "App with bundle ID '\(bundleId)' not found or accessibility permissions not granted"
                    } else {
                        errorMessage =
                            "No frontmost app found or accessibility permissions not granted"
                    }
                    let result = ["success": false, "message": errorMessage]
                    let jsonData = try! JSONSerialization.data(
                        withJSONObject: result, options: [.prettyPrinted])
                    let jsonString = String(data: jsonData, encoding: .utf8)!
                    return CallTool.Result(content: [.text(jsonString)], isError: true)
                }

                let elementInfo = getElementInfo(element: mainWindowElement)
                let encoder = JSONEncoder()
                encoder.outputFormatting = .prettyPrinted
                let jsonData = try! encoder.encode(elementInfo)
                var jsonObject = try! JSONSerialization.jsonObject(with: jsonData) as! [String: Any]
                jsonObject["appName"] = appName
                let updatedJsonData = try! JSONSerialization.data(withJSONObject: jsonObject)
                let jsonString = String(data: updatedJsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)])

            case "generate_descriptive_path":
                guard let (mainWindowElement, _) = getFrontmostAppElement() else {
                    let errorMessage =
                        "No frontmost app found or accessibility permissions not granted"
                    let result = ["success": false, "message": errorMessage]
                    let jsonData = try! JSONSerialization.data(
                        withJSONObject: result, options: [.prettyPrinted])
                    let jsonString = String(data: jsonData, encoding: .utf8)!
                    return CallTool.Result(content: [.text(jsonString)], isError: true)
                }

                let x = params.arguments?["x"]?.doubleValue
                let y = params.arguments?["y"]?.doubleValue
                let pathString = params.arguments?["path"]?.stringValue ?? ""

                let targetElement: AXUIElement
                if !pathString.isEmpty {
                    // Use provided path
                    fputs("navigateToElementWithPath generate_descriptive_path", stderr)
                    guard
                        let element = navigateToElementWithPath(
                            startElement: mainWindowElement, pathString: pathString)
                    else {
                        let result = [
                            "success": false,
                            "message": "harish 6 Invalid path: \(pathString)",
                        ]
                        let jsonData = try! JSONSerialization.data(
                            withJSONObject: result, options: [.prettyPrinted])
                        let jsonString = String(data: jsonData, encoding: .utf8)!
                        return CallTool.Result(content: [.text(jsonString)], isError: true)
                    }
                    targetElement = element
                } else if let x = x, let y = y {
                    // Use provided coordinates
                    var elementRef: AXUIElement?
                    let result = AXUIElementCopyElementAtPosition(
                        AXUIElementCreateSystemWide(),
                        Float(x),
                        Float(y),
                        &elementRef
                    )

                    if result == .success, let element = elementRef {
                        targetElement = element
                    } else {
                        let result = [
                            "success": false,
                            "message": "No element found at specified coordinates",
                        ]
                        let jsonData = try! JSONSerialization.data(
                            withJSONObject: result, options: [.prettyPrinted])
                        let jsonString = String(data: jsonData, encoding: .utf8)!
                        return CallTool.Result(content: [.text(jsonString)], isError: true)
                    }
                } else {
                    // Use current mouse position
                    let elementInfo = getElementAtLocation()
                    var elementRef: AXUIElement?
                    let result = AXUIElementCopyElementAtPosition(
                        AXUIElementCreateSystemWide(),
                        Float(NSEvent.mouseLocation.x),
                        Float(NSEvent.mouseLocation.y),
                        &elementRef
                    )

                    if result == .success, let element = elementRef {
                        targetElement = element
                    } else {
                        let result = [
                            "success": false,
                            "message": "No element found at current mouse position",
                        ]
                        let jsonData = try! JSONSerialization.data(
                            withJSONObject: result, options: [.prettyPrinted])
                        let jsonString = String(data: jsonData, encoding: .utf8)!
                        return CallTool.Result(content: [.text(jsonString)], isError: true)
                    }
                }

                let descriptivePath = generateDescriptivePath(
                    to: targetElement, from: mainWindowElement)
                let result = [
                    "success": true,
                    "path": descriptivePath,
                    "message": "Descriptive path generated successfully",
                ]
                let jsonData = try! JSONSerialization.data(
                    withJSONObject: result, options: [.prettyPrinted])
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)])

            default:
                let result = ["success": false, "message": "Unknown tool: \(params.name)"]
                let jsonData = try! JSONSerialization.data(
                    withJSONObject: result, options: [.prettyPrinted])
                let jsonString = String(data: jsonData, encoding: .utf8)!
                return CallTool.Result(content: [.text(jsonString)], isError: true)
            }
        }

        // Create transport and service
        let transport = StdioTransport(logger: logger)
        let mcpService = AccessibilityMCPService(server: server, transport: transport)

        // Create service group with signal handling
        let serviceGroup = ServiceGroup(
            services: [mcpService],
            gracefulShutdownSignals: [.sigterm, .sigint],
            cancellationSignals: [],
            logger: logger
        )

        // Run the service group
        try await serviceGroup.run()
    }
}

// MARK: - Path Generation and Parsing
struct PathComponent {
    let type: String
    let attributes: [String: String]
    let index: Int?

    init(type: String, attributes: [String: String] = [:], index: Int? = nil) {
        self.type = type
        self.attributes = attributes
        self.index = index
    }

    func toString() -> String {
        var result = type

        // Create a dictionary with all attributes and index
        var jsonDict: [String: Any] = [:]

        // Add attributes
        for (key, value) in attributes {
            jsonDict[key] = value
        }

        // Add index if present
        if let index = index {
            jsonDict["index"] = index
        }

        // Convert to JSON string
        if let jsonData = try? JSONSerialization.data(withJSONObject: jsonDict),
            let jsonString = String(data: jsonData, encoding: .utf8)
        {
            result += "[\(jsonString)]"
        } else {
            // Fallback to simple format if JSON serialization fails
            var attrStrings: [String] = []
            for (key, value) in attributes {
                attrStrings.append("\"\(key)\": \"\(value)\"")
            }
            if let index = index {
                attrStrings.append("\"index\": \(index)")
            }
            result += "[{\(attrStrings.joined(separator: ", "))}]"
        }

        return result
    }

    static func parse(_ string: String) -> PathComponent? {
        // Extract type (everything before the first bracket)
        guard let bracketIndex = string.firstIndex(of: "[") else {
            // No attributes or index, just type
            return PathComponent(type: string)
        }

        let type = String(string[..<bracketIndex])
        let bracketContent = String(string[string.index(after: bracketIndex)...])

        // Remove closing bracket
        guard bracketContent.hasSuffix("]") else { return nil }
        let content = String(
            bracketContent[..<bracketContent.index(before: bracketContent.endIndex)])

        var attributes: [String: String] = [:]
        var index: Int? = nil

        // Try to parse as JSON first
        if content.hasPrefix("{") && content.hasSuffix("}") {
            do {
                if let jsonData = content.data(using: .utf8),
                    let jsonDict = try JSONSerialization.jsonObject(with: jsonData)
                        as? [String: Any]
                {

                    // Extract attributes
                    for (key, value) in jsonDict {
                        if key == "index" {
                            if let intValue = value as? Int {
                                index = intValue
                            } else if let stringValue = value as? String,
                                let intValue = Int(stringValue)
                            {
                                index = intValue
                            }
                        } else {
                            attributes[key] = String(describing: value)
                        }
                    }

                    return PathComponent(type: type, attributes: attributes, index: index)
                }
            } catch {
                // If JSON parsing fails, fall back to the old parsing method
                print("JSON parsing failed for path component: \(content), error: \(error)")
            }
        }

        // Fallback to old parsing method for backward compatibility
        var currentIndex = content.startIndex
        while currentIndex < content.endIndex {
            // Skip whitespace
            while currentIndex < content.endIndex && content[currentIndex].isWhitespace {
                currentIndex = content.index(after: currentIndex)
            }

            if currentIndex >= content.endIndex { break }

            // Check if this is an index attribute
            if content[currentIndex...].hasPrefix("index=") {
                let indexStart = content.index(currentIndex, offsetBy: 6)
                var indexEnd = indexStart
                while indexEnd < content.endIndex && content[indexEnd].isNumber {
                    indexEnd = content.index(after: indexEnd)
                }
                let indexStr = String(content[indexStart..<indexEnd])
                index = Int(indexStr)
                currentIndex = indexEnd

                // Skip to next attribute if there's a comma
                if currentIndex < content.endIndex && content[currentIndex] == "," {
                    currentIndex = content.index(after: currentIndex)
                }
                continue
            }

            // Parse key-value attribute
            guard let equalsIndex = content[currentIndex...].firstIndex(of: "=") else { break }
            let key = String(content[currentIndex..<equalsIndex]).trimmingCharacters(
                in: .whitespaces)
            currentIndex = content.index(after: equalsIndex)

            // Parse value (handle quoted strings properly)
            var value: String
            if currentIndex < content.endIndex && content[currentIndex] == "\"" {
                // Quoted string
                currentIndex = content.index(after: currentIndex)  // Skip opening quote
                var valueStart = currentIndex
                var valueEnd = currentIndex

                // Find the closing quote
                while valueEnd < content.endIndex {
                    if content[valueEnd] == "\"" {
                        // Check if it's escaped
                        if valueEnd > content.startIndex
                            && content[content.index(before: valueEnd)] == "\\"
                        {
                            valueEnd = content.index(after: valueEnd)
                            continue
                        }
                        break
                    }
                    valueEnd = content.index(after: valueEnd)
                }

                if valueEnd >= content.endIndex {
                    // No closing quote found
                    return nil
                }

                value = String(content[valueStart..<valueEnd])
                currentIndex = content.index(after: valueEnd)  // Skip closing quote
            } else {
                // Unquoted value - read until comma or end
                var valueStart = currentIndex
                var valueEnd = currentIndex

                while valueEnd < content.endIndex && content[valueEnd] != "," {
                    valueEnd = content.index(after: valueEnd)
                }

                value = String(content[valueStart..<valueEnd]).trimmingCharacters(in: .whitespaces)
                currentIndex = valueEnd
            }

            attributes[key] = value

            // Skip to next attribute if there's a comma
            if currentIndex < content.endIndex && content[currentIndex] == "," {
                currentIndex = content.index(after: currentIndex)
            }
        }

        return PathComponent(type: type, attributes: attributes, index: index)
    }
}

// MARK: - Type Compatibility Functions
func areTypesCompatible(expectedType: String, actualType: String) -> Bool {
    // Exact match
    if expectedType == actualType {
        return true
    }

    // Define type compatibility groups
    let buttonTypes = ["AXButton", "AXPopUpButton", "AXMenuButton", "AXToggleButton"]
    let textTypes = ["AXTextField", "AXTextArea", "AXStaticText", "AXText"]
    let groupTypes = ["AXGroup", "AXScrollArea", "AXSplitGroup", "AXTabGroup"]
    let listTypes = ["AXList", "AXOutline", "AXTable"]
    let menuTypes = ["AXMenu", "AXMenuBar", "AXMenuBarItem", "AXMenuItem"]
    let windowTypes = ["AXWindow", "AXDialog", "AXSheet", "AXDrawer"]
    let imageTypes = ["AXImage", "AXIcon"]
    let progressTypes = ["AXProgressIndicator", "AXSlider"]

    // Check if both types are in the same compatibility group
    let typeGroups = [
        buttonTypes,
        textTypes,
        groupTypes,
        listTypes,
        menuTypes,
        windowTypes,
        imageTypes,
        progressTypes,
    ]

    for group in typeGroups {
        if group.contains(expectedType) && group.contains(actualType) {
            return true
        }
    }

    // Special cases for common substitutions
    let specialCompatibility: [String: [String]] = [
        "AXButton": ["AXPopUpButton", "AXMenuButton", "AXToggleButton"],
        "AXPopUpButton": ["AXButton", "AXMenuButton"],
        "AXTextField": ["AXTextArea", "AXStaticText"],
        "AXTextArea": ["AXTextField", "AXStaticText"],
        "AXGroup": ["AXScrollArea", "AXSplitGroup"],
        "AXWindow": ["AXDialog", "AXSheet"],
        "AXList": ["AXOutline", "AXTable"],
        "AXImage": ["AXIcon"],
        "AXIcon": ["AXImage"],
    ]

    if let compatibleTypes = specialCompatibility[expectedType] {
        return compatibleTypes.contains(actualType)
    }

    if let compatibleTypes = specialCompatibility[actualType] {
        return compatibleTypes.contains(expectedType)
    }

    return false
}

func getTypeCompatibilityScore(expectedType: String, actualType: String) -> Int {
    // Higher score means better compatibility
    if expectedType == actualType {
        return 100  // Perfect match
    }

    // Define compatibility scores for different type relationships
    let highCompatibility: [String: [String]] = [
        "AXButton": ["AXPopUpButton", "AXMenuButton", "AXToggleButton"],
        "AXPopUpButton": ["AXButton", "AXMenuButton"],
        "AXTextField": ["AXTextArea"],
        "AXTextArea": ["AXTextField"],
        "AXGroup": ["AXScrollArea", "AXSplitGroup", "AXLandmarkMain"],
        "AXWindow": ["AXDialog", "AXSheet"],
        "AXList": ["AXOutline", "AXTable"],
    ]

    if let compatibleTypes = highCompatibility[expectedType], compatibleTypes.contains(actualType) {
        return 80  // High compatibility
    }

    if let compatibleTypes = highCompatibility[actualType], compatibleTypes.contains(expectedType) {
        return 80  // High compatibility
    }

    // Medium compatibility for broader groups
    let buttonTypes = ["AXButton", "AXPopUpButton", "AXMenuButton", "AXToggleButton"]
    let textTypes = ["AXTextField", "AXTextArea", "AXStaticText", "AXText"]
    let groupTypes = ["AXGroup", "AXScrollArea", "AXSplitGroup", "AXTabGroup"]

    if buttonTypes.contains(expectedType) && buttonTypes.contains(actualType) {
        return 60
    }
    if textTypes.contains(expectedType) && textTypes.contains(actualType) {
        return 60
    }
    if groupTypes.contains(expectedType) && groupTypes.contains(actualType) {
        return 60
    }

    return 0  // No compatibility
}

func generateDescriptivePath(to element: AXUIElement, from startElement: AXUIElement) -> String {
    var pathComponents: [PathComponent] = []
    var currentElement = startElement

    // Use depth-first search to find the path to the target element
    func findPathToElement(from: AXUIElement, target: AXUIElement, currentPath: [PathComponent])
        -> [PathComponent]?
    {
        if from == target {
            return currentPath
        }

        let children = getChildren(element: from)
        for (index, child) in children.enumerated() {
            let childInfo = getElementInfo(element: child)

            // Create attributes for the path component
            var attributes: [String: String] = [:]
            if !childInfo.title.isEmpty && childInfo.title != "None" {
                attributes["title"] = childInfo.title
            }
            if !childInfo.label.isEmpty && childInfo.label != "None" {
                attributes["label"] = childInfo.label
            }
            if !childInfo.value.isEmpty && childInfo.value != "None" {
                attributes["value"] = childInfo.value
            }
            if let identifier = childInfo.identifier, !identifier.isEmpty && identifier != "None" {
                attributes["identifier"] = identifier
            }

            let pathComponent = PathComponent(
                type: childInfo.type,
                attributes: attributes,
                index: index
            )

            var newPath = currentPath
            newPath.append(pathComponent)

            if let result = findPathToElement(from: child, target: target, currentPath: newPath) {
                return result
            }
        }

        return nil
    }

    if let foundPath = findPathToElement(from: startElement, target: element, currentPath: []) {
        pathComponents = foundPath
    }

    return pathComponents.map { $0.toString() }.joined(separator: " > ")
}

func parseDescriptivePath(_ pathString: String) -> [PathComponent] {
    let components = pathString.components(separatedBy: " > ")
    return components.compactMap { PathComponent.parse($0.trimmingCharacters(in: .whitespaces)) }
}

func navigateToElementByDescriptivePath(startElement: AXUIElement, pathComponents: [PathComponent])
    -> AXUIElement?
{
    // Helper struct to store candidate elements with their scores
    struct CandidateElement {
        let element: AXUIElement
        let score: Int
        let index: Int
    }

    // Helper struct to store complete paths with cumulative scores
    struct PathResult {
        let element: AXUIElement
        let cumulativeScore: Double
        let path: [CandidateElement]
    }

    // Recursive function that collects all possible paths with cumulative scores
    func collectAllPaths(
        currentElement: AXUIElement,
        remainingPathComponents: [PathComponent],
        currentPath: [CandidateElement] = [],
        currentScore: Double = 0.0,
        depth: Int = 0
    ) -> [PathResult] {

        // Base case: if no more path components, we've found a complete path
        guard !remainingPathComponents.isEmpty else {
            return [
                PathResult(
                    element: currentElement,
                    cumulativeScore: currentScore,
                    path: currentPath
                )
            ]
        }

        let pathComponent = remainingPathComponents[0]
        let remainingComponents = Array(remainingPathComponents.dropFirst())

        if pathComponent.type == "AXWindow" {
            fputs(
                "Skipping pathComponent: \(pathComponent) because it describes the startElement\n",
                stderr)
            return collectAllPaths(
                currentElement: currentElement,
                remainingPathComponents: remainingComponents,
                currentPath: currentPath,
                currentScore: currentScore,
                depth: depth + 1
            )
        }

        let children = getGroupTransparentChildrenWithInfo(element: currentElement)
        var candidates: [CandidateElement] = []

        // Evaluate all children and create candidates with scores
        for (index, childTuple) in children.enumerated() {
            let childInfo = childTuple.1
            let typeCompatibilityScore = getTypeCompatibilityScore(
                expectedType: pathComponent.type, actualType: childInfo.type)

            if typeCompatibilityScore > 0 {
                // Calculate attribute score
                var attributeScore: Double = 0
                let totalAttributes = pathComponent.attributes.count

                for (key, value) in pathComponent.attributes {
                    switch key {
                    case "title":
                        if childInfo.title == value {
                            attributeScore += 1
                        } else if childInfo.title.isEmpty || childInfo.title == "None" {
                            attributeScore += 0.5
                        }
                    case "label":
                        if childInfo.label == value {
                            attributeScore += 1
                        } else if childInfo.label.isEmpty || childInfo.label == "None" {
                            attributeScore += 0.5
                        }
                    case "value":
                        if childInfo.value == value {
                            attributeScore += 1
                        } else if childInfo.value.isEmpty || childInfo.value == "None" {
                            attributeScore += 0.5
                        }
                    case "identifier":
                        if childInfo.identifier == value {
                            attributeScore += 1
                        } else if childInfo.identifier == nil || childInfo.identifier == "None" {
                            attributeScore += 0.5
                        }
                    default:
                        attributeScore += 0.5
                    }
                }

                // Calculate overall score
                let overallScore =
                    typeCompatibilityScore
                    + (totalAttributes > 0
                        ? Int((attributeScore / Double(totalAttributes)) * 20) : 0)

                // If index is specified, boost score for exact match
                let finalScore =
                    if let expectedIndex = pathComponent.index, expectedIndex == index {
                        overallScore + 50  // Significant boost for exact index match
                    } else {
                        overallScore
                    }

                if finalScore >= 60 {  // Minimum threshold
                    candidates.append(
                        CandidateElement(
                            element: childTuple.0,
                            score: finalScore,
                            index: index
                        ))
                }
            }
        }

        // Sort candidates by score (highest first)
        candidates.sort { $0.score > $1.score }

        fputs("Depth \(depth): Found \(candidates.count) candidates for \(pathComponent)\n", stderr)

        let skippableTypes = ["AXScrollArea", "AXGroup"]
        if candidates.count == 0 && remainingComponents.count > 0
            && skippableTypes.contains(pathComponent.type)
        {
            // Try skipping the component
            fputs(
                "Skipping pathComponent: \(pathComponent) because no match was found\n",
                stderr)
            return collectAllPaths(
                currentElement: currentElement,
                remainingPathComponents: remainingComponents,
                currentPath: currentPath,
                currentScore: currentScore,
                depth: depth + 1
            )
        }
        for (i, candidate) in candidates.enumerated() {
            let childInfo = getElementInfo(element: candidate.element)
            fputs(
                "  Candidate \(i): score=\(candidate.score), index=\(candidate.index), type=\(childInfo.type), title=\(childInfo.title)\n",
                stderr)
        }

        var allPaths: [PathResult] = []

        // Collect all possible paths from each candidate
        for (candidateIndex, candidate) in candidates.enumerated() {
            fputs(
                "Depth \(depth): Exploring candidate \(candidateIndex) (score: \(candidate.score))\n",
                stderr)

            // Calculate weighted score for this depth (later elements have higher weight)
            let depthWeight = Double(depth + 1)  // Depth 0 = weight 1, Depth 1 = weight 2, etc.
            let weightedScore = Double(candidate.score) * depthWeight

            // Recursively collect all paths from this candidate
            let subPaths = collectAllPaths(
                currentElement: candidate.element,
                remainingPathComponents: remainingComponents,
                currentPath: currentPath + [candidate],
                currentScore: currentScore + weightedScore,
                depth: depth + 1
            )

            allPaths.append(contentsOf: subPaths)
        }

        fputs("Depth \(depth): Collected \(allPaths.count) total paths\n", stderr)
        return allPaths
    }

    // Collect all possible paths
    let allPaths = collectAllPaths(
        currentElement: startElement,
        remainingPathComponents: pathComponents
    )

    fputs("Total paths found: \(allPaths.count)\n", stderr)

    // Find the path with the highest cumulative score
    guard let bestPath = allPaths.max(by: { $0.cumulativeScore < $1.cumulativeScore }) else {
        fputs("No valid paths found\n", stderr)
        return nil
    }

    fputs("Best path selected with cumulative score: \(bestPath.cumulativeScore)\n", stderr)
    for (i, candidate) in bestPath.path.enumerated() {
        let childInfo = getElementInfo(element: candidate.element)
        fputs(
            "  Step \(i): score=\(candidate.score), type=\(childInfo.type), title=\(childInfo.title)\n",
            stderr)
    }

    return bestPath.element
}

func isDescriptivePath(_ pathString: String) -> Bool {
    return pathString.contains(" > ") || pathString.contains("[")
}

func navigateToElementWithPath(startElement: AXUIElement, pathString: String) -> AXUIElement? {
    if isDescriptivePath(pathString) {
        let pathComponents = parseDescriptivePath(pathString)
        return navigateToElementByDescriptivePath(
            startElement: startElement, pathComponents: pathComponents)
    } else {
        // Legacy index-based path
        let pathComponents =
            pathString.isEmpty ? [] : pathString.split(separator: ",").map(String.init)
        return navigateToElement(startElement: startElement, path: pathComponents)
    }
}

// MARK: - HTTP Helper Functions for Polling Server Communication
func getEventsFromPollingServer() -> [UserEvent]? {
    guard let url = URL(string: "http://localhost:8080/events") else {
        print("Error: Invalid URL for polling server")
        return nil
    }

    var request = URLRequest(url: url)
    request.httpMethod = "GET"
    request.timeoutInterval = 2.0

    let semaphore = DispatchSemaphore(value: 0)
    var events: [UserEvent]?

    let task = URLSession.shared.dataTask(with: request) { data, response, error in
        defer { semaphore.signal() }

        if let error = error {
            print("Error connecting to polling server: \(error)")
            return
        }

        guard let data = data else {
            print("Error: No data received from polling server")
            return
        }

        do {
            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            events = try decoder.decode([UserEvent].self, from: data)
            print("Successfully received \(events?.count ?? 0) events from polling server")
        } catch {
            print("Error decoding events from polling server: \(error)")
            if let responseString = String(data: data, encoding: .utf8) {
                print("Response data: \(responseString)")
            }
        }
    }

    task.resume()
    semaphore.wait()

    return events
}

func clearEventsFromPollingServer() -> Bool {
    guard let url = URL(string: "http://localhost:8080/events") else {
        print("Error: Invalid URL for polling server")
        return false
    }

    var request = URLRequest(url: url)
    request.httpMethod = "DELETE"
    request.timeoutInterval = 2.0

    let semaphore = DispatchSemaphore(value: 0)
    var success = false

    let task = URLSession.shared.dataTask(with: request) { data, response, error in
        defer { semaphore.signal() }

        if let error = error {
            print("Error connecting to polling server for clear: \(error)")
            return
        }

        guard let data = data else {
            print("Error: No data received from polling server for clear")
            return
        }

        do {
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                let result = json["success"] as? Bool
            {
                success = result
                print("Successfully cleared events from polling server: \(success)")
            }
        } catch {
            print("Error decoding clear response from polling server: \(error)")
            if let responseString = String(data: data, encoding: .utf8) {
                print("Response data: \(responseString)")
            }
        }
    }

    task.resume()
    semaphore.wait()

    return success
}

func getEventCountFromPollingServer() -> Int? {
    guard let url = URL(string: "http://localhost:8080/count") else {
        print("Error: Invalid URL for polling server")
        return nil
    }

    var request = URLRequest(url: url)
    request.httpMethod = "GET"
    request.timeoutInterval = 2.0

    let semaphore = DispatchSemaphore(value: 0)
    var count: Int?

    let task = URLSession.shared.dataTask(with: request) { data, response, error in
        defer { semaphore.signal() }

        if let error = error {
            print("Error connecting to polling server for count: \(error)")
            return
        }

        guard let data = data else {
            print("Error: No data received from polling server for count")
            return
        }

        do {
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                let eventCount = json["count"] as? Int
            {
                count = eventCount
                print("Successfully received event count from polling server: \(count)")
            }
        } catch {
            print("Error decoding event count from polling server: \(error)")
            if let responseString = String(data: data, encoding: .utf8) {
                print("Response data: \(responseString)")
            }
        }
    }

    task.resume()
    semaphore.wait()

    return count
}
