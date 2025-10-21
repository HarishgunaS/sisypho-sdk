const SelectionCommands = {
  SELECT_ENTIRE_DOM: "select_entire_dom",
  PRESS_LINK: "press_link",
  PRESS_BUTTON: "press_button",
  SELECT_ELEMENT_WITH_ID: "select_element_with_id",
};

function initNativeHostAndInject(tabId, url) {
  console.log("initNativeHostAndInject", tabId, url);
  if (
    url.startsWith("chrome://") ||
    url.startsWith("https://chrome.google.com/webstore") ||
    url.includes(".pdf")
  ) {
    console.warn("Blocked script injection into restricted URL:", url);
    return;
  }

  chrome.runtime.sendNativeMessage(
    "com.example.sisypho_host",
    { message: "init" },
    (response) => {
      console.log("response", response);
      if (chrome.runtime.lastError) {
        console.error("Native message error:", chrome.runtime.lastError.message || chrome.runtime.lastError);
        return;
      }

      if (response && response.command) {
        const command = response.command;
        const param = response.param;

        if (command === SelectionCommands.SELECT_ENTIRE_DOM) {
          chrome.scripting.executeScript({
            target: { tabId },
            func: () => {
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

              const domTree = document.body
                ? serializeElement(document.body)
                : null;

              chrome.runtime.sendMessage({
                type: "dom_tree",
                data: domTree,
              });
            },
          });
        }

        if (command === SelectionCommands.SELECT_ELEMENT_WITH_ID) {
          chrome.scripting.executeScript({
            target: { tabId },
            func: (elementId) => {
              const el = document.getElementById(elementId);
              const elString = el ? el.outerHTML : null;
              chrome.runtime.sendMessage({
                type: "element_by_id",
                data: elString,
              });
            },
            args: [param],
          });
        }

        if (command === SelectionCommands.PRESS_LINK) {
          chrome.scripting.executeScript({
            target: { tabId },
            func: (href) => {
              const link = document.querySelector(`a[href="${href}"]`);
              if (link) {
                link.click();
                chrome.runtime.sendMessage({
                  type: "operation_status",
                  command: "press_link",
                  status: "success",
                });
              } else {
                chrome.runtime.sendMessage({
                  type: "operation_status",
                  command: "press_link",
                  status: "failure",
                });
              }
            },
            args: [param],
          });
        }

        if (command === SelectionCommands.PRESS_BUTTON) {
          console.log("PRESS_BUTTON", param);
          chrome.scripting.executeScript({
            target: { tabId },
            func: (identifier) => {
              const button =
                document.querySelector(`button#${identifier}`) ||
                Array.from(document.querySelectorAll("button")).find(
                  (btn) =>
                    btn.textContent.trim().toLowerCase() ===
                    identifier.trim().toLowerCase()
                );

              if (button) {
                button.click();
                chrome.runtime.sendMessage({
                  type: "operation_status",
                  command: "press_button",
                  status: "success",
                });
              } else {
                chrome.runtime.sendMessage({
                  type: "operation_status",
                  command: "press_button",
                  status: "failure",
                });
              }
              console.log("button press finished", button);
            },
            args: [param],
          });
        }
      }
    }
  );
}

// 🔁 Listen for results from content/injected scripts and forward to native host
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "dom_tree") {
    chrome.runtime.sendNativeMessage("com.example.sisypho_host", {
      type: "dom_tree",
      data: message.data,
    });
  } else if (message.type === "element_by_id") {
    chrome.runtime.sendNativeMessage("com.example.sisypho_host", {
      type: "element_by_id",
      data: message.data,
    });
  } else if (message.type === "operation_status") {
    chrome.runtime.sendNativeMessage("com.example.sisypho_host", {
      type: "operation_status",
      command: message.command,
      status: message.status,
    });
  }
});

// 🧩 Hook into lifecycle events
chrome.runtime.onInstalled.addListener(() => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs.length > 0) {
      const tab = tabs[0];
      initNativeHostAndInject(tab.id, tab.url);
    }
  });
});

chrome.runtime.onStartup.addListener(() => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs.length > 0) {
      const tab = tabs[0];
      initNativeHostAndInject(tab.id, tab.url);
    }
  });
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url) {
    initNativeHostAndInject(tabId, tab.url);
  }
});
