#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const apiBase = (process.env.OPENRI_API_BASE || "http://127.0.0.1:8008").replace(/\/+$/, "");

async function requestJson(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, options);
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`OpenRI API ${path} failed with HTTP ${response.status}: ${text}`);
  }
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`OpenRI API ${path} returned HTTP ${response.status} with a non-JSON body.`);
  }
}

function asText(payload) {
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(payload, null, 2),
      },
    ],
  };
}

const server = new McpServer({
  name: "openri-mcp",
  version: "0.3.2",
});

server.tool("openri_health", "Check the configured local OpenRI API health endpoint.", {}, async () => {
  return asText(await requestJson("/api/health"));
});

server.tool(
  "openri_check_text",
  "Run OpenRI checks against manuscript text through the configured local OpenRI API.",
  {
    text: z.string().min(1).describe("Manuscript text to check."),
    filename: z.string().min(1).default("manuscript.txt").describe("Display filename for the submitted text."),
  },
  async ({ text, filename }) => {
    return asText(
      await requestJson("/api/runs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ manuscript_text: text, title: filename, source_metadata: { filename } }),
      }),
    );
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);
