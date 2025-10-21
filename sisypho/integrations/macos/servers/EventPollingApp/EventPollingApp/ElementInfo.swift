import Foundation

public struct ElementInfo: Codable {
    public let index: Int?
    public let label: String
    public let title: String
    public let value: String
    public let type: String
    public let text: String?
    public let description: String?
    public let pressable: Bool
    public let availableActions: [String]
    public let hasMenu: Bool
    public let menuItems: [MenuItem]?
    public let identifier: String?
    public let appName: String?
    public let appBundleId: String?
    public let appProcessId: Int?
    public let path: String?
    public let semanticPath: String?
    public let descriptivePath: String?

    public init(
        index: Int?,
        label: String,
        title: String,
        value: String,
        type: String,
        text: String?,
        description: String?,
        pressable: Bool,
        availableActions: [String],
        hasMenu: Bool,
        menuItems: [MenuItem]?,
        identifier: String?,
        appName: String?,
        appBundleId: String?,
        appProcessId: Int?,
        path: String?,
        semanticPath: String?,
        descriptivePath: String?
    ) {
        self.index = index
        self.label = label
        self.title = title
        self.value = value
        self.type = type
        self.text = text
        self.description = description
        self.pressable = pressable
        self.availableActions = availableActions
        self.hasMenu = hasMenu
        self.menuItems = menuItems
        self.identifier = identifier
        self.appName = appName
        self.appBundleId = appBundleId
        self.appProcessId = appProcessId
        self.path = path
        self.semanticPath = semanticPath
        self.descriptivePath = descriptivePath
    }

    public init() {
        self.label = ""
        self.title = ""
        self.value = ""
        self.type = ""
        self.pressable = false
        self.availableActions = []
        self.hasMenu = false
        self.menuItems = []

        self.index = nil
        self.text = nil
        self.description = nil
        self.identifier = nil
        self.appName = nil
        self.appBundleId = nil
        self.appProcessId = nil
        self.path = nil
        self.semanticPath = nil
        self.descriptivePath = nil
    }
}

public struct MenuItem: Codable {
    public let index: Int
    public let title: String

    public init(index: Int, title: String) {
        self.index = index
        self.title = title
    }
}
