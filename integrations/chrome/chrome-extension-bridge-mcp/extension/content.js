const RPCErrorCodes = {
  ParseError: -32700,
  InvalidRequest: -32600,
  MethodNotFound: -32601,
  InvalidParams: -32602,
  InternalError: -32603,
  ServerError: -32000,
};

const MCPCallTag = {
  Tool: "mcp:tool",
  Resource: "mcp:resource",
};

// No longer storing interactions locally - they go to background script

// Connection state tracking
let isRegistered = false;
let registrationRetries = 0;
const maxRegistrationRetries = 5;

// Helper function to check if extension context is valid
function isExtensionContextValid() {
  try {
    // Check if chrome APIs are available
    if (!chrome || !chrome.runtime || !chrome.storage) {
      return false;
    }

    // Check if we have a valid extension ID
    if (!chrome.runtime.id) {
      return false;
    }

    // Additional check for storage API availability
    if (!chrome.storage.local) {
      return false;
    }

    return true;
  } catch (error) {
    console.warn("Extension context invalidated from helper function:", error);
    return false;
  }
}

// Send interaction to background script
function sendInteractionToBackground(interaction) {
  if (!isExtensionContextValid()) {
    console.warn("Extension context invalidated, cannot send interaction");
    return;
  }

  try {
    chrome.runtime.sendMessage(
      {
        type: "add_interaction",
        interaction: interaction,
      },
      (response) => {
        if (chrome.runtime.lastError) {
          console.warn(
            "Error sending interaction to background:",
            chrome.runtime.lastError
          );
        } else {
          console.log("Interaction sent to background successfully");
        }
      }
    );
  } catch (error) {
    console.warn("Failed to send interaction to background:", error);
  }
}

// Register with background script with retry logic
function registerWithBackground() {
  if (!isExtensionContextValid()) {
    console.warn("Extension context invalid, cannot register with background");
    return;
  }

  if (isRegistered) {
    console.log("Already registered with background script");
    return;
  }

  console.log("Registering content script with background script...");
  chrome.runtime.sendMessage({ type: "content_script_ready" }, (response) => {
    if (chrome.runtime.lastError) {
      console.warn(
        "Error registering content script:",
        chrome.runtime.lastError
      );

      // Retry registration with exponential backoff
      if (registrationRetries < maxRegistrationRetries) {
        registrationRetries++;
        const delay = Math.min(
          1000 * Math.pow(2, registrationRetries - 1),
          10000
        );
        console.log(
          `Retrying registration in ${delay}ms (attempt ${registrationRetries}/${maxRegistrationRetries})`
        );
        setTimeout(registerWithBackground, delay);
      } else {
        console.error("Max registration retries reached");
      }
      return;
    }

    if (response && response.status === "registered") {
      console.log(
        "Content script successfully registered with background script"
      );
      isRegistered = true;
      registrationRetries = 0;

      // Force reload interaction queue after registration
      loadInteractionQueue();
    } else {
      console.warn("Unexpected response from background script:", response);
    }
  });
}

// No longer need to load interaction queue locally

// Handle page lifecycle events
window.addEventListener("beforeunload", () => {
  console.log("Content: Page unloading");

  // Notify background script that this content script is being destroyed
  if (isExtensionContextValid()) {
    try {
      chrome.runtime
        .sendMessage({
          type: "content_script_destroyed",
          tabId: chrome.runtime.id,
        })
        .catch(() => {
          // Ignore errors during page unload
        });
    } catch (error) {
      // Ignore errors during page unload
    }
  }
});

// Handle page visibility changes (for SPA navigation)
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") {
    console.log("Content: Page hidden");
  }
});

// Function to capture DOM state
function captureDOMState() {
  function serializeElement(el) {
    const obj = {
      tag: el.tagName.toLowerCase(),
      attributes: {},
      text:
        el.childNodes.length === 1 &&
        el.childNodes[0].nodeType === Node.TEXT_NODE
          ? el.textContent.trim()
          : null,
      children: [],
    };
    for (let attr of el.attributes) {
      obj.attributes[attr.name] = attr.value;
    }
    for (let child of el.children) {
      obj.children.push(serializeElement(child));
    }
    return obj;
  }
  return serializeElement(document.body);
}

// Function to generate XPath for an element
function getXPath(element) {
  if (!element || element.nodeType !== Node.ELEMENT_NODE) {
    return null;
  }

  // Handle special cases
  if (element === document.body) {
    return "/html/body";
  }

  if (element === document.documentElement) {
    return "/html";
  }

  // Build path from element to root
  const path = [];
  let current = element;

  while (current && current !== document.documentElement) {
    let selector = current.tagName.toLowerCase();

    // Add ID if available (makes XPath more specific and reliable)
    if (current.id) {
      selector += `[@id='${current.id}']`;
      path.unshift(selector);
      break; // ID should be unique, so we can stop here
    }

    // Add class information if available (helps with identification)
    if (current.className && typeof current.className === "string") {
      const classes = current.className
        .trim()
        .split(/\s+/)
        .filter((c) => c);
      if (classes.length > 0) {
        selector += `[@class='${classes.join(" ")}']`;
      }
    }

    // Find position among siblings of the same tag
    let sibling = current.parentNode ? current.parentNode.firstChild : null;
    let position = 1;

    while (sibling) {
      if (
        sibling.nodeType === Node.ELEMENT_NODE &&
        sibling.tagName === current.tagName
      ) {
        if (sibling === current) {
          break;
        }
        position++;
      }
      sibling = sibling.nextSibling;
    }

    // Add position if there are multiple siblings with same tag
    if (current.parentNode) {
      const siblings = Array.from(current.parentNode.children).filter(
        (child) => child.tagName === current.tagName
      );
      if (siblings.length > 1) {
        selector += `[${position}]`;
      }
    }

    path.unshift(selector);
    current = current.parentNode;
  }

  return path.length > 0 ? "/" + path.join("/") : null;
}

// Function to get additional element context information
function getElementContext(element) {
  const rect = element.getBoundingClientRect();
  return {
    xpath: getXPath(element),
    selector: getCSSSelectorForElement(element),
    position: {
      x: Math.round(rect.left + window.scrollX),
      y: Math.round(rect.top + window.scrollY),
      width: Math.round(rect.width),
      height: Math.round(rect.height),
      visible:
        rect.width > 0 && rect.height > 0 && element.offsetParent !== null,
    },
    attributes: Array.from(element.attributes || []).reduce((acc, attr) => {
      acc[attr.name] = attr.value;
      return acc;
    }, {}),
    tagName: element.tagName.toLowerCase(),
  };
}

// Function to generate CSS selector for an element
function getCSSSelectorForElement(element) {
  if (!element || element.nodeType !== Node.ELEMENT_NODE) {
    return null;
  }

  // Use ID if available
  if (element.id) {
    return `#${element.id}`;
  }

  // Build selector path
  const path = [];
  let current = element;

  while (current && current !== document.documentElement) {
    let selector = current.tagName.toLowerCase();

    // Add classes if available
    if (current.className && typeof current.className === "string") {
      const classes = current.className
        .trim()
        .split(/\s+/)
        .filter((c) => c && !c.includes(" "))
        .map((c) => `.${c}`)
        .join("");
      if (classes) {
        selector += classes;
      }
    }

    // Add nth-child if needed for uniqueness
    if (current.parentNode) {
      const siblings = Array.from(current.parentNode.children).filter(
        (child) => child.tagName === current.tagName
      );
      if (siblings.length > 1) {
        const index = siblings.indexOf(current) + 1;
        selector += `:nth-child(${index})`;
      }
    }

    path.unshift(selector);
    current = current.parentNode;
  }

  return path.join(" > ");
}

// Setup interaction tracking
function setupInteractionTracking() {
  // Track clicks
  document.addEventListener(
    "click",
    (event) => {
      const target = event.target;
      const elementContext = getElementContext(target);

      const interaction = {
        type: "click",
        timestamp: new Date().toISOString(),
        element: {
          tag: target.tagName.toLowerCase(),
          id: target.id || null,
          class: target.className || null,
          text: target.textContent?.trim() || null,
          xpath: elementContext.xpath,
          selector: elementContext.selector,
          position: elementContext.position,
          attributes: elementContext.attributes,
        },
        event: {
          clientX: event.clientX,
          clientY: event.clientY,
          pageX: event.pageX,
          pageY: event.pageY,
          button: event.button,
          ctrlKey: event.ctrlKey,
          shiftKey: event.shiftKey,
          altKey: event.altKey,
          metaKey: event.metaKey,
        },
        page: {
          url: window.location.href,
          title: document.title,
          scrollX: window.scrollX,
          scrollY: window.scrollY,
        },
        domState: captureDOMState(),
      };
      console.log("click interaction", interaction);
      sendInteractionToBackground(interaction);
    },
    { capture: true, passive: true }
  );

  // Track mousedown events for better compatibility with elements that might prevent click events
  document.addEventListener(
    "mousedown",
    (event) => {
      const target = event.target;
      const elementContext = getElementContext(target);

      const interaction = {
        type: "mousedown",
        timestamp: new Date().toISOString(),
        element: {
          tag: target.tagName.toLowerCase(),
          id: target.id || null,
          class: target.className || null,
          text: target.textContent?.trim() || null,
          xpath: elementContext.xpath,
          selector: elementContext.selector,
          position: elementContext.position,
          attributes: elementContext.attributes,
        },
        event: {
          clientX: event.clientX,
          clientY: event.clientY,
          pageX: event.pageX,
          pageY: event.pageY,
          button: event.button,
          ctrlKey: event.ctrlKey,
          shiftKey: event.shiftKey,
          altKey: event.altKey,
          metaKey: event.metaKey,
        },
        page: {
          url: window.location.href,
          title: document.title,
          scrollX: window.scrollX,
          scrollY: window.scrollY,
        },
        domState: captureDOMState(),
      };
      console.log("mousedown interaction", interaction);
      sendInteractionToBackground(interaction);
    },
    { capture: true, passive: true }
  );

  // Track input
  document.addEventListener(
    "input",
    (event) => {
      const target = event.target;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
        const elementContext = getElementContext(target);

        const interaction = {
          type: "input",
          timestamp: new Date().toISOString(),
          element: {
            tag: target.tagName.toLowerCase(),
            id: target.id || null,
            class: target.className || null,
            value: target.value || null,
            xpath: elementContext.xpath,
            selector: elementContext.selector,
            position: elementContext.position,
            attributes: elementContext.attributes,
            inputType: target.type || null,
            name: target.name || null,
            placeholder: target.placeholder || null,
          },
          event: {
            inputType: event.inputType || null,
            data: event.data || null,
            isComposing: event.isComposing || false,
          },
          page: {
            url: window.location.href,
            title: document.title,
            scrollX: window.scrollX,
            scrollY: window.scrollY,
          },
          domState: captureDOMState(),
        };
        console.log("input interaction", interaction);
        sendInteractionToBackground(interaction);
      }
    },
    true
  );

  // Track form submissions
  document.addEventListener(
    "submit",
    (event) => {
      const target = event.target;
      const elementContext = getElementContext(target);

      // Collect form data
      const formData = new FormData(target);
      const formFields = {};
      const formElements = [];

      // Get all form elements with their details
      Array.from(target.elements).forEach((element) => {
        if (element.name || element.id) {
          const fieldContext = getElementContext(element);
          formElements.push({
            name: element.name || element.id,
            type: element.type || element.tagName.toLowerCase(),
            value: element.value || null,
            xpath: fieldContext.xpath,
            selector: fieldContext.selector,
            position: fieldContext.position,
          });

          if (element.name) {
            formFields[element.name] = element.value;
          }
        }
      });

      const interaction = {
        type: "submit",
        timestamp: new Date().toISOString(),
        element: {
          tag: target.tagName.toLowerCase(),
          id: target.id || null,
          class: target.className || null,
          action: target.action || null,
          method: target.method || "GET",
          xpath: elementContext.xpath,
          selector: elementContext.selector,
          position: elementContext.position,
          attributes: elementContext.attributes,
        },
        form: {
          fields: formFields,
          elements: formElements,
          enctype: target.enctype || "application/x-www-form-urlencoded",
          target: target.target || "_self",
        },
        event: {
          defaultPrevented: event.defaultPrevented,
          cancelable: event.cancelable,
        },
        page: {
          url: window.location.href,
          title: document.title,
          scrollX: window.scrollX,
          scrollY: window.scrollY,
        },
        domState: captureDOMState(),
      };
      console.log("submit interaction", interaction);
      sendInteractionToBackground(interaction);
    },
    true
  );
}

// Setup interaction tracking immediately
setupInteractionTracking();

class RPCError extends Error {
  message;
  code;
  data;

  constructor(code, message, data) {
    super(message);
    this.code = code;
    this.message = message;
    this.data = data;
  }

  toString() {
    return JSON.stringify({
      code: this.code,
      message: this.message,
      data: this.data,
    });
  }

  toJSON() {
    return {
      code: this.code,
      message: this.message,
      data: this.data,
    };
  }
}

class RPCResponse {
  id;
  result;

  constructor(id, result) {
    this.id = id;
    this.result = result;
  }

  toString() {
    return JSON.stringify({
      id: this.id,
      result: this.result,
    });
  }

  toJSON() {
    return {
      id: this.id,
      result: this.result,
    };
  }
}

// Browser Automation Functions
const BrowserTools = {
  // DOM Selection and Information
  getDOMTree: () => {
    function serializeElement(el) {
      const obj = {
        tag: el.tagName.toLowerCase(),
        attributes: {},
        text:
          el.childNodes.length === 1 &&
          el.childNodes[0].nodeType === Node.TEXT_NODE
            ? el.textContent.trim()
            : null,
        children: [],
      };
      for (let attr of el.attributes) {
        obj.attributes[attr.name] = attr.value;
      }
      for (let child of el.children) {
        obj.children.push(serializeElement(child));
      }
      return obj;
    }

    const domTree = serializeElement(document.body);
    return JSON.stringify(domTree);
  },

  getPageInfo: () => {
    const pageInfo = {
      url: window.location.href,
      title: document.title,
      metadata: {
        description:
          document.querySelector('meta[name="description"]')?.content || null,
        keywords:
          document.querySelector('meta[name="keywords"]')?.content || null,
      },
    };
    return JSON.stringify(pageInfo);
  },

  // Element Selection
  getElementById: (id) => {
    const element = document.getElementById(id);
    return element ? element.outerHTML : "null";
  },

  querySelector: (selector) => {
    const element = document.querySelector(selector);
    return element ? element.outerHTML : "null";
  },

  // Click Actions
  clickLink: (identifier) => {
    const link = Array.from(document.getElementsByTagName("a")).find(
      (a) => a.textContent.trim() === identifier || a.href === identifier
    );
    if (link) {
      link.click();
      return JSON.stringify({
        status: "success",
        message: "Successfully clicked link",
      });
    }
    return JSON.stringify({
      status: "error",
      message: "Link not found",
    });
  },

  clickButton: (identifier) => {
    const button =
      document.getElementById(identifier) ||
      Array.from(document.getElementsByTagName("button")).find(
        (btn) => btn.textContent.trim() === identifier
      );
    if (button) {
      button.click();
      return JSON.stringify({
        status: "success",
        message: "Successfully clicked button",
      });
    }
    return JSON.stringify({
      status: "error",
      message: "Button not found",
    });
  },

  clickElement: (selector) => {
    const element = document.querySelector(selector);
    if (element) {
      element.click();
      return JSON.stringify({
        status: "success",
        message: "Successfully clicked element",
      });
    }
    return JSON.stringify({
      status: "error",
      message: "Element not found",
    });
  },

  // Form Interaction
  typeText: async ({ selector, text, options = {} }) => {
    const element = document.querySelector(selector);
    if (!element) {
      return JSON.stringify({
        status: "error",
        message: "Element not found",
      });
    }

    element.focus();

    if (options.delay) {
      for (let char of text) {
        element.value += char;
        await new Promise((resolve) => setTimeout(resolve, options.delay));
      }
    } else {
      element.value = text;
    }

    // Dispatch input event
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));

    if (options.submitAfter) {
      const form = element.closest("form");
      if (form) {
        form.submit();
      }
    }

    return JSON.stringify({
      status: "success",
      message: "Successfully typed text",
    });
  },

  submitForm: (selector) => {
    const form = document.querySelector(selector);
    if (form) {
      form.submit();
      return JSON.stringify({
        status: "success",
        message: "Successfully submitted form",
      });
    }
    return JSON.stringify({
      status: "error",
      message: "Form not found",
    });
  },

  // Navigation
  navigate: (url) => {
    window.location.href = url;
    return JSON.stringify({
      status: "success",
      message: `Navigating to ${url}`,
    });
  },

  goBack: () => {
    window.history.back();
    return JSON.stringify({
      status: "success",
      message: "Navigating back",
    });
  },

  goForward: () => {
    window.history.forward();
    return JSON.stringify({
      status: "success",
      message: "Navigating forward",
    });
  },

  reload: ({ bypassCache = false } = {}) => {
    window.location.reload(bypassCache);
    return JSON.stringify({
      status: "success",
      message: `Reloading page${bypassCache ? " (bypass cache)" : ""}`,
    });
  },

  // Scrolling and Viewport
  scroll: ({ target }) => {
    if (target === "top") {
      window.scrollTo(0, 0);
    } else if (target === "bottom") {
      window.scrollTo(0, document.body.scrollHeight);
    } else if (target.x !== undefined && target.y !== undefined) {
      window.scrollTo(target.x, target.y);
    }
    return JSON.stringify({
      status: "success",
      message: `Scrolled to ${JSON.stringify(target)}`,
    });
  },

  // JavaScript Execution
  evaluate: async ({ code, args = [] }) => {
    try {
      const fn = new Function(...args.map((_, i) => `arg${i}`), code);
      const result = await fn(...args);
      return JSON.stringify({
        status: "success",
        result: JSON.stringify(result),
      });
    } catch (error) {
      return JSON.stringify({
        status: "error",
        message: error.message,
      });
    }
  },

  // Wait and Timing
  waitForElement: async ({ selector, options = {} }) => {
    const timeout = options.timeout || 5000;
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const element = document.querySelector(selector);
      if (element) {
        if (!options.visible || element.offsetParent !== null) {
          return JSON.stringify({
            status: "success",
            html: element.outerHTML,
          });
        }
      }
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    return JSON.stringify({
      status: "error",
      message: "Element not found or not visible within timeout",
    });
  },

  // Debug tool to check interaction queue state (now handled by background)
  debugInteractionQueue: () => {
    return JSON.stringify({
      status: "success",
      message: "Interaction queue is now managed by background script",
      extensionContextValid: isExtensionContextValid(),
    });
  },

  // Force reconnect tool for debugging
  forceReconnect: () => {
    if (isExtensionContextValid()) {
      try {
        chrome.runtime.sendMessage({ type: "force_reconnect" }, (response) => {
          if (chrome.runtime.lastError) {
            console.warn("Error forcing reconnect:", chrome.runtime.lastError);
          } else {
            console.log("Force reconnect initiated");
          }
        });
      } catch (error) {
        console.warn("Failed to force reconnect:", error);
      }
    }
    return JSON.stringify({
      status: "success",
      message: "Force reconnect initiated",
    });
  },
};

// Add tools to window object
Object.assign(window, BrowserTools);

// Debug: Check if tools are properly assigned
console.log("Content: Checking if tools are assigned to window:");
console.log(
  "Content: window.debugInteractionQueue:",
  typeof window.debugInteractionQueue
);

class WS {
  /**
   * @type {boolean}
   */
  _connected = false;
  _pendingMessages = [];
  _messageCallbacks = new Map();
  _nextMessageId = 1;
  _messageListener = null;
  _reconnectAttempts = 0;
  _maxReconnectAttempts = 5;
  _currentClientSocketId = null;

  /**
   * Connect to the MCP server via background script
   */
  connect() {
    console.log("Content: Connecting to MCP server via background script");

    // Listen for messages from background script (with error handling)
    if (isExtensionContextValid()) {
      try {
        // Remove any existing listener to prevent duplicates
        if (this._messageListener) {
          chrome.runtime.onMessage.removeListener(this._messageListener);
        }

        this._messageListener = (message, sender, sendResponse) => {
          if (message.type === "websocket_connected") {
            console.log("Content: WebSocket connected via background");
            this._connected = true;
            this._reconnectAttempts = 0;
            // Process any pending messages
            this._processPendingMessages();
          } else if (message.type === "websocket_disconnected") {
            console.log("Content: WebSocket disconnected via background");
            this._connected = false;
          } else if (message.type === "websocket_message") {
            this._handleMessage(message.data);
          }
        };

        chrome.runtime.onMessage.addListener(this._messageListener);

        // Check current connection status with retry logic
        this._checkConnectionStatus();
      } catch (error) {
        console.warn("Failed to setup WebSocket communication:", error);
      }
    } else {
      console.warn(
        "Extension context invalidated, WebSocket communication not available"
      );
    }
  }

  _processPendingMessages() {
    if (this._pendingMessages.length > 0) {
      console.log(
        `Content: Processing ${this._pendingMessages.length} pending messages`
      );
      const messages = [...this._pendingMessages];
      this._pendingMessages = [];
      messages.forEach((msg) => this._sendMessage(msg));
    }
  }

  _checkConnectionStatus() {
    if (!isExtensionContextValid()) {
      return;
    }

    chrome.runtime.sendMessage({ type: "websocket_status" }, (response) => {
      if (chrome.runtime.lastError) {
        console.warn(
          "Error checking WebSocket status:",
          chrome.runtime.lastError
        );
        // Retry after a short delay
        setTimeout(() => this._checkConnectionStatus(), 1000);
        return;
      }
      if (response && response.status === "connected") {
        console.log("Content: WebSocket already connected");
        this._connected = true;
        this._reconnectAttempts = 0;
        // Process any pending messages
        this._processPendingMessages();
      } else {
        console.log("Content: WebSocket not connected, requesting connection");
        // Request connection if not connected
        this._requestReconnection();
      }
    });
  }

  _requestReconnection() {
    if (this._reconnectAttempts >= this._maxReconnectAttempts) {
      console.error("Content: Max reconnection attempts reached");
      return;
    }

    this._reconnectAttempts++;
    const delay = Math.min(
      1000 * Math.pow(2, this._reconnectAttempts - 1),
      10000
    );

    console.log(
      `Content: Requesting reconnection in ${delay}ms (attempt ${this._reconnectAttempts}/${this._maxReconnectAttempts})`
    );

    setTimeout(() => {
      chrome.runtime.sendMessage(
        { type: "websocket_reconnect" },
        (response) => {
          if (chrome.runtime.lastError) {
            console.warn(
              "Error requesting reconnection:",
              chrome.runtime.lastError
            );
            this._requestReconnection();
            return;
          }

          // Check status again after reconnection attempt
          setTimeout(() => this._checkConnectionStatus(), 1000);
        }
      );
    }, delay);
  }

  disconnect() {
    console.log("Content: Disconnecting from MCP server");
    this._connected = false;

    // Remove message listener if it exists
    if (this._messageListener && isExtensionContextValid()) {
      try {
        chrome.runtime.onMessage.removeListener(this._messageListener);
        this._messageListener = null;
      } catch (error) {
        console.warn("Error removing message listener:", error);
      }
    }

    // Clear pending messages
    this._pendingMessages = [];
  }

  _sendMessage(message) {
    if (!isExtensionContextValid()) {
      console.warn("Extension context invalidated, cannot send message");
      return;
    }

    if (this._connected) {
      try {
        chrome.runtime.sendMessage(
          {
            type: "websocket_send",
            data: message,
          },
          (response) => {
            if (chrome.runtime.lastError) {
              console.warn(
                "Error sending message to background:",
                chrome.runtime.lastError
              );
              // Mark as disconnected and try to reconnect
              this._connected = false;
              this._checkConnectionStatus();
              return;
            }
            if (response && response.status === "error") {
              console.error("Content: Error sending message:", response.error);
              // If it's a connection error, try to reconnect
              if (response.error && response.error.includes("not connected")) {
                this._connected = false;
                this._checkConnectionStatus();
              }
            }
          }
        );
      } catch (error) {
        console.warn("Failed to send message to background:", error);
        // Mark as disconnected and try to reconnect
        this._connected = false;
        this._checkConnectionStatus();
      }
    } else {
      // Queue message for when connection is established
      this._pendingMessages.push(message);
      console.log(
        `Content: Queued message, total pending: ${this._pendingMessages.length}`
      );
      // Try to reconnect if not connected
      this._checkConnectionStatus();
    }
  }

  _handleMessage(message) {
    try {
      console.log("Content: Received message from MCP server:", message);
      const { id, method, params } = message;
      console.log("method:", method);
      console.log("params:", params);

      this.handle(method, params)
        .then((res) => {
          console.log("Content: Tool call successful, result:", res);
          this.response(id, res);
        })
        .catch((e) => {
          console.error("Content: Tool call failed:", e);
          this.error(
            id,
            e instanceof RPCError
              ? e
              : new RPCError(RPCErrorCodes.InternalError, e.message, e)
          );
        });
    } catch (e) {
      console.error("Content: Error handling message:", e);
      this.error(
        null,
        e instanceof RPCError
          ? e
          : new RPCError(RPCErrorCodes.InternalError, e.message, e)
      );
    }
  }

  /**
   * handle MCP server request
   * @param {string} method - method path, format as "object.innerObject.func" or "object.innerObject.attribute"
   * @param {Array} params - parameters array
   * @returns {Promise<any>} method execution result or attribute value
   */
  async handle(method, params = []) {
    try {
      console.log("Content: Handling method:", method, "with params:", params);
      const parts = method.split(".");
      const mcpMethod = parts.shift();
      let current = window;
      let i = 0;

      console.log("Content: MCP method:", mcpMethod, "parts:", parts);

      while (i < parts.length - 1) {
        const part = parts[i];
        if (!current[part]) {
          console.error(
            "Content: Object not found:",
            parts.slice(0, i + 1).join(".")
          );
          throw new RPCError(
            RPCErrorCodes.MethodNotFound,
            `Object '${parts.slice(0, i + 1).join(".")}' not found in context`,
            { path: parts.slice(0, i + 1).join(".") }
          );
        }
        current = current[part];
        i++;
      }

      const lastPart = parts[parts.length - 1];
      const target = current[lastPart];
      console.log(
        "Content: Target:",
        lastPart,
        "found:",
        typeof target,
        target
      );

      // resource Return value
      if (mcpMethod === MCPCallTag.Resource) {
        if (target === undefined) {
          throw new RPCError(
            RPCErrorCodes.MethodNotFound,
            `Resource '${method}' not found`,
            { method }
          );
        }
        return target;
      }

      if (mcpMethod === MCPCallTag.Tool) {
        if (typeof target !== "function") {
          console.error(
            "Content: Target is not a function:",
            typeof target,
            target
          );
          throw new RPCError(
            RPCErrorCodes.MethodNotFound,
            `Method '${method}' is not a function`,
            { method }
          );
        }

        console.log("Content: Calling function:", lastPart);
        const result = await target.apply(current, params);
        console.log("Content: Function result:", result);
        return result;
      }

      throw new RPCError(
        RPCErrorCodes.MethodNotFound,
        `Method '${method}' is not a valid type`,
        { method }
      );
    } catch (error) {
      if (error instanceof RPCError) {
        throw error;
      }

      throw new RPCError(
        RPCErrorCodes.InternalError,
        `Error processing '${method}': ${error.message}`,
        { method, error: error.message }
      );
    }
  }

  /**
   * send success response
   * @param {string} id - request id
   * @param {any} result - response result
   */
  response(id, result) {
    console.log("Content: send response:", id, result);
    const response = new RPCResponse(id, result);
    // Send response via background script
    this._sendMessage(response);
  }

  /**
   * send error response
   * @param {string} id - request id
   * @param {RPCError} error - error object
   */
  error(id, error) {
    console.error("Content: send error:", id, error);
    this._sendMessage({ id, error: error.toJSON() });
  }
}

// Extension debug code
(function debugExtension() {
  document.addEventListener("DOMContentLoaded", () => {
    // Page DOM loaded
  });

  // Create a visual element to confirm extension is running
  try {
    const debugElement = document.createElement("div");
    debugElement.style.position = "fixed";
    debugElement.style.top = "10px";
    debugElement.style.right = "10px";
    debugElement.style.zIndex = "9999";
    debugElement.style.background = "rgba(255,0,0,0.3)";
    debugElement.style.padding = "5px";
    debugElement.style.borderRadius = "3px";
    debugElement.style.fontSize = "12px";
    debugElement.textContent = "MCP Extension Loaded";

    // Wait for DOM ready
    if (document.body) {
      document.body.appendChild(debugElement);
    } else {
      document.addEventListener("DOMContentLoaded", () => {
        document.body.appendChild(debugElement);
      });
    }
  } catch (e) {
    console.error("create debug element failed:", e);
  }
})();

// Initialize MCP client
function initializeMcpClient() {
  console.log("McpExtensionClient: Initializing...");

  // Check if already initialized
  if (window.McpExtensionClient) {
    console.log("McpExtensionClient: Already exists, reconnecting...");
    window.McpExtensionClient.disconnect();
  }

  const McpExtensionClient = new WS();
  McpExtensionClient.connect();
  window.McpExtensionClient = McpExtensionClient;
  console.log("McpExtensionClient Established");
}

// Initialize immediately
initializeMcpClient();

// Also initialize when DOM is ready (for cases where script loads before DOM)
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    console.log("McpExtensionClient: DOM ready, ensuring connection...");
    if (window.McpExtensionClient) {
      window.McpExtensionClient._checkConnectionStatus();
    }
  });
}

// Registration is now handled by handleReinjection() function

// Periodic health check to ensure connection stays alive
setInterval(() => {
  if (window.McpExtensionClient && !window.McpExtensionClient._connected) {
    console.log(
      "McpExtensionClient: Health check - connection lost, checking status..."
    );
    window.McpExtensionClient._checkConnectionStatus();
  }
}, 10000); // Check every 10 seconds

// Detect if this is a re-injected content script
function handleReinjection() {
  if (window.McpExtensionReinjected) {
    console.log("Content: Re-injection detected, cleaning up previous instance");
    
    // Clean up previous instance
    if (window.McpExtensionClient) {
      try {
        window.McpExtensionClient.disconnect();
      } catch (error) {
        console.warn("Content: Error cleaning up previous client:", error);
      }
    }
  }
  
  // Mark this as re-injected
  window.McpExtensionReinjected = true;
  
  // Re-initialize everything
  console.log("Content: Initializing fresh content script instance");
  registerWithBackground();
}

// Handle re-injection scenarios
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', handleReinjection);
} else {
  handleReinjection();
}

// Cleanup function for when content script is being destroyed
window.addEventListener("beforeunload", () => {
  // Disconnect MCP client
  if (window.McpExtensionClient) {
    window.McpExtensionClient.disconnect();
  }
  
  // Clear re-injection marker
  delete window.McpExtensionReinjected;
});
