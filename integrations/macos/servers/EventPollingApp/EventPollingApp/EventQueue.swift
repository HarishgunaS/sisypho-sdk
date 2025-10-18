import Foundation

public final class EventQueue: @unchecked Sendable {
    private var events: [UserEvent] = []
    private let queue = DispatchQueue(label: "com.sisypho.eventqueue", attributes: .concurrent)
    private let maxEvents = 500  // Reduced from 1000 for better memory management

    // Performance optimization: use a serial queue for writes to reduce contention
    private let writeQueue = DispatchQueue(
        label: "com.sisypho.eventqueue.write", qos: .userInitiated)

    public init() {}

    public func addEvent(_ event: UserEvent) {
        // Use write queue for better performance
        writeQueue.async {
            self.events.append(event)
            if self.events.count > self.maxEvents {
                // Remove oldest events in batches for better performance
                let removeCount = min(100, self.events.count - self.maxEvents)
                self.events.removeFirst(removeCount)
            }
        }
    }

    public func getEvents() -> [UserEvent] {
        return writeQueue.sync {
            return Array(events)
        }
    }

    public func clearEvents() {
        writeQueue.async {
            self.events.removeAll()
        }
    }

    public func getEventCount() -> Int {
        return writeQueue.sync {
            return events.count
        }
    }

    public func getEventStatistics() -> [String: Any] {
        return writeQueue.sync {
            let totalEvents = events.count
            let eventsByType = Dictionary(grouping: events, by: { $0.type })
                .mapValues { $0.count }
            let eventsBySource = Dictionary(
                grouping: events, by: { $0.details["source"] ?? "unknown" }
            )
            .mapValues { $0.count }

            return [
                "total_events": totalEvents,
                "events_by_type": eventsByType,
                "events_by_source": eventsBySource,
                "oldest_event": events.first?.timestamp,
                "newest_event": events.last?.timestamp,
            ]
        }
    }
}
