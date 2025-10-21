import Foundation
import Network
import os.log

final class EventServer: @unchecked Sendable {
    private let eventQueue: EventQueue
    private let listener: NWListener
    private let logger = Logger(subsystem: "com.sisypho.eventserver", category: "EventServer")

    init(eventQueue: EventQueue) throws {
        self.eventQueue = eventQueue

        // Create HTTP server on localhost:8080
        let parameters = NWParameters.tcp
        listener = try NWListener(using: parameters, on: NWEndpoint.Port(integerLiteral: 8080))

        listener.newConnectionHandler = { [weak self] connection in
            self?.handleConnection(connection)
        }
    }

    func start() {
        listener.start(queue: .main)
        logger.info("Event server started on port 8080")
    }

    func stop() {
        listener.cancel()
        logger.info("Event server stopped")
    }

    private func handleConnection(_ connection: NWConnection) {
        connection.start(queue: .main)

        connection.receive(minimumIncompleteLength: 1, maximumLength: 65536) {
            [weak self] data, _, isComplete, error in
            guard let self = self, let data = data else {
                connection.cancel()
                return
            }

            if let request = String(data: data, encoding: .utf8) {
                let response = self.handleRequest(request)
                if let responseData = response.data(using: .utf8) {
                    connection.send(
                        content: responseData,
                        completion: .contentProcessed { _ in
                            connection.cancel()
                        })
                }
            }
        }
    }

    private func handleRequest(_ request: String) -> String {
        let lines = request.components(separatedBy: "\r\n")
        guard let firstLine = lines.first else {
            return createHTTPResponse(status: 400, body: "Bad Request")
        }

        let parts = firstLine.components(separatedBy: " ")
        guard parts.count >= 2 else {
            return createHTTPResponse(status: 400, body: "Bad Request")
        }

        let method = parts[0]
        let path = parts[1]

        switch (method, path) {
        case ("GET", "/events"):
            return getEvents()
        case ("GET", "/count"):
            return getEventCount()
        case ("GET", "/stats"):
            return getEventStats()
        case ("DELETE", "/events"):
            return clearEvents()
        default:
            return createHTTPResponse(status: 404, body: "Not Found")
        }
    }

    private func getEvents() -> String {
        let events = eventQueue.getEvents()
        print("DEBUG: EventServer - Retrieved \(events.count) events from queue")
        let cgeventtapEvents = events.filter { $0.details["source"] == "cgeventtap" }
        print(
            "DEBUG: EventServer - Found \(cgeventtapEvents.count) events with source 'cgeventtap'")

        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = .prettyPrinted

        do {
            let jsonData = try encoder.encode(events)
            let jsonString = String(data: jsonData, encoding: .utf8) ?? "[]"
            return createHTTPResponse(
                status: 200, body: jsonString, contentType: "application/json")
        } catch {
            logger.error("Failed to encode events to JSON: \(error)")
            print("DEBUG: JSON encoding error: \(error)")
            // Return a simplified error response with event count
            let errorResponse: [String: Any] = ["error": "Failed to encode events", "count": events.count]
            if let errorData = try? JSONSerialization.data(withJSONObject: errorResponse),
               let errorString = String(data: errorData, encoding: .utf8) {
                return createHTTPResponse(status: 500, body: errorString, contentType: "application/json")
            }
            return createHTTPResponse(status: 500, body: "{\"error\": \"Internal Server Error\"}", contentType: "application/json")
        }
    }

    private func getEventCount() -> String {
        let count = eventQueue.getEventCount()
        let response = ["count": count]

        do {
            let jsonData = try JSONSerialization.data(withJSONObject: response)
            let jsonString = String(data: jsonData, encoding: .utf8) ?? "{}"
            return createHTTPResponse(
                status: 200, body: jsonString, contentType: "application/json")
        } catch {
            return createHTTPResponse(status: 500, body: "Internal Server Error")
        }
    }

    private func getEventStats() -> String {
        let stats = eventQueue.getEventStatistics()

        do {
            let jsonData = try JSONSerialization.data(withJSONObject: stats)
            let jsonString = String(data: jsonData, encoding: .utf8) ?? "{}"
            return createHTTPResponse(
                status: 200, body: jsonString, contentType: "application/json")
        } catch {
            return createHTTPResponse(status: 500, body: "Internal Server Error")
        }
    }

    private func clearEvents() -> String {
        eventQueue.clearEvents()
        let response: [String: Any] = ["success": true, "message": "All events cleared"]

        do {
            let jsonData = try JSONSerialization.data(withJSONObject: response)
            let jsonString = String(data: jsonData, encoding: .utf8) ?? "{}"
            return createHTTPResponse(
                status: 200, body: jsonString, contentType: "application/json")
        } catch {
            return createHTTPResponse(status: 500, body: "Internal Server Error")
        }
    }

    private func createHTTPResponse(status: Int, body: String, contentType: String = "text/plain")
        -> String
    {
        let statusText =
            status == 200
            ? "OK"
            : status == 400 ? "Bad Request" : status == 404 ? "Not Found" : "Internal Server Error"
        return """
            HTTP/1.1 \(status) \(statusText)
            Content-Type: \(contentType)
            Content-Length: \(body.utf8.count)
            Access-Control-Allow-Origin: *

            \(body)
            """
    }
}
