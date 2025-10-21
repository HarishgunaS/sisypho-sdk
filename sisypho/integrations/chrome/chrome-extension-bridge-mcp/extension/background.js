// Background script to maintain persistent WebSocket connection
// This keeps the connection alive across page navigations

let ws = null;
let isConnected = false;
let reconnectAttempts = 0;
const maxReconnectAttempts = 10;
const reconnectDelay = 2000; // 2 seconds
let connectionCheckInterval = null;
let keepAliveInterval = null;

// Tab management
let activeTabs = new Set(); // Track tabs with active content scripts
let tabStates = new Map(); // Track state of each tab
let pendingMessages = new Map(); // Queue messages for tabs that aren't ready yet

// Interaction queue management
let interactionQueue = [];
const INTERACTION_QUEUE_KEY = "mcp_interaction_queue";

// Load interaction queue from storage on initialization
function loadInteractionQueue() {
  console.log("Background: Loading interaction queue from storage");
  chrome.storage.local.get([INTERACTION_QUEUE_KEY], (result) => {
    if (chrome.runtime.lastError) {
      console.warn(
        "Background: Error loading interaction queue:",
        chrome.runtime.lastError
      );
      return;
    }
    const storedInteractions = result[INTERACTION_QUEUE_KEY] || [];
    interactionQueue = storedInteractions;
    console.log(
      "Background: Loaded interaction queue from storage:",
      interactionQueue.length,
      "items"
    );
  });
}

// Save interaction queue to storage
function saveInteractionQueue() {
  chrome.storage.local.set(
    { [INTERACTION_QUEUE_KEY]: interactionQueue },
    () => {
      if (chrome.runtime.lastError) {
        console.warn(
          "Background: Error saving interaction queue:",
          chrome.runtime.lastError
        );
        return;
      }
      console.log(
        "Background: Saved interaction queue to storage:",
        interactionQueue.length,
        "items"
      );
    }
  );
}

// Add interaction to queue
function addInteraction(interaction) {
  interactionQueue.push(interaction);
  console.log(
    "Background: Added interaction to queue, total:",
    interactionQueue.length
  );
  saveInteractionQueue();
}

// Get and clear interaction queue
function getAndClearInteractionQueue() {
  const interactions = [...interactionQueue];
  interactionQueue = [];
  console.log(
    "Background: Retrieved and cleared interaction queue, returned:",
    interactions.length,
    "items"
  );
  saveInteractionQueue();
  return interactions;
}

// Get current queue size
function getInteractionQueueSize() {
  return interactionQueue.length;
}

// Tab management functions
function addActiveTab(tabId) {
  activeTabs.add(tabId);
  tabStates.set(tabId, {
    connected: false,
    lastSeen: Date.now(),
    url: null,
    ready: false,
  });
  console.log(
    `Background: Added active tab ${tabId}, total active tabs: ${activeTabs.size}`
  );

  // Send any pending messages for this tab
  sendPendingMessages(tabId);
}

function removeActiveTab(tabId) {
  activeTabs.delete(tabId);
  tabStates.delete(tabId);
  pendingMessages.delete(tabId);
  console.log(
    `Background: Removed active tab ${tabId}, total active tabs: ${activeTabs.size}`
  );
}

function updateTabState(tabId, state) {
  if (tabStates.has(tabId)) {
    const currentState = tabStates.get(tabId);
    tabStates.set(tabId, { ...currentState, ...state, lastSeen: Date.now() });
  }
}

function getActiveTabs() {
  return Array.from(activeTabs);
}

function isTabActive(tabId) {
  return activeTabs.has(tabId);
}

function sendPendingMessages(tabId) {
  if (pendingMessages.has(tabId)) {
    const messages = pendingMessages.get(tabId);
    console.log(
      `Background: Sending ${messages.length} pending messages to tab ${tabId}`
    );

    messages.forEach((message) => {
      chrome.tabs.sendMessage(tabId, message).catch((error) => {
        console.log(
          `Background: Failed to send pending message to tab ${tabId}:`,
          error.message
        );
      });
    });

    pendingMessages.delete(tabId);
  }
}

function queueMessageForTab(tabId, message) {
  if (!pendingMessages.has(tabId)) {
    pendingMessages.set(tabId, []);
  }
  pendingMessages.get(tabId).push(message);
  console.log(
    `Background: Queued message for tab ${tabId}, total pending: ${
      pendingMessages.get(tabId).length
    }`
  );
}

// WebSocket connection management
function connectWebSocket() {
  if (ws && isConnected) {
    console.log("Background: WebSocket already connected");
    return;
  }

  // Prevent multiple simultaneous connection attempts
  if (ws && ws.readyState === WebSocket.CONNECTING) {
    console.log("Background: WebSocket connection already in progress");
    return;
  }

  try {
    console.log("Background: Attempting to connect to WebSocket...");
    ws = new WebSocket("ws://localhost:54319");

    ws.onopen = () => {
      console.log("Background: WebSocket connected to MCP server");
      isConnected = true;
      reconnectAttempts = 0;
      
      // Update badge to show connected status
      updateConnectionBadge(true);

      // Start keep-alive mechanism (every 20 seconds to prevent service worker termination)
      if (keepAliveInterval) {
        clearInterval(keepAliveInterval);
      }
      keepAliveInterval = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          try {
            ws.send(JSON.stringify({ type: "keepalive" }));
            console.log("Background: Sent keepalive message");
          } catch (error) {
            console.warn("Background: Failed to send keepalive:", error);
          }
        } else {
          clearInterval(keepAliveInterval);
          keepAliveInterval = null;
        }
      }, 20000); // Every 20 seconds

      // Start connection health check
      if (connectionCheckInterval) {
        clearInterval(connectionCheckInterval);
      }
      connectionCheckInterval = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          try {
            ws.send(JSON.stringify({ type: "ping" }));
          } catch (error) {
            console.warn(
              "Background: Ping failed, connection lost:",
              error
            );
            isConnected = false;
            if (ws) {
              ws.close();
            }
            // Notify popup that connection was lost
            notifyPopupStatusChange(false, "Connection lost");
          }
        } else if (ws && ws.readyState !== WebSocket.CONNECTING) {
          console.warn(
            "Background: WebSocket not in OPEN state, connection lost"
          );
          isConnected = false;
          if (ws) {
            ws.close();
          }
          // Notify popup that connection was lost
          notifyPopupStatusChange(false, "Connection lost");
        }
      }, 10000); // Check every 10 seconds

      // Notify active content scripts that connection is ready
      const activeTabIds = getActiveTabs();
      activeTabIds.forEach((tabId) => {
        const tabState = tabStates.get(tabId);
        if (tabState && tabState.ready) {
          chrome.tabs
            .sendMessage(tabId, {
              type: "websocket_connected",
              status: "connected",
            })
            .then(() => {
              updateTabState(tabId, { connected: true });
              console.log(
                "Background: Notified active tab of connection:",
                tabId
              );
            })
            .catch((error) => {
              console.log(
                "Background: Could not notify tab of connection:",
                tabId,
                error.message
              );
              removeActiveTab(tabId);
            });
        } else {
          // Queue the connection message for when the tab is ready
          queueMessageForTab(tabId, {
            type: "websocket_connected",
            status: "connected",
          });
        }
      });
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        console.log("Background: Received message from MCP server:", message);

        // Handle retrieve_write_interaction_queue tool locally
        if (message.method === "mcp:tool.retrieve_write_interaction_queue") {
          console.log(
            "Background: Handling retrieve_write_interaction_queue locally"
          );
          const interactions = getAndClearInteractionQueue();
          const response = {
            id: message.id,
            result: JSON.stringify({
              status: "success",
              interactions: interactions,
            }),
          };
          ws.send(JSON.stringify(response));
          return;
        }

        // Handle getInteractionQueueSize tool locally
        if (message.method === "mcp:tool.getInteractionQueueSize") {
          console.log("Background: Handling getInteractionQueueSize locally");
          const size = getInteractionQueueSize();
          const response = {
            id: message.id,
            result: JSON.stringify({
              status: "success",
              size: size,
            }),
          };
          ws.send(JSON.stringify(response));
          return;
        }

        // Forward other messages to active tabs with content scripts
        const activeTabIds = getActiveTabs();
        if (activeTabIds.length === 0) {
          console.warn(
            "Background: No active tabs available to receive MCP message"
          );
          // Send error response back to MCP server instead of just returning
          if (message.id) {
            const errorResponse = {
              id: message.id,
              error: {
                code: -32603,
                message: "No active tabs available to receive MCP message",
              },
            };
            ws.send(JSON.stringify(errorResponse));
          }
          return;
        }

        let messageSent = false;
        activeTabIds.forEach((tabId) => {
          const tabState = tabStates.get(tabId);
          if (tabState && tabState.ready) {
            chrome.tabs
              .sendMessage(tabId, {
                type: "websocket_message",
                data: message,
              })
              .then(() => {
                messageSent = true;
                console.log(
                  "Background: Message forwarded to active tab:",
                  tabId
                );
              })
              .catch((error) => {
                // Tab might have been closed or content script destroyed
                console.log(
                  "Background: Could not send message to active tab:",
                  tabId,
                  error.message
                );
                // Remove inactive tab
                removeActiveTab(tabId);
              });
          } else {
            // Queue the message for when the tab is ready
            queueMessageForTab(tabId, {
              type: "websocket_message",
              data: message,
            });
            messageSent = true; // Consider it "sent" since it's queued
          }
        });

        // Log if no message was sent to any tab
        setTimeout(() => {
          if (!messageSent) {
            console.warn(
              "Background: No active tabs could receive MCP message"
            );
            // Send error response back to MCP server
            if (message.id) {
              const errorResponse = {
                id: message.id,
                error: {
                  code: -32603,
                  message: "No active tabs could receive MCP message",
                },
              };
              ws.send(JSON.stringify(errorResponse));
            }
          }
        }, 100);
      } catch (error) {
        console.error("Background: Error parsing WebSocket message:", error);
      }
    };

    ws.onclose = (event) => {
      console.log(
        "Background: WebSocket connection closed:",
        event.code,
        event.reason
      );
      isConnected = false;
      
      // Update badge to show disconnected status
      updateConnectionBadge(false);

      // Clear keep-alive interval
      if (keepAliveInterval) {
        clearInterval(keepAliveInterval);
        keepAliveInterval = null;
      }

      // Clear connection health check
      if (connectionCheckInterval) {
        clearInterval(connectionCheckInterval);
        connectionCheckInterval = null;
      }

      // Notify active content scripts that connection is lost
      const activeTabIds = getActiveTabs();
      activeTabIds.forEach((tabId) => {
        const tabState = tabStates.get(tabId);
        if (tabState && tabState.ready) {
          chrome.tabs
            .sendMessage(tabId, {
              type: "websocket_disconnected",
              status: "disconnected",
            })
            .then(() => {
              updateTabState(tabId, { connected: false });
              console.log(
                "Background: Notified active tab of disconnection:",
                tabId
              );
            })
            .catch((error) => {
              console.log(
                "Background: Could not notify tab of disconnection:",
                tabId,
                error.message
              );
              removeActiveTab(tabId);
            });
        } else {
          // Queue the disconnection message for when the tab is ready
          queueMessageForTab(tabId, {
            type: "websocket_disconnected",
            status: "disconnected",
          });
        }
      });

      // No automatic reconnection - user must manually reconnect via popup
      console.log("Background: Connection lost. Use popup to manually reconnect.");
      notifyPopupStatusChange(false, "Connection lost - manual reconnection required");
    };

    ws.onerror = (error) => {
      console.error("Background: WebSocket error:", {
        type: error.type,
        message: error.message || "Unknown WebSocket error",
        error: error.error || error,
        readyState: ws ? ws.readyState : "unknown",
      });

      isConnected = false;
    };
  } catch (error) {
    console.error("Background: Error creating WebSocket connection:", error);
    isConnected = false;

    // No automatic reconnection - user must manually reconnect via popup
    console.log("Background: Connection error. Use popup to manually reconnect.");
    notifyPopupStatusChange(false, "Connection error - manual reconnection required");
  }
}

// Handle messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log(
    "Background: Received message from content script:",
    message.type,
    "from tab:",
    sender.tab?.id,
    "with data:",
    message.data
  );

  // Add timeout to prevent blocking
  const timeoutId = setTimeout(() => {
    console.warn(
      "Background: Message response timeout, sending error response for:",
      message.type
    );
    sendResponse({ status: "error", error: "Response timeout" });
  }, 2000); // 2 second timeout

  // Add error handling wrapper
  const safeSendResponse = (response) => {
    try {
      clearTimeout(timeoutId);
      sendResponse(response);
    } catch (error) {
      console.error("Background: Error sending response:", error);
    }
  };

  if (message.type === "websocket_send") {
    // Check if connected before sending (no auto-connect)
    if (!isConnected || !ws || ws.readyState !== WebSocket.OPEN) {
      console.log(
        "Background: WebSocket not connected. Use popup to manually connect."
      );
      safeSendResponse({ 
        status: "not_connected", 
        error: "Not connected to MCP server. Use popup to connect manually." 
      });
      return true;
    }

    try {
      ws.send(JSON.stringify(message.data));
      safeSendResponse({ status: "sent" });
    } catch (error) {
      console.error("Background: Error sending WebSocket message:", error);
      // Mark as disconnected but don't auto-reconnect
      isConnected = false;
      updateConnectionBadge(false);
      safeSendResponse({ status: "error", error: error.message });
    }
    return true; // Keep the message channel open for async response
  }

  if (message.type === "websocket_status") {
    // Just return status, no auto-connect
    safeSendResponse({
      status: isConnected ? "connected" : "disconnected",
      reconnectAttempts: reconnectAttempts,
    });
    return true;
  }

  if (message.type === "websocket_reconnect") {
    // This is now handled by manual_connect - redirect to that
    console.log("Background: Reconnect request redirected to manual connection");
    safeSendResponse({ status: "use_manual_connect", message: "Use popup to manually connect" });
    return true;
  }

  if (message.type === "content_script_destroyed") {
    const tabId = sender.tab?.id;
    console.log("Background: Content script destroyed for tab:", tabId);
    if (tabId) {
      removeActiveTab(tabId);
    }
    // No response needed for this event
    clearTimeout(timeoutId);
    return false;
  }

  if (message.type === "content_script_ready") {
    const tabId = sender.tab?.id;
    console.log("Background: Content script ready for tab:", tabId);
    if (tabId) {
      addActiveTab(tabId);
      updateTabState(tabId, { ready: true });

      // If we're already connected, notify this tab immediately
      if (isConnected) {
        chrome.tabs
          .sendMessage(tabId, {
            type: "websocket_connected",
            status: "connected",
          })
          .then(() => {
            updateTabState(tabId, { connected: true });
            console.log(
              "Background: Immediately notified new tab of connection:",
              tabId
            );
          })
          .catch((error) => {
            console.log(
              "Background: Could not notify new tab of connection:",
              tabId,
              error.message
            );
            removeActiveTab(tabId);
          });
      }

      // Send any pending messages for this tab
      sendPendingMessages(tabId);
    }
    safeSendResponse({ status: "registered" });
    return true;
  }

  if (message.type === "get_tab_status") {
    safeSendResponse({
      status: "success",
      activeTabs: getActiveTabs(),
      tabStates: Object.fromEntries(tabStates),
      totalActiveTabs: activeTabs.size,
      websocketConnected: isConnected,
    });
    return true;
  }

  if (message.type === "force_reconnect") {
    console.log("Background: Force reconnect requested");
    if (ws) {
      ws.close();
    }
    reconnectAttempts = 0;
    connectWebSocket();
    safeSendResponse({ status: "reconnecting" });
    return true;
  }

  if (message.type === "add_interaction") {
    console.log("Background: Received interaction from content script");
    addInteraction(message.interaction);
    safeSendResponse({ status: "added" });
    return true;
  }

  if (message.type === "get_interaction_queue_size") {
    const size = getInteractionQueueSize();
    safeSendResponse({ status: "success", size: size });
    return true;
  }

  // Manual connection/disconnection handlers for popup
  if (message.type === "manual_connect") {
    console.log("Background: Manual connect requested");
    
    if (isConnected && ws && ws.readyState === WebSocket.OPEN) {
      safeSendResponse({ success: true, message: "Already connected" });
      return true;
    }
    
    // Reset reconnection attempts for manual connection
    reconnectAttempts = 0;
    
    connectWebSocket();
    
    // Wait a moment to see if connection succeeds
    setTimeout(() => {
      if (isConnected && ws && ws.readyState === WebSocket.OPEN) {
        safeSendResponse({ success: true, message: "Connected successfully" });
        // Notify popup of status change
        notifyPopupStatusChange(true);
      } else {
        const errorMsg = ws && ws.readyState === WebSocket.CONNECTING 
          ? "Connection in progress..." 
          : "Failed to connect to MCP server. Make sure it's running on localhost:54319";
        safeSendResponse({ success: false, error: errorMsg });
        notifyPopupStatusChange(false, errorMsg);
      }
    }, 1000);
    
    return true;
  }

  if (message.type === "manual_disconnect") {
    console.log("Background: Manual disconnect requested");
    
    if (ws) {
      ws.close();
    }
    isConnected = false;
    reconnectAttempts = maxReconnectAttempts; // Prevent auto-reconnection
    
    // Clear keep-alive interval
    if (keepAliveInterval) {
      clearInterval(keepAliveInterval);
      keepAliveInterval = null;
    }
    
    // Clear connection check interval to prevent auto-reconnection
    if (connectionCheckInterval) {
      clearInterval(connectionCheckInterval);
      connectionCheckInterval = null;
    }
    
    safeSendResponse({ success: true, message: "Disconnected successfully" });
    // Notify popup of status change
    notifyPopupStatusChange(false);
    return true;
  }

  if (message.type === "get_connection_status") {
    safeSendResponse({ 
      connected: isConnected,
      activeTabs: activeTabs.size,
      reconnectAttempts: reconnectAttempts
    });
    return true;
  }
});

// Notify popup of connection status changes and update badge
function notifyPopupStatusChange(connected, error = null) {
  // Update extension badge
  updateConnectionBadge(connected);
  
  // Notify popup if it's open
  try {
    chrome.runtime.sendMessage({
      type: 'connection_status_changed',
      connected: connected,
      error: error
    });
  } catch (e) {
    // Popup might not be open, which is fine
    console.log('Background: Could not notify popup of status change:', e.message);
  }
}

// Update extension badge based on connection status
function updateConnectionBadge(connected) {
  if (connected) {
    chrome.action.setBadgeText({text: "ON"});
    chrome.action.setBadgeBackgroundColor({color: [0, 200, 0, 255]}); // Green
    chrome.action.setTitle({title: "MCP Extension - Connected to localhost:54319"});
  } else {
    chrome.action.setBadgeText({text: "OFF"});
    chrome.action.setBadgeBackgroundColor({color: [200, 0, 0, 255]}); // Red
    chrome.action.setTitle({title: "MCP Extension - Disconnected (Click to connect)"});
  }
}

// Re-inject content scripts into existing tabs
async function reinjectContentScripts() {
  try {
    console.log("Background: Re-injecting content scripts into existing tabs...");
    const tabs = await chrome.tabs.query({
      url: ["http://*/*", "https://*/*"]
    });
    
    let successCount = 0;
    let failCount = 0;
    
    for (const tab of tabs) {
      try {
        await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          files: ['content.js']
        });
        console.log(`Background: Re-injected content script into tab ${tab.id} (${tab.url})`);
        successCount++;
      } catch (error) {
        console.log(`Background: Failed to inject into tab ${tab.id}: ${error.message}`);
        failCount++;
      }
    }
    
    console.log(`Background: Content script re-injection complete. Success: ${successCount}, Failed: ${failCount}`);
  } catch (error) {
    console.error('Background: Failed to re-inject content scripts:', error);
  }
}

// Initialize extension on install/update (NO automatic connection)
chrome.runtime.onInstalled.addListener(async (details) => {
  console.log(`Background: Extension ${details.reason} detected`);
  
  // Re-inject content scripts for install/update scenarios
  if (details.reason === 'install' || details.reason === 'update') {
    console.log("Background: Performing content script re-injection...");
    await reinjectContentScripts();
  }
  
  console.log("Background: Extension initialized. Use popup to manually connect to MCP server.");
  // Load interaction queue on startup
  loadInteractionQueue();
  // Initialize badge as disconnected
  updateConnectionBadge(false);
});

// Handle tab lifecycle events
chrome.tabs.onCreated.addListener((tab) => {
  console.log("Background: New tab created:", tab.id);
  // Don't add to active tabs yet - wait for content script to register
});

chrome.tabs.onRemoved.addListener((tabId, removeInfo) => {
  console.log("Background: Tab removed:", tabId);
  if (isTabActive(tabId)) {
    removeActiveTab(tabId);
  }
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (
    changeInfo.status === "complete" &&
    tab.url &&
    tab.url.startsWith("http")
  ) {
    console.log(
      "Background: Tab updated, ensuring WebSocket connection is active:",
      tabId
    );

    // Update tab state with new URL
    if (isTabActive(tabId)) {
      updateTabState(tabId, { url: tab.url });
    }

    // Log connection status but don't auto-connect
    if (!isConnected || !ws || ws.readyState !== WebSocket.OPEN) {
      console.log(
        "Background: WebSocket not connected. Use popup to manually connect to MCP server."
      );
    }
  }
});

// Periodic cleanup of stale tabs
setInterval(() => {
  const now = Date.now();
  const staleThreshold = 15000; // 15 seconds

  activeTabs.forEach((tabId) => {
    const state = tabStates.get(tabId);
    if (state && now - state.lastSeen > staleThreshold) {
      console.log(
        `Background: Removing stale tab ${tabId} (last seen ${Math.round(
          (now - state.lastSeen) / 1000
        )}s ago)`
      );
      removeActiveTab(tabId);
    }
  });
}, 30000); // Check every 30 seconds

// Handle extension shutdown
chrome.runtime.onSuspend.addListener(() => {
  console.log("Background: Extension suspending, closing WebSocket...");
  if (keepAliveInterval) {
    clearInterval(keepAliveInterval);
    keepAliveInterval = null;
  }
  if (connectionCheckInterval) {
    clearInterval(connectionCheckInterval);
    connectionCheckInterval = null;
  }
  if (ws) {
    ws.close();
  }
});

console.log("Background: MCP WebSocket bridge initialized");
