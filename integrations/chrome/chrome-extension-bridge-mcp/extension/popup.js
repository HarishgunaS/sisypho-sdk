// Popup script for MCP Extension
// Handles manual connection/disconnection controls

document.addEventListener('DOMContentLoaded', function() {
  const connectBtn = document.getElementById('connectBtn');
  const disconnectBtn = document.getElementById('disconnectBtn');
  const statusDiv = document.getElementById('status');
  const activeTabsSpan = document.getElementById('activeTabs');
  const errorMessage = document.getElementById('errorMessage');

  // Initialize popup state
  updateUI();

  // Connect button handler
  connectBtn.addEventListener('click', function() {
    console.log('Popup: Connect button clicked');
    updateStatus('connecting', 'Connecting...');
    connectBtn.disabled = true;
    
    // Send connect message to background script
    chrome.runtime.sendMessage(
      { type: 'manual_connect' },
      function(response) {
        console.log('Popup: Connect response:', response);
        
        if (chrome.runtime.lastError) {
          console.error('Popup: Runtime error:', chrome.runtime.lastError);
          showError('Extension error: ' + chrome.runtime.lastError.message);
          updateStatus('disconnected', 'Disconnected');
          connectBtn.disabled = false;
          return;
        }
        
        if (response && response.success) {
          updateStatus('connected', 'Connected');
          updateButtonVisibility(false, true);
          hideError();
        } else {
          const errorMsg = response ? response.error : 'Unknown connection error';
          showError('Connection failed: ' + errorMsg + '\n\nMake sure you have started recording on the Sisypho macOS app.');
          updateStatus('disconnected', 'Disconnected');
          connectBtn.disabled = false;
        }
      }
    );
  });

  // Disconnect button handler
  disconnectBtn.addEventListener('click', function() {
    console.log('Popup: Disconnect button clicked');
    
    // Send disconnect message to background script
    chrome.runtime.sendMessage(
      { type: 'manual_disconnect' },
      function(response) {
        console.log('Popup: Disconnect response:', response);
        
        if (chrome.runtime.lastError) {
          console.error('Popup: Runtime error:', chrome.runtime.lastError);
          showError('Extension error: ' + chrome.runtime.lastError.message);
          return;
        }
        
        updateStatus('disconnected', 'Disconnected');
        updateButtonVisibility(true, false);
        hideError();
      }
    );
  });

  // Update UI based on current connection state
  function updateUI() {
    chrome.runtime.sendMessage(
      { type: 'get_connection_status' },
      function(response) {
        if (chrome.runtime.lastError) {
          console.error('Popup: Error getting status:', chrome.runtime.lastError);
          updateStatus('disconnected', 'Disconnected');
          updateButtonVisibility(true, false);
          return;
        }
        
        if (response) {
          const isConnected = response.connected;
          const statusText = isConnected ? 'Connected' : 'Disconnected';
          const statusClass = isConnected ? 'connected' : 'disconnected';
          
          updateStatus(statusClass, statusText);
          updateButtonVisibility(!isConnected, isConnected);
          
          // Update active tabs count
          if (response.activeTabs !== undefined) {
            activeTabsSpan.textContent = response.activeTabs;
          }
        }
      }
    );
  }

  // Update status display
  function updateStatus(statusClass, statusText) {
    statusDiv.className = `status ${statusClass}`;
    statusDiv.textContent = `Status: ${statusText}`;
  }

  // Update button visibility
  function updateButtonVisibility(showConnect, showDisconnect) {
    connectBtn.style.display = showConnect ? 'block' : 'none';
    disconnectBtn.style.display = showDisconnect ? 'block' : 'none';
    connectBtn.disabled = false;
  }

  // Show error message
  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
  }

  // Hide error message
  function hideError() {
    errorMessage.style.display = 'none';
  }

  // Listen for status updates from background script
  chrome.runtime.onMessage.addListener(function(message, sender, sendResponse) {
    if (message.type === 'connection_status_changed') {
      console.log('Popup: Connection status changed:', message.connected);
      
      const isConnected = message.connected;
      const statusText = isConnected ? 'Connected' : 'Disconnected';
      const statusClass = isConnected ? 'connected' : 'disconnected';
      
      updateStatus(statusClass, statusText);
      updateButtonVisibility(!isConnected, isConnected);
      
      if (message.error) {
        showError(message.error + '\n\nMake sure you have started recording on the Sisypho macOS app.');
      } else {
        hideError();
      }
    }
    
    if (message.type === 'active_tabs_changed') {
      activeTabsSpan.textContent = message.count;
    }
  });

  // Refresh status every 5 seconds to stay in sync
  setInterval(updateUI, 5000);
});