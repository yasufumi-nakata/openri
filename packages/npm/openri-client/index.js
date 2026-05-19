export class OpenRIClientError extends Error {
  constructor(message, { status, responseBody } = {}) {
    super(message);
    this.name = "OpenRIClientError";
    this.status = status;
    this.responseBody = responseBody;
  }
}

function trimBaseUrl(baseUrl) {
  const value = String(baseUrl || "http://127.0.0.1:8008");
  let end = value.length;
  while (end > 0 && value.charCodeAt(end - 1) === 47) {
    end -= 1;
  }
  return value.slice(0, end);
}

async function parseResponse(response) {
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new OpenRIClientError(`OpenRI API request failed with HTTP ${response.status}`, {
      status: response.status,
      responseBody: body,
    });
  }
  return body;
}

export function createOpenRIClient({ baseUrl = "http://127.0.0.1:8008", fetchImpl = globalThis.fetch } = {}) {
  if (typeof fetchImpl !== "function") {
    throw new TypeError("createOpenRIClient requires a fetch implementation.");
  }
  const root = trimBaseUrl(baseUrl);

  return {
    async health() {
      return parseResponse(await fetchImpl(`${root}/api/health`));
    },

    async runText({ text, filename = "manuscript.txt", checks, profile } = {}) {
      if (typeof text !== "string" || text.length === 0) {
        throw new TypeError("runText requires a non-empty text string.");
      }
      const payload = {
        manuscript_text: text,
        title: filename,
        source_metadata: { filename },
      };
      if (Array.isArray(checks)) {
        payload.activated_rulesets = checks;
      }
      if (profile && typeof profile === "object") {
        payload.source_metadata = { ...payload.source_metadata, ...profile };
      }
      return parseResponse(
        await fetchImpl(`${root}/api/runs`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(payload),
        }),
      );
    },
  };
}
