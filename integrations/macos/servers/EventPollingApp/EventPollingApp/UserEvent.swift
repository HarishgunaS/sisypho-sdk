import Foundation

public struct UserEvent: Codable {
    public let timestamp: Date
    public let type: String  // "click", "keyboard", "scroll", "keyboard_modifier", or "menu_selection"
    public let details: [String: String]  // Simplified to avoid Codable issues with Any

    public init(timestamp: Date, type: String, details: [String: String]) {
        self.timestamp = timestamp
        self.type = type
        self.details = details
    }

    // Custom Codable implementation for [String: String]
    enum CodingKeys: String, CodingKey {
        case timestamp, type, details
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        timestamp = try container.decode(Date.self, forKey: .timestamp)
        type = try container.decode(String.self, forKey: .type)
        details = try container.decode([String: String].self, forKey: .details)
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        
        // Safely encode timestamp - check for valid date
        let safeTimestamp: Date
        if timestamp.timeIntervalSinceReferenceDate.isNaN || 
           timestamp.timeIntervalSinceReferenceDate.isInfinite ||
           timestamp.timeIntervalSinceReferenceDate < 0 {
            // Use current date if timestamp is invalid
            safeTimestamp = Date()
            print("DEBUG: Invalid timestamp detected, using current date")
        } else {
            safeTimestamp = timestamp
        }
        
        try container.encode(safeTimestamp, forKey: .timestamp)
        try container.encode(type, forKey: .type)
        
        // Sanitize details dictionary to prevent encoding issues
        var sanitizedDetails: [String: String] = [:]
        for (key, value) in details {
            // Ensure key and value are not empty and contain valid characters
            let sanitizedKey = key.isEmpty ? "unknown_key" : key
            let sanitizedValue = value.isEmpty ? "empty" : value
            sanitizedDetails[sanitizedKey] = sanitizedValue
        }
        
        try container.encode(sanitizedDetails, forKey: .details)
    }
}
