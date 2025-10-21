import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { Client } from "../src/client";

const port = 54319;
const client = new Client(port);

await client.connect();

// Define response schemas
const ContentItemSchema = z.object({
  type: z.literal("text"),
  text: z.string()
});

const ResponseSchema = z.object({
  content: z.array(ContentItemSchema)
});

// Create an MCP server
const server = new McpServer({
  name: "Chrome-Browser-Control",
  version: "1.0.0",
  description: "Control Chrome browser using MCP protocol"
});

// DOM Selection and Information
server.tool(
  "getDOMTree",
  "Get the entire DOM tree of the current page",
  {},
  async () => {
    const response = await client.callToolExtension("getDOMTree");
    return response;
  }
);

server.tool(
  "getPageInfo",
  "Get current page information including URL, title, and metadata",
  {},
  async () => {
    const response = await client.callToolExtension("getPageInfo");
    return response;
  }
);

// Element Selection
server.tool(
  "getElementById",
  "Get an element by its ID",
  { id: z.string() },
  async ({ id }) => {
    const response = await client.callToolExtension("getElementById", id);
    return ResponseSchema.parse(response);
  }
);

server.tool(
  "querySelector",
  "Get an element using a CSS selector",
  { selector: z.string() },
  async ({ selector }) => {
    const response = await client.callToolExtension("querySelector", selector);
    return ResponseSchema.parse(response);
  }
);

// Click Actions
server.tool(
  "clickLink",
  "Click a link by its text content or href",
  { identifier: z.string() },
  async ({ identifier }) => {
    const response = await client.callToolExtension("clickLink", identifier);
    return ResponseSchema.parse(response);
  }
);

server.tool(
  "clickButton",
  "Click a button by its text content or ID",
  { identifier: z.string() },
  async ({ identifier }) => {
    const response = await client.callToolExtension("clickButton", identifier);
    return ResponseSchema.parse(response);
  }
);

server.tool(
  "clickElement",
  "Click any element using a CSS selector",
  { selector: z.string() },
  async ({ selector }) => {
    const response = await client.callToolExtension("clickElement", selector);
    return ResponseSchema.parse(response);
  }
);

// Form Interaction
server.tool(
  "typeText",
  "Type text into a focused input field",
  { 
    selector: z.string(),
    text: z.string(),
    options: z.object({
      delay: z.number().optional(),
      submitAfter: z.boolean().optional()
    }).optional()
  },
  async ({ selector, text, options }) => {
    const response = await client.callToolExtension("typeText", { selector, text, options });
    return ResponseSchema.parse(response);
  }
);

server.tool(
  "submitForm",
  "Submit a form by its ID or containing element selector",
  { selector: z.string() },
  async ({ selector }) => {
    const response = await client.callToolExtension("submitForm", selector);
    return ResponseSchema.parse(response);
  }
);

// Navigation
server.tool(
  "navigate",
  "Navigate to a specific URL",
  { url: z.string().url() },
  async ({ url }) => {
    const response = await client.callToolExtension("navigate", url);
    return ResponseSchema.parse(response);
  }
);

server.tool(
  "goBack",
  "Navigate back in browser history",
  {},
  async () => {
    const response = await client.callToolExtension("goBack");
    return ResponseSchema.parse(response);
  }
);

server.tool(
  "goForward",
  "Navigate forward in browser history",
  {},
  async () => {
    const response = await client.callToolExtension("goForward");
    return ResponseSchema.parse(response);
  }
);

server.tool(
  "reload",
  "Reload the current page",
  { 
    options: z.object({
      bypassCache: z.boolean().optional()
    }).optional()
  },
  async ({ options }) => {
    const response = await client.callToolExtension("reload", options);
    return ResponseSchema.parse(response);
  }
);

// Scrolling and Viewport
server.tool(
  "scroll",
  "Scroll the page",
  {
    target: z.union([
      z.literal("top"),
      z.literal("bottom"),
      z.object({
        x: z.number(),
        y: z.number()
      })
    ])
  },
  async ({ target }) => {
    const response = await client.callToolExtension("scroll", { target });
    return ResponseSchema.parse(response);
  }
);

// JavaScript Execution
server.tool(
  "evaluate",
  "Execute JavaScript code in the page context",
  { 
    code: z.string(),
    args: z.array(z.union([z.string(), z.number(), z.boolean(), z.object({}), z.null()])).optional()
  },
  async ({ code, args }) => {
    const response = await client.callToolExtension("evaluate", { code, args });
    return ResponseSchema.parse(response);
  }
);

// Wait and Timing
server.tool(
  "waitForElement",
  "Wait for an element to appear in the DOM",
  { 
    selector: z.string(),
    options: z.object({
      timeout: z.number().optional(),
      visible: z.boolean().optional()
    }).optional()
  },
  async ({ selector, options }) => {
    const response = await client.callToolExtension("waitForElement", { selector, options });
    return ResponseSchema.parse(response);
  }
);

// Add the new tool before the transport setup
server.tool(
  "retrieve_write_interaction_queue",
  "Retrieve and clear the queue of user interactions with the webpage",
  {},
  async () => {
    const response = await client.callToolExtension("retrieve_write_interaction_queue");
    return response;
  }
);

server.tool(
  "getInteractionQueueSize",
  "Get the current size of the interaction queue",
  {},
  async () => {
    const response = await client.callToolExtension("getInteractionQueueSize");
    return response;
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);

process.on("SIGINT", async () => {
  console.log("Received SIGINT signal");
  await client.dispose();
  process.exit(0);
});
