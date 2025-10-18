import AppKit
import ApplicationServices
import Carbon
import CoreGraphics
import Foundation
import os.log

typealias AXObserverCallback = @convention(c) (
    AXObserver, AXUIElement, CFString, UnsafeMutableRawPointer?
) -> Void

// System-wide accessibility observer callback
let systemWideAXObserverCallback: AXObserverCallback = {
    (observer, element, notification, userData) in
    guard let userData = userData else { return }
    let monitor = Unmanaged<EventPollingMonitor>.fromOpaque(userData).takeUnretainedValue()
    monitor.handleSystemWideAccessibilityEvent(
        observer: observer, element: element, notification: notification)
}

// MARK: - Helper Functions
func getString(_ value: CFTypeRef?) -> String? {
    guard let value = value else { return nil }
    if CFGetTypeID(value) == CFStringGetTypeID() {
        return value as? String
    }
    return nil
}

// Convert screen coordinates to accessibility coordinates if needed
func convertToAccessibilityCoordinates(_ screenPoint: NSPoint) -> NSPoint {
    // On macOS, screen coordinates have (0,0) at bottom-left
    // Accessibility APIs typically expect the same coordinate system
    // But let's add some debugging to verify this assumption
    print(
        "DEBUG: Converting screen coordinates (\(screenPoint.x), \(screenPoint.y)) to accessibility coordinates"
    )

    // Get screen height to potentially flip Y coordinate if needed
    let screenHeight = NSScreen.main?.frame.height ?? 0
    print("DEBUG: Screen height: \(screenHeight)")

    // For now, return the same coordinates as we assume they're compatible
    // If this doesn't work, we might need to flip the Y coordinate
    return screenPoint
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

// MARK: - Cached Element Info
struct CachedElementInfo {
    let elementInfo: ElementInfo
    let timestamp: Date
    let location: NSPoint

    var isStale: Bool {
        return Date().timeIntervalSince(timestamp) > 0.1  // 100ms cache
    }
}

// MARK: - Path Generation (Optimized)
struct PathComponent {
    let type: String
    let attributes: [String: String]
    var index: Int?

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

func getPathToRoot(root: AXUIElement, node: AXUIElement, currentPath: [AXUIElement])
    -> [AXUIElement]
{
    var newPath = currentPath
    newPath.append(node)
    if root == node {
        return currentPath
    }
    var parentValue: CFTypeRef?
    if AXUIElementCopyAttributeValue(
        node, kAXParentAttribute as CFString, &parentValue) != .success
    {
        return currentPath
    }

    let parentElement = (parentValue as! AXUIElement)

    return getPathToRoot(root: root, node: parentElement, currentPath: newPath)
}

func getPathFromRoot(pathToRoot: [AXUIElement]) -> [AXUIElement] {
    var pathFromRoot = pathToRoot
    pathFromRoot.reverse()
    var i = 0
    while i < pathFromRoot.count - 1 {
        let current = pathFromRoot[i]
        let next = pathFromRoot[i + 1]
        let children = getChildren(element: current)
        if children.contains(where: { CFEqual($0, next) }) {
            i += 1
        } else {
            pathFromRoot.remove(at: i + 1)
        }
    }
    return pathFromRoot
}

// MARK: - Descriptive Path Generation Functions
func generateDescriptivePath(to endElement: AXUIElement, from startElement: AXUIElement) -> String {
    print("DEBUG: Starting complex descriptive path generation")
    var pathComponents: [PathComponent] = []

    var elements: [AXUIElement] = getPathToRoot(
        root: startElement, node: endElement, currentPath: [])
    elements = getPathFromRoot(pathToRoot: elements)
    var previousElementInfo: ElementInfo?

    for (i, element) in elements.enumerated() {
        // check if the current element is a tab group
        let childInfo = getElementInfoFast(element: element, skipPath: true)
        // create attributes for the path component
        var attributes: [String: String] = [:]
        if !childInfo.title.isEmpty && childInfo.title != "None" {
            attributes["title"] = childInfo.title
        }
        if !childInfo.label.isEmpty && childInfo.label != "None" {
            attributes["label"] = childInfo.label
        }
        if !childInfo.value.isEmpty && childInfo.value != "None" && childInfo.value.count < 255 {  // TODO: make this a legit number
            attributes["value"] = childInfo.value
        }
        if let identifier = childInfo.identifier, !identifier.isEmpty && identifier != "None" {
            attributes["identifier"] = identifier
        }

        // Ignore index for children of tab groups
        var pathComponent = PathComponent(
            type: childInfo.type,
            attributes: attributes,
        )
        let isParentTabGroup = previousElementInfo?.type == "AXTabGroup"
        if !isParentTabGroup && i > 0 {
            let children = getChildren(element: elements[i - 1])
            for (index, child) in children.enumerated() {
                if child == element {
                    pathComponent.index = index
                }
            }
        }
        // TODO: maybe make this smarter?
        let skipThisComponent = false
        if !skipThisComponent {
            pathComponents.append(pathComponent)
            previousElementInfo = childInfo
        }
    }

    pathComponents = pathComponents.filter { $0.type != "AXGroup" }

    return pathComponents.map { $0.toString() }.joined(separator: " > ")
}

func generateDescriptivePathFromRoot(to element: AXUIElement) -> String {
    print("DEBUG: Starting descriptive path generation")

    // Get the process ID of the element
    var pid: pid_t = 0
    guard AXUIElementGetPid(element, &pid) == .success else {
        print("DEBUG: Failed to get process ID")
        return "Unknown"
    }

    print("DEBUG: Got process ID: \(pid)")

    // Create application element
    let appElement = AXUIElementCreateApplication(pid)

    // Try to generate path from application to element
    let path = generateDescriptivePath(to: element, from: appElement)

    // If path is empty, try a simpler approach by getting parent chain
    if path.isEmpty {
        print("DEBUG: Complex path generation failed, trying simple path")
        return generateSimpleDescriptivePath(to: element, from: appElement)
    }

    print("DEBUG: Complex path generation succeeded: \(path)")
    return path
}

func generateSimpleDescriptivePath(to element: AXUIElement, from startElement: AXUIElement)
    -> String
{
    print("DEBUG: Starting simple path generation")
    var pathComponents: [String] = []
    var currentElement = element
    var depth = 0
    let maxDepth = 10  // Limit depth to avoid infinite loops

    while depth < maxDepth {
        // Get element info
        let elementInfo = getElementInfoFast(element: currentElement, skipPath: true)
        print(
            "DEBUG: Element at depth \(depth): type=\(elementInfo.type), title=\(elementInfo.title), label=\(elementInfo.label)"
        )

        // Create a simple path component
        var component = elementInfo.type
        if !elementInfo.title.isEmpty && elementInfo.title != "None" {
            component += "[title=\"\(elementInfo.title)\"]"
        } else if !elementInfo.label.isEmpty && elementInfo.label != "None" {
            component += "[label=\"\(elementInfo.label)\"]"
        } else if let identifier = elementInfo.identifier,
            !identifier.isEmpty && identifier != "None"
        {
            component += "[identifier=\"\(identifier)\"]"
        }

        pathComponents.insert(component, at: 0)
        print("DEBUG: Added component: \(component)")

        // Check if we've reached the start element
        if currentElement == startElement {
            print("DEBUG: Reached start element, breaking")
            break
        }

        // Get parent element
        var parentValue: CFTypeRef?
        if AXUIElementCopyAttributeValue(
            currentElement, kAXParentAttribute as CFString, &parentValue) != .success
        {
            print("DEBUG: Failed to get parent element at depth \(depth)")
            break
        }

        currentElement = (parentValue as! AXUIElement)
        depth += 1
    }

    let result = pathComponents.joined(separator: " > ")
    print("DEBUG: Simple path generation result: \(result)")
    return result
}

// MARK: - Event Deduplication
struct EventKey: Hashable {
    let type: String
    let source: String
    let location: String
    let keyCode: String?
    let buttonNumber: String?
    let timestamp: TimeInterval

    init(
        type: String, source: String, location: NSPoint, keyCode: String? = nil,
        buttonNumber: String? = nil, timestamp: TimeInterval
    ) {
        self.type = type
        self.source = source
        self.location = "\(Int(location.x)),\(Int(location.y))"
        self.keyCode = keyCode
        self.buttonNumber = buttonNumber
        self.timestamp = timestamp
    }
}

// MARK: - Optimized Element Info Cache
class ElementInfoCache {
    private var cache: [String: CachedElementInfo] = [:]
    private let cacheQueue = DispatchQueue(
        label: "com.sisypho.elementcache", attributes: .concurrent)
    private let maxCacheSize = 100

    // Thread-safe access to cache
    private let cacheLock = NSLock()

    func getCachedElementInfo(at location: NSPoint) -> ElementInfo? {
        let key = "\(Int(location.x)),\(Int(location.y))"
        cacheLock.lock()
        defer { cacheLock.unlock() }

        guard let cached = cache[key], !cached.isStale else {
            return nil
        }
        return cached.elementInfo
    }

    func cacheElementInfo(_ elementInfo: ElementInfo, at location: NSPoint) {
        let key = "\(Int(location.x)),\(Int(location.y))"
        let cached = CachedElementInfo(
            elementInfo: elementInfo, timestamp: Date(), location: location)

        cacheLock.lock()
        defer { cacheLock.unlock() }

        cache[key] = cached

        // Clean up old entries if cache is too large
        if cache.count > maxCacheSize {
            let sortedKeys = cache.keys.sorted { key1, key2 in
                cache[key1]?.timestamp ?? Date.distantPast < cache[key2]?.timestamp
                    ?? Date.distantPast
            }
            let keysToRemove = sortedKeys.prefix(cache.count - maxCacheSize)
            for key in keysToRemove {
                cache.removeValue(forKey: key)
            }
        }
    }

    func clearCache() {
        cacheLock.lock()
        defer { cacheLock.unlock() }
        cache.removeAll()
    }
}

// MARK: - Event Deduplication Cache
class EventDeduplicationCache {
    private var recentEvents: Set<EventKey> = []
    private let cacheLock = NSLock()
    private let maxCacheSize = 100
    private let deduplicationWindow: TimeInterval = 0.1  // 100ms window

    func shouldProcessEvent(_ eventKey: EventKey) -> Bool {
        cacheLock.lock()
        defer { cacheLock.unlock() }

        // Clean up old events outside the deduplication window
        let currentTime = Date().timeIntervalSinceReferenceDate
        recentEvents = recentEvents.filter { currentTime - $0.timestamp < deduplicationWindow }

        // Check if this event is already in the cache
        if recentEvents.contains(eventKey) {
            return false
        }

        // Add to cache
        recentEvents.insert(eventKey)

        // Limit cache size
        if recentEvents.count > maxCacheSize {
            let sortedEvents = recentEvents.sorted { $0.timestamp < $1.timestamp }
            recentEvents = Set(sortedEvents.suffix(maxCacheSize))
        }

        return true
    }

    func clearCache() {
        cacheLock.lock()
        defer { cacheLock.unlock() }
        recentEvents.removeAll()
    }

    func getCacheSize() -> Int {
        cacheLock.lock()
        defer { cacheLock.unlock() }
        return recentEvents.count
    }
}

// MARK: - Optimized Element Info Functions
func getElementInfoFast(element: AXUIElement, skipPath: Bool = true) -> ElementInfo {
    var values: CFArray?
    let result = AXUIElementCopyMultipleAttributeValues(
        element,
        [
            kAXRoleAttribute as CFString, kAXTitleAttribute as CFString,
            kAXDescriptionAttribute as CFString, kAXValueAttribute as CFString,
            kAXIdentifierAttribute as CFString,
        ] as CFArray, AXCopyMultipleAttributeOptions.init(rawValue: 0),
        &values
    )
    guard result == .success, let attributesArray = values as? [CFTypeRef],
        attributesArray.count == 5
    else {
        return ElementInfo()
    }
    let role = getString(attributesArray[0]) ?? "Unknown"
    let title = getString(attributesArray[1]) ?? ""
    print("DEBUG: Found element - type: \(role), title: \(title)")
    let description = getString(attributesArray[2]) ?? "None"
    let value = getString(attributesArray[3]) ?? "None"
    let identifier = getString(attributesArray[4]) ?? "None"

    // Get app information from the element
    var appName: String? = nil
    var appBundleId: String? = nil
    var appProcessId: Int? = nil

    // Get the process ID of the element
    var pid: pid_t = 0
    if AXUIElementGetPid(element, &pid) == .success {
        appProcessId = Int(pid)

        // Get app name and bundle ID from the process
        if let app = NSWorkspace.shared.runningApplications.first(where: {
            $0.processIdentifier == pid
        }) {
            appName = app.localizedName
            appBundleId = app.bundleIdentifier
        }
    }

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

    // Check if element is pressable (simplified)
    var actionNamesCFArray: CFArray?
    let actionNamesResult = AXUIElementCopyActionNames(element, &actionNamesCFArray)
    var availableActions: [String] = []
    var isPressable = false
    if actionNamesResult == .success, let actionNamesCFArray = actionNamesCFArray as? [String] {
        availableActions = actionNamesCFArray
        let pressableActions = ["AXPress", "AXClick", "AXTap"]
        isPressable = actionNamesCFArray.contains { pressableActions.contains($0) }
    }

    // Generate descriptive path if not skipped
    var descriptivePath: String? = nil
    if !skipPath {
        // Skip path generation in getEGementInfoFast to avoid blocking
        // Path generation will be done separately in the event handlers
        descriptivePath = generateDescriptivePathFromRoot(to: element)
    }

    return ElementInfo(
        index: nil,
        label: description,
        title: title,
        value: value,
        type: role,
        text: text,
        description: description,
        pressable: isPressable,
        availableActions: availableActions,
        hasMenu: false,  // Skip menu detection for performance
        menuItems: nil,
        identifier: identifier,
        appName: appName,
        appBundleId: appBundleId,
        appProcessId: appProcessId,
        path: nil,  // Skip path generation for performance
        semanticPath: nil,
        descriptivePath: descriptivePath
    )
}

func getElementAtLocationFast(
    requiredAction: String? = nil, skipPath: Bool = false, at location: NSPoint? = nil
) -> ElementInfo {
    let screenLocation = location ?? NSEvent.mouseLocation
    let accessibilityLocation = convertToAccessibilityCoordinates(screenLocation)

    print(
        "DEBUG: getElementAtLocationFast called at screen coordinates: (\(screenLocation.x), \(screenLocation.y))"
    )
    print(
        "DEBUG: Using accessibility coordinates: (\(accessibilityLocation.x), \(accessibilityLocation.y))"
    )

    // Get the element at the specified location
    var elementRef: AXUIElement?
    let result = AXUIElementCopyElementAtPosition(
        AXUIElementCreateSystemWide(),
        Float(accessibilityLocation.x),
        Float(accessibilityLocation.y),
        &elementRef
    )

    if result == .success, let element = elementRef {
        print(
            "DEBUG: Successfully found element at coordinates (\(screenLocation.x), \(screenLocation.y))"
        )
        // If no required action is specified, return the element at location
        if requiredAction == nil {
            print("NO required action, returning found element")
            return getElementInfoFast(element: element, skipPath: skipPath)
        }

        // Check if the initial element has the required action
        var actionNamesCFArray: CFArray?
        let actionNamesResult = AXUIElementCopyActionNames(element, &actionNamesCFArray)
        if actionNamesResult == .success, let actionNamesCFArray = actionNamesCFArray as? [String] {
            if actionNamesCFArray.contains(requiredAction!) {
                print("First element had required action")
                return getElementInfoFast(element: element, skipPath: skipPath)
            }
        }

        // If the initial element doesn't have the required action, check its parents
        var currentElement = element
        var depth = 0
        let maxDepth = 5  // Reduced from 10 for performance

        while depth < maxDepth {
            // Get the parent element
            print("searching parents for required action")
            var parentValue: CFTypeRef?
            if AXUIElementCopyAttributeValue(
                currentElement, kAXParentAttribute as CFString, &parentValue) != .success
            {
                break
            }

            let parent = (parentValue as! AXUIElement)

            // Check if the parent has the required action
            var parentActionNamesCFArray: CFArray?
            let parentActionNamesResult = AXUIElementCopyActionNames(
                parent, &parentActionNamesCFArray)
            if parentActionNamesResult == .success,
                let parentActionNamesCFArray = parentActionNamesCFArray as? [String]
            {
                if parentActionNamesCFArray.contains(requiredAction!) {
                    return getElementInfoFast(element: parent, skipPath: skipPath)
                }
            }

            // Move up to the parent for the next iteration
            currentElement = parent
            depth += 1
        }

        currentElement = element
        depth = 0

        // check children that intersect?
        while depth < maxDepth {
            print("DEBUG: looking for children!", depth)
            var foundChild = false
            var children: [AXUIElement] = getChildren(element: element)
            for child in children {
                print("DEBUG: checking if child intersects!")
                var posValue: CFTypeRef?
                var sizeValue: CFTypeRef?

                let posResult = AXUIElementCopyAttributeValue(
                    child,
                    kAXPositionAttribute as CFString,
                    &posValue)
                let sizeResult = AXUIElementCopyAttributeValue(
                    child,
                    kAXSizeAttribute as CFString,
                    &sizeValue)

                guard posResult == .success,
                    sizeResult == .success
                else {
                    continue
                }

                let posAX = posValue as! AXValue
                let sizeAX = sizeValue as! AXValue

                var position = CGPoint.zero
                var size = CGSize.zero

                if !AXValueGetValue(posAX, .cgPoint, &position) { continue }
                if !AXValueGetValue(sizeAX, .cgSize, &size) { continue }

                let frame = CGRect(origin: position, size: size)
                print(frame.origin, frame.size)
                print(accessibilityLocation)
                if frame.contains(accessibilityLocation) {
                    print("DEBUG: point inside child frame!")
                    depth += 1
                    foundChild = true
                    currentElement = child
                    // Check if the child has the required action
                    var childActionNamesCFArray: CFArray?
                    let childActionNamesResult = AXUIElementCopyActionNames(
                        child, &childActionNamesCFArray)
                    if childActionNamesResult == .success,
                        let childActionNamesCFArray = childActionNamesCFArray as? [String]
                    {
                        print("DEBUG: child actions extracted")
                        if childActionNamesCFArray.contains(requiredAction!) {
                            print("DEBUG: child has required action!")
                            return getElementInfoFast(element: child, skipPath: skipPath)
                        }
                    }
                    break
                }
            }
            if !foundChild {
                break
            }
        }

        // If no parent with the required action is found, return the original element
        return getElementInfoFast(element: element, skipPath: skipPath)
    }

    // Return a default element info if we can't find the element
    print("DEBUG: Failed to find element at coordinates (\(screenLocation.x), \(screenLocation.y))")
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
        identifier: "None",
        appName: nil,
        appBundleId: nil,
        appProcessId: nil,
        path: nil,
        semanticPath: nil,
        descriptivePath: "Unknown"
    )
}

// MARK: - AXObserver Event Monitor
final class EventPollingMonitor: @unchecked Sendable {
    private let logger = Logger(
        subsystem: "com.sisypho.eventpolling", category: "EventPollingMonitor")
    private var lastMouseLocation: NSPoint = NSEvent.mouseLocation
    private var lastElementInfo: ElementInfo
    private var lastMouseButtonState: UInt = 0
    private var lastKeyState: UInt = 0
    private var keyboardMonitor: NSObjectProtocol?
    private var scrollMonitor: NSObjectProtocol?
    private var mouseMonitor: NSObjectProtocol?
    private let eventQueue: EventQueue

    // Performance optimizations
    private let elementCache = ElementInfoCache()
    private let eventDeduplicationCache = EventDeduplicationCache()
    private let backgroundQueue = DispatchQueue(
        label: "com.sisypho.background", qos: .userInitiated)
    private let pathGenerationQueue = DispatchQueue(
        label: "com.sisypho.pathgeneration", qos: .userInitiated)
    private var lastEventTime: Date = Date()
    private var eventCount: Int = 0
    private var cmdSpaceCount: Int = 0

    // Modifier key tracking
    private var currentModifiers: Set<String> = []
    private var lastModifierFlags: NSEvent.ModifierFlags = []

    // AXObserver properties
    private var systemWideObserver: AXObserver?
    private var focusedAppObserver: AXObserver?
    private var currentFocusedApp: NSRunningApplication?
    private var observerRunLoopSource: CFRunLoopSource?

    // System shortcut detection
    private var lastModifierState: NSEvent.ModifierFlags = []
    private var shortcutDetectionTimer: Timer?

    // CGEventTap for capturing all system events including shortcuts
    private var eventTap: CFMachPort?
    private var eventTapRunLoopSource: CFRunLoopSource?

    init(eventQueue: EventQueue) {
        self.eventQueue = eventQueue
        self.lastElementInfo = getElementAtLocationFast(skipPath: true, at: NSEvent.mouseLocation)
    }

    func startPolling() {
        print("Starting optimized AXObserver-based event detection...")

        // Initialize modifier state
        initializeModifierState()

        // Start CGEventTap for capturing all system events including shortcuts
        startCGEventTapMonitoring()

        // Check if we're running as a child process
        let parentProcessId = ProcessInfo.processInfo.environment["PARENT_PROCESS_ID"]
        let isChildProcess = parentProcessId != nil

        // For child processes, continue even if some monitoring fails
        if isChildProcess {
            print("Running as child process - continuing with available monitoring methods")
        }

        // Start keyboard monitoring
        startKeyboardMonitoring()

        // Start scroll monitoring
        startScrollMonitoring()

        // Start mouse monitoring
        startMouseMonitoring()

        // Start AXObserver monitoring
        startAXObserverMonitoring()

        print("Optimized AXObserver monitoring started")
    }

    private func startCGEventTapMonitoring() {
        print("Setting up optimized CGEventTap for capturing all system events...")

        // Create event mask for all events we want to capture
        let eventMask =
            (1 << CGEventType.keyDown.rawValue) | (1 << CGEventType.keyUp.rawValue)
            | (1 << CGEventType.flagsChanged.rawValue) | (1 << CGEventType.leftMouseDown.rawValue)
            | (1 << CGEventType.leftMouseUp.rawValue) | (1 << CGEventType.rightMouseDown.rawValue)
            | (1 << CGEventType.rightMouseUp.rawValue) | (1 << CGEventType.scrollWheel.rawValue)

        // Create the event tap callback
        let callback: CGEventTapCallBack = { (proxy, type, event, refcon) -> Unmanaged<CGEvent>? in
            guard let refcon = refcon else { return Unmanaged.passUnretained(event) }
            let monitor = Unmanaged<EventPollingMonitor>.fromOpaque(refcon).takeUnretainedValue()

            // Check if this is a null event (event tap becoming invalid)
            if type == .null {
                print("DEBUG: CGEventTap became invalid, will recreate...")
                DispatchQueue.main.async {
                    monitor.recreateEventTap()
                }
                return nil
            }

            // Check if event tap was disabled by timeout
            if type == .tapDisabledByTimeout {
                print("DEBUG: CGEventTap disabled by timeout! Re-enabling...")
                if let eventTap = monitor.eventTap {
                    CGEvent.tapEnable(tap: eventTap, enable: true)
                }
                return Unmanaged.passUnretained(event)
            }

            monitor.handleCGEvent(proxy: proxy, type: type, event: event)
            return Unmanaged.passUnretained(event)
        }

        // Create the event tap
        eventTap = CGEvent.tapCreate(
            tap: .cgSessionEventTap,
            place: .headInsertEventTap,
            options: .defaultTap,
            eventsOfInterest: CGEventMask(eventMask),
            callback: callback,
            userInfo: Unmanaged.passUnretained(self).toOpaque()
        )

        if let eventTap = eventTap {
            print("CGEventTap created successfully")

            // Create run loop source
            eventTapRunLoopSource = CFMachPortCreateRunLoopSource(
                kCFAllocatorDefault,
                eventTap,
                0
            )

            if let runLoopSource = eventTapRunLoopSource {
                // Add to run loop
                CFRunLoopAddSource(
                    CFRunLoopGetCurrent(),
                    runLoopSource,
                    .commonModes
                )

                // Enable the event tap
                CGEvent.tapEnable(tap: eventTap, enable: true)
                print("CGEventTap monitoring started successfully")
            } else {
                print("Failed to create run loop source for CGEventTap")
            }
        } else {
            print("Failed to create CGEventTap - check Accessibility permissions")
            print("DEBUG: This usually means the app doesn't have Accessibility permissions")
            print("DEBUG: Go to System Preferences > Security & Privacy > Privacy > Accessibility")
            print("DEBUG: and add this app to the list of allowed applications")

            // Check if we're running as a child process
            let parentProcessId = ProcessInfo.processInfo.environment["PARENT_PROCESS_ID"]
            let isChildProcess = parentProcessId != nil

            if isChildProcess {
                print(
                    "WARNING: Running as child process - CGEventTap creation failed but continuing..."
                )
                print("The parent process should have the necessary permissions")
            }
        }
    }

    private func recreateEventTap() {
        print("DEBUG: Recreating CGEventTap...")

        // Clean up existing event tap
        if let eventTap = eventTap {
            CGEvent.tapEnable(tap: eventTap, enable: false)
            if let runLoopSource = eventTapRunLoopSource {
                CFRunLoopRemoveSource(CFRunLoopGetCurrent(), runLoopSource, .commonModes)
            }
            CFMachPortInvalidate(eventTap)
        }

        eventTap = nil
        eventTapRunLoopSource = nil

        // Recreate the event tap
        startCGEventTapMonitoring()
    }

    // Public method to get event tap status for debugging
    func getEventTapStatus() -> [String: Any] {
        let timeSinceLastEvent = Date().timeIntervalSince(lastEventTime)
        return [
            "eventTapExists": eventTap != nil,
            "eventTapEnabled": eventTap != nil ? CGEvent.tapIsEnabled(tap: eventTap!) : false,
            "runLoopSourceExists": eventTapRunLoopSource != nil,
            "lastEventTime": lastEventTime,
            "timeSinceLastEvent": timeSinceLastEvent,
            "totalEventCount": eventCount,
            "cmdSpaceCount": cmdSpaceCount,
            "deduplicationCacheSize": eventDeduplicationCache.getCacheSize(),
        ]
    }

    // Public method to manually recreate event tap for testing
    func forceRecreateEventTap() {
        print("DEBUG: Force recreating CGEventTap...")
        recreateEventTap()
    }

    private func handleCGEvent(proxy: CGEventTapProxy, type: CGEventType, event: CGEvent) {
        // Capture the actual event timestamp from the system
        // CGEvent timestamp is in nanoseconds since system boot, convert to proper Date
        let rawTimestamp = event.timestamp
        let eventTimestamp: Date

        // Convert nanoseconds to seconds and check if valid
        let timestampInSeconds = TimeInterval(rawTimestamp) / 1_000_000_000.0

        if rawTimestamp == 0 || timestampInSeconds.isNaN || timestampInSeconds.isInfinite {
            print("DEBUG: Invalid CGEvent timestamp: \(rawTimestamp), using current date")
            eventTimestamp = Date()
        } else {
            // CGEvent timestamps are relative to system boot time, not reference date
            // For now, just use current time to avoid timestamp issues
            eventTimestamp = Date()
        }
        let currentMouseLocation = NSEvent.mouseLocation

        // For mouse events, get the exact location from the event
        var eventLocation = currentMouseLocation
        if type == .leftMouseDown || type == .leftMouseUp || type == .rightMouseDown
            || type == .rightMouseUp
        {
            eventLocation = event.location
            print("DEBUG: Mouse event at location: (\(eventLocation.x), \(eventLocation.y))")
        }

        // Create event key for deduplication
        let keyCode =
            type == .keyDown || type == .keyUp
            ? String(event.getIntegerValueField(.keyboardEventKeycode)) : nil
        let buttonNumber =
            (type == .leftMouseDown || type == .leftMouseUp || type == .rightMouseDown
                || type == .rightMouseUp)
            ? String(event.getIntegerValueField(.mouseEventButtonNumber)) : nil

        let eventKey = EventKey(
            type: String(describing: type),
            source: "cgeventtap",
            location: eventLocation,
            keyCode: keyCode,
            buttonNumber: buttonNumber,
            timestamp: eventTimestamp.timeIntervalSinceReferenceDate
        )

        // Check for deduplication
        guard eventDeduplicationCache.shouldProcessEvent(eventKey) else {
            print("DEBUG: Skipping duplicate event: \(eventKey)")
            return
        }

        // Update event tracking (minimal work on main thread)
        lastEventTime = eventTimestamp
        eventCount += 1

        if type == .leftMouseUp || type == .leftMouseDown || type == .rightMouseUp
            || type == .rightMouseDown
        {
            // process mouse events immediately
            self.processEvent(
                type: type, event: event, mouseLocation: eventLocation,
                eventTimestamp: eventTimestamp)
        } else {
            // Move all heavy processing to background queue to avoid blocking UI
            // This ensures the main thread remains responsive while processing events
            backgroundQueue.async {
                self.processEvent(
                    type: type, event: event, mouseLocation: eventLocation,
                    eventTimestamp: eventTimestamp)
            }
        }
    }

    private func processEvent(
        type: CGEventType, event: CGEvent, mouseLocation: NSPoint, eventTimestamp: Date
    ) {
        // Get element info on background thread
        let elementInfo: ElementInfo
        if let cached = self.elementCache.getCachedElementInfo(at: mouseLocation) {
            elementInfo = cached
        } else {
            // Skip descriptive path for keyboard events to improve performance
            print("is the caching stuff the issue?")
            elementInfo = getElementAtLocationFast(skipPath: true, at: mouseLocation)
            self.elementCache.cacheElementInfo(elementInfo, at: mouseLocation)
        }

        switch type {
        case .keyDown, .keyUp:
            self.handleCGKeyboardEvent(
                type: type, event: event, mouseLocation: mouseLocation,
                elementInfo: elementInfo, eventTimestamp: eventTimestamp)
        case .flagsChanged:
            self.handleCGFlagsChangedEvent(
                event: event, mouseLocation: mouseLocation, elementInfo: elementInfo,
                eventTimestamp: eventTimestamp)
        case .leftMouseDown, .leftMouseUp, .rightMouseDown, .rightMouseUp:
            // For mouse events, get element info at the exact location where the event occurred
            var requiredAction: String? = nil
            if type == .leftMouseDown || type == .leftMouseUp {
                requiredAction = "AXPress"
            } else if type == .rightMouseDown || type == .rightMouseUp {
                requiredAction = "AXShowMenu"
            }
            print("DEBUG mouse type", type)
            let mouseElementInfo = getElementAtLocationFast(
                requiredAction: requiredAction, skipPath: false, at: mouseLocation)

            self.handleCGMouseEvent(
                type: type, event: event, mouseLocation: mouseLocation,
                elementInfo: mouseElementInfo, eventTimestamp: eventTimestamp
            )
        case .scrollWheel:
            // For scroll events, get element info with descriptive path
            let scrollElementInfo: ElementInfo
            if let cached = self.elementCache.getCachedElementInfo(at: mouseLocation) {
                scrollElementInfo = cached
            } else {
                scrollElementInfo = getElementAtLocationFast(skipPath: true, at: mouseLocation)
                self.elementCache.cacheElementInfo(scrollElementInfo, at: mouseLocation)
            }
            self.handleCGScrollEvent(
                event: event, mouseLocation: mouseLocation, elementInfo: scrollElementInfo,
                eventTimestamp: eventTimestamp)
        default:
            break
        }
    }

    private func handleCGKeyboardEvent(
        type: CGEventType, event: CGEvent, mouseLocation: NSPoint, elementInfo: ElementInfo,
        eventTimestamp: Date
    ) {
        let keyCode = event.getIntegerValueField(.keyboardEventKeycode)
        let flags = event.flags
        let characters = getCharacters(from: event)
        // For charactersIgnoringModifiers, create a copy with modifiers removed
        let eventCopy = event.copy()!
        eventCopy.flags = CGEventFlags(rawValue: 0)
        let charactersIgnoringModifiers = getCharacters(from: eventCopy)

        let keyName = getKeyName(for: UInt16(keyCode))
        let eventType = type == .keyDown ? "keydown" : "keyup"

        // Check for system shortcuts
        if flags.contains(.maskCommand) {
            if keyCode == 49 {  // Space key
                cmdSpaceCount += 1
            }
        }

        let eventDetails: [String: String] = [
            "key_code": String(keyCode),
            "key_name": keyName,
            "characters": characters,
            "characters_ignoring_modifiers": charactersIgnoringModifiers,
            "modifier_flags": String(flags.rawValue),
            "active_modifiers": getActiveModifiersString(from: flags),
            "action": eventType,
            "source": "cgeventtap",
            "location_x": String(format: "%.2f", mouseLocation.x),
            "location_y": String(format: "%.2f", mouseLocation.y),
            // "element_type": elementInfo.type,
            // "element_title": elementInfo.title,
            // "element_label": elementInfo.label,
            // "element_value": elementInfo.value,
            // "element_pressable": String(elementInfo.pressable),
            // "element_identifier": "None",  // elementInfo.identifier ?? "None",
            // "element_actions": elementInfo.availableActions.joined(separator: ", "),
            // "element_text": "None",  // elementInfo.text ?? "None",
            // "element_description": "None",  // elementInfo.description ?? "None",
            // "element_descriptive_path": "None",  // elementInfo.descriptivePath ?? "None",
            "app_name": elementInfo.appName ?? "Unknown",
            "app_bundle_id": elementInfo.appBundleId ?? "Unknown",
            "app_process_id": String(elementInfo.appProcessId ?? 0),
        ]

        let userEvent = UserEvent(
            timestamp: eventTimestamp,
            type: "keyboard",
            details: eventDetails
        )

        // Use background queue for event processing
        backgroundQueue.async {
            self.eventQueue.addEvent(userEvent)
        }
    }

    private func handleCGFlagsChangedEvent(
        event: CGEvent, mouseLocation: NSPoint, elementInfo: ElementInfo, eventTimestamp: Date
    ) {
        let flags = event.flags
        let previousFlags = lastModifierFlags

        // Check for modifier key changes
        let modifierKeys: [(NSEvent.ModifierFlags, String)] = [
            (.command, "cmd"),
            (.shift, "shift"),
            (.option, "alt"),
            (.control, "ctrl"),
            (.function, "fn"),
            (.capsLock, "caps"),
        ]

        for (flag, modifierName) in modifierKeys {
            let wasPressed = previousFlags.contains(flag)
            let isPressed = flags.contains(CGEventFlags(rawValue: UInt64(flag.rawValue)))

            if wasPressed != isPressed {
                // Modifier state changed
                let action = isPressed ? "pressed" : "released"

                let eventDetails: [String: String] = [
                    "modifiers": modifierName,
                    "action": action,
                    "source": "cgeventtap",
                    "location_x": String(format: "%.2f", mouseLocation.x),
                    "location_y": String(format: "%.2f", mouseLocation.y),
                    "element_type": elementInfo.type,
                    "element_title": elementInfo.title,
                    "element_label": elementInfo.label,
                    "element_value": elementInfo.value,
                    "element_pressable": String(elementInfo.pressable),
                    "element_identifier": elementInfo.identifier ?? "None",
                    "element_actions": elementInfo.availableActions.joined(separator: ", "),
                    "element_text": elementInfo.text ?? "None",
                    "element_description": elementInfo.description ?? "None",
                    "element_descriptive_path": elementInfo.descriptivePath ?? "None",
                    "app_name": elementInfo.appName ?? "Unknown",
                    "app_bundle_id": elementInfo.appBundleId ?? "Unknown",
                    "app_process_id": String(elementInfo.appProcessId ?? 0),
                ]

                let userEvent = UserEvent(
                    timestamp: eventTimestamp,
                    type: "keyboard_modifier",
                    details: eventDetails
                )

                // Use background queue for event processing
                backgroundQueue.async {
                    self.eventQueue.addEvent(userEvent)
                }

                // Update current modifiers set
                if isPressed {
                    currentModifiers.insert(modifierName)
                } else {
                    currentModifiers.remove(modifierName)
                }
            }
        }

        lastModifierFlags = NSEvent.ModifierFlags(rawValue: UInt(flags.rawValue))
    }

    private func handleCGMouseEvent(
        type: CGEventType, event: CGEvent, mouseLocation: NSPoint, elementInfo: ElementInfo,
        eventTimestamp: Date
    ) {
        let buttonNumber = event.getIntegerValueField(.mouseEventButtonNumber)
        let clickCount = event.getIntegerValueField(.mouseEventClickState)
        let flags = event.flags

        let eventType = type == .leftMouseDown || type == .rightMouseDown ? "mousedown" : "mouseup"

        let eventDetails: [String: String] = [
            "button_number": String(buttonNumber),
            "click_count": String(clickCount),
            "event_type": String(describing: type),
            "modifier_flags": String(flags.rawValue),
            "source": "cgeventtap",
            "location_x": String(format: "%.2f", mouseLocation.x),
            "location_y": String(format: "%.2f", mouseLocation.y),
            "element_type": elementInfo.type,
            "element_title": elementInfo.title,
            "element_label": elementInfo.label,
            "element_value": elementInfo.value,
            "element_pressable": String(elementInfo.pressable),
            "element_identifier": elementInfo.identifier ?? "None",
            "element_actions": elementInfo.availableActions.joined(separator: ", "),
            "element_text": elementInfo.text ?? "None",
            "element_description": elementInfo.description ?? "None",
            "element_descriptive_path": elementInfo.descriptivePath ?? "None",
            "app_name": elementInfo.appName ?? "Unknown",
            "app_bundle_id": elementInfo.appBundleId ?? "Unknown",
            "app_process_id": String(elementInfo.appProcessId ?? 0),
        ]

        let userEvent = UserEvent(
            timestamp: eventTimestamp,
            type: "mouse",
            details: eventDetails
        )

        // Use background queue for event processing
        backgroundQueue.async {
            self.eventQueue.addEvent(userEvent)
        }
    }

    private func handleCGScrollEvent(
        event: CGEvent, mouseLocation: NSPoint, elementInfo: ElementInfo, eventTimestamp: Date
    ) {
        let deltaX = event.getDoubleValueField(.scrollWheelEventDeltaAxis2)
        let deltaY = event.getDoubleValueField(.scrollWheelEventDeltaAxis1)

        if abs(deltaY) > 0.1 || abs(deltaX) > 0.1 {
            let eventDetails: [String: String] = [
                "delta_x": String(format: "%.2f", deltaX),
                "delta_y": String(format: "%.2f", deltaY),
                "source": "cgeventtap",
                "location_x": String(format: "%.2f", mouseLocation.x),
                "location_y": String(format: "%.2f", mouseLocation.y),
                "element_type": elementInfo.type,
                "element_title": elementInfo.title,
                "element_label": elementInfo.label,
                "element_value": elementInfo.value,
                "element_pressable": String(elementInfo.pressable),
                "element_identifier": elementInfo.identifier ?? "None",
                "element_actions": elementInfo.availableActions.joined(separator: ", "),
                "element_text": elementInfo.text ?? "None",
                "element_description": elementInfo.description ?? "None",
                "element_descriptive_path": elementInfo.descriptivePath ?? "None",
                "app_name": elementInfo.appName ?? "Unknown",
                "app_bundle_id": elementInfo.appBundleId ?? "Unknown",
                "app_process_id": String(elementInfo.appProcessId ?? 0),
            ]

            let userEvent = UserEvent(
                timestamp: eventTimestamp,
                type: "scroll",
                details: eventDetails
            )

            // Use background queue for event processing
            backgroundQueue.async {
                self.eventQueue.addEvent(userEvent)
            }
        }
    }

    private func getActiveModifiersString(from flags: CGEventFlags) -> String {
        var modifiers: [String] = []

        if flags.contains(.maskCommand) { modifiers.append("cmd") }
        if flags.contains(.maskShift) { modifiers.append("shift") }
        if flags.contains(.maskAlternate) { modifiers.append("alt") }
        if flags.contains(.maskControl) { modifiers.append("ctrl") }
        if flags.contains(.maskSecondaryFn) { modifiers.append("fn") }
        if flags.contains(.maskAlphaShift) { modifiers.append("caps") }

        return modifiers.isEmpty ? "none" : modifiers.joined(separator: ",")
    }

    private func initializeModifierState() {
        // Get current modifier state from the system
        let currentFlags = NSEvent.modifierFlags
        lastModifierFlags = currentFlags

        // Initialize current modifiers set
        currentModifiers.removeAll()
        let modifierKeys: [(NSEvent.ModifierFlags, String)] = [
            (.command, "cmd"),
            (.shift, "shift"),
            (.option, "alt"),
            (.control, "ctrl"),
            (.function, "fn"),
            (.capsLock, "caps"),
        ]

        for (flag, modifierName) in modifierKeys {
            if currentFlags.contains(flag) {
                currentModifiers.insert(modifierName)
            }
        }
    }

    private func startAXObserverMonitoring() {
        // Create system-wide observer for global events
        createSystemWideObserver()

        // Start monitoring focused application
        startFocusedAppMonitoring()

        // Set up run loop source for AXObserver
        setupObserverRunLoop()
    }

    private func createSystemWideObserver() {
        let systemWideElement = AXUIElementCreateSystemWide()
        var observer: AXObserver?

        let callback: AXObserverCallback = { observer, element, notification, context in
            guard let context = context else { return }
            let monitor = Unmanaged<EventPollingMonitor>
                .fromOpaque(context)
                .takeUnretainedValue()
            monitor.handleSystemWideAccessibilityEvent(
                observer: observer, element: element, notification: notification)
        }

        var pid: pid_t = 0
        AXUIElementGetPid(systemWideElement, &pid)

        let result: AXError = AXObserverCreate(
            pid,
            callback,
            &observer
        )

        if result == .success, let observer = observer {
            systemWideObserver = observer

            // Add notifications for system-wide events
            let notifications: [CFString] = [
                kAXFocusedUIElementChangedNotification as CFString,
                kAXFocusedWindowChangedNotification as CFString,
                kAXApplicationActivatedNotification as CFString,
                kAXApplicationDeactivatedNotification as CFString,
            ]

            for notification in notifications {
                AXObserverAddNotification(
                    observer as AXObserver, systemWideElement, notification, nil)
            }

            print("System-wide AXObserver created successfully")
        } else {
            print("Failed to create system-wide AXObserver")
        }
    }

    private func startFocusedAppMonitoring() {
        // Get the currently focused application
        if let focusedApp = NSWorkspace.shared.frontmostApplication {
            currentFocusedApp = focusedApp
            createFocusedAppObserver(for: focusedApp)
        }

        // Monitor for application focus changes
        NotificationCenter.default.addObserver(
            forName: NSWorkspace.didActivateApplicationNotification,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            if let app = notification.userInfo?[NSWorkspace.applicationUserInfoKey]
                as? NSRunningApplication
            {
                self?.currentFocusedApp = app
                self?.createFocusedAppObserver(for: app)
            }
        }
    }

    private func createFocusedAppObserver(for app: NSRunningApplication) {
        // Clean up existing observer
        if let existingObserver = focusedAppObserver {
            AXObserverRemoveNotification(
                existingObserver as AXObserver,
                AXUIElementCreateApplication(app.processIdentifier),
                kAXFocusedUIElementChangedNotification as CFString
            )
        }

        let appElement = AXUIElementCreateApplication(app.processIdentifier)
        var observer: AXObserver?

        let callback: AXObserverCallback = { observer, element, notification, context in
            guard let context = context else { return }
            let monitor = Unmanaged<EventPollingMonitor>
                .fromOpaque(context)
                .takeUnretainedValue()
            monitor.handleFocusedAppAccessibilityEvent(
                observer: observer, element: element, notification: notification)
        }

        let result: AXError = AXObserverCreate(
            app.processIdentifier,
            callback,
            &observer
        )

        if result == .success, let observer = observer {
            focusedAppObserver = observer

            // Add notification for focused element changes
            AXObserverAddNotification(
                observer as AXObserver,
                AXUIElementCreateApplication(app.processIdentifier),
                kAXFocusedUIElementChangedNotification as CFString,
                nil
            )

            print("Focused app AXObserver created for \(app.localizedName ?? "Unknown")")
        } else {
            print("Failed to create focused app AXObserver for \(app.localizedName ?? "Unknown")")
        }
    }

    private func setupObserverRunLoop() {
        // Create run loop source for AXObserver
        if let observer = systemWideObserver {
            observerRunLoopSource = AXObserverGetRunLoopSource(observer as AXObserver)
            if let runLoopSource = observerRunLoopSource {
                CFRunLoopAddSource(
                    CFRunLoopGetCurrent(),
                    runLoopSource,
                    .commonModes
                )
            }
        }
    }

    internal func handleSystemWideAccessibilityEvent(
        observer: AXObserver, element: AXUIElement, notification: CFString
    ) {
        // Handle system-wide accessibility events
        let notificationName = notification as String

        // Use background queue for processing
        backgroundQueue.async {
            let eventTimestamp = Date()
            let eventDetails: [String: String] = [
                "notification": notificationName,
                "source": "axobserver_system",
                "timestamp": ISO8601DateFormatter().string(from: eventTimestamp),
            ]

            let userEvent = UserEvent(
                timestamp: eventTimestamp,
                type: "accessibility_system",
                details: eventDetails
            )

            self.eventQueue.addEvent(userEvent)
        }
    }

    internal func handleFocusedAppAccessibilityEvent(
        observer: AXObserver, element: AXUIElement, notification: CFString
    ) {
        // Handle focused app accessibility events
        let notificationName = notification as String

        // Use background queue for processing
        backgroundQueue.async {
            let eventTimestamp = Date()
            let eventDetails: [String: String] = [
                "notification": notificationName,
                "source": "axobserver_focused",
                "timestamp": ISO8601DateFormatter().string(from: eventTimestamp),
            ]

            let userEvent = UserEvent(
                timestamp: eventTimestamp,
                type: "accessibility_focused",
                details: eventDetails
            )

            self.eventQueue.addEvent(userEvent)
        }
    }

    private func startKeyboardMonitoring() {
        // Monitor for keyboard events using NSEvent
        keyboardMonitor =
            NSEvent.addLocalMonitorForEvents(matching: [.keyDown, .keyUp]) {
                [weak self] event in
                // This is a backup to CGEventTap - CGEventTap should handle most events
                return event
            } as? NSObjectProtocol
    }

    private func startScrollMonitoring() {
        // Monitor for scroll events using NSEvent
        scrollMonitor =
            NSEvent.addLocalMonitorForEvents(matching: [.scrollWheel]) {
                [weak self] event in
                // This is a backup to CGEventTap - CGEventTap should handle most events
                return event
            } as? NSObjectProtocol
    }

    private func startMouseMonitoring() {
        // Monitor for mouse events using NSEvent
        mouseMonitor =
            NSEvent.addLocalMonitorForEvents(matching: [
                .leftMouseDown, .leftMouseUp, .rightMouseDown, .rightMouseUp,
            ]) { [weak self] event in
                // This is a backup to CGEventTap - CGEventTap should handle most events
                return event
            } as? NSObjectProtocol
    }

    func stopPolling() {
        // Stop CGEventTap
        if let eventTap = eventTap {
            CGEvent.tapEnable(tap: eventTap, enable: false)
            if let runLoopSource = eventTapRunLoopSource {
                CFRunLoopRemoveSource(CFRunLoopGetCurrent(), runLoopSource, .commonModes)
            }
            CFMachPortInvalidate(eventTap)
        }

        // Stop AXObserver
        if let observer = systemWideObserver {
            AXObserverRemoveNotification(
                observer as AXObserver,
                AXUIElementCreateSystemWide(),
                kAXFocusedUIElementChangedNotification as CFString
            )
        }

        if let observer = focusedAppObserver {
            AXObserverRemoveNotification(
                observer as AXObserver,
                AXUIElementCreateApplication(currentFocusedApp?.processIdentifier ?? 0),
                kAXFocusedUIElementChangedNotification as CFString
            )
        }

        // Remove run loop sources
        if let runLoopSource = observerRunLoopSource {
            CFRunLoopRemoveSource(CFRunLoopGetCurrent(), runLoopSource, .commonModes)
        }

        // Stop NSEvent monitors
        if let keyboardMonitor = keyboardMonitor {
            NSEvent.removeMonitor(keyboardMonitor)
        }
        if let scrollMonitor = scrollMonitor {
            NSEvent.removeMonitor(scrollMonitor)
        }
        if let mouseMonitor = mouseMonitor {
            NSEvent.removeMonitor(mouseMonitor)
        }

        // Clear caches
        elementCache.clearCache()
        eventDeduplicationCache.clearCache()

        print("Event polling stopped")
    }
}

// MARK: - Helper Functions for CGEvent Processing
func getCharacters(from event: CGEvent) -> String {
    var length: Int = 0
    event.keyboardGetUnicodeString(
        maxStringLength: 255, actualStringLength: &length, unicodeString: nil)
    var unicodeString = [UniChar](repeating: 0, count: length)
    event.keyboardGetUnicodeString(
        maxStringLength: length, actualStringLength: &length, unicodeString: &unicodeString)
    return String(utf16CodeUnits: unicodeString, count: length)
}

func getKeyName(for keyCode: UInt16) -> String {
    switch keyCode {
    case 0: return "a"
    case 1: return "s"
    case 2: return "d"
    case 3: return "f"
    case 4: return "h"
    case 5: return "g"
    case 6: return "z"
    case 7: return "x"
    case 8: return "c"
    case 9: return "v"
    case 11: return "b"
    case 12: return "q"
    case 13: return "w"
    case 14: return "e"
    case 15: return "r"
    case 16: return "y"
    case 17: return "t"
    case 18: return "1"
    case 19: return "2"
    case 20: return "3"
    case 21: return "4"
    case 22: return "6"
    case 23: return "5"
    case 24: return "="
    case 25: return "9"
    case 26: return "7"
    case 27: return "-"
    case 28: return "8"
    case 29: return "0"
    case 30: return "]"
    case 31: return "o"
    case 32: return "u"
    case 33: return "["
    case 34: return "i"
    case 35: return "p"
    case 37: return "l"
    case 38: return "j"
    case 39: return "'"
    case 40: return "k"
    case 41: return ";"
    case 42: return "\\"
    case 43: return ","
    case 44: return "/"
    case 45: return "n"
    case 46: return "m"
    case 47: return "."
    case 50: return "`"
    case 65: return "."
    case 67: return "*"
    case 69: return "+"
    case 71: return "⌧"
    case 75: return "/"
    case 76: return "↩"
    case 78: return "-"
    case 81: return "="
    case 82: return "0"
    case 83: return "1"
    case 84: return "2"
    case 85: return "3"
    case 86: return "4"
    case 87: return "5"
    case 88: return "6"
    case 89: return "7"
    case 91: return "8"
    case 92: return "9"
    case 36: return "↩"
    case 48: return "⇥"
    case 49: return " "
    case 51: return "⌫"
    case 53: return "⎋"
    case 96: return "F5"
    case 97: return "F6"
    case 98: return "F7"
    case 99: return "F3"
    case 100: return "F8"
    case 101: return "F9"
    case 103: return "F11"
    case 105: return "⌤"
    case 107: return "F10"
    case 109: return "⌘"
    case 111: return "F12"
    case 114: return "⌤"
    case 115: return "↖"
    case 116: return "⇞"
    case 117: return "⌦"
    case 118: return "F4"
    case 119: return "↘"
    case 120: return "F2"
    case 121: return "⇟"
    case 122: return "F1"
    case 123: return "←"
    case 124: return "→"
    case 125: return "↓"
    case 126: return "↑"
    case 0x3B: return "⌃"
    case 0x3C: return "⇧"
    case 0x3D: return "⌥"
    case 0x3E: return "⌘"
    case 0x3F: return "fn"
    default: return "key\(keyCode)"
    }
}
