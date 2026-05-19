import assert from "node:assert/strict";
import test from "node:test";
import fc from "fast-check";
import { createOpenRIClient } from "../index.js";

test("runText serializes arbitrary manuscript text without mutation", async () => {
  await fc.assert(
    fc.asyncProperty(fc.string({ minLength: 1, maxLength: 2000 }), fc.string({ minLength: 1, maxLength: 80 }), async (text, filename) => {
      const calls = [];
      const client = createOpenRIClient({
        baseUrl: "http://openri.test/",
        fetchImpl: async (url, options) => {
          calls.push({ url, options });
          return new Response(JSON.stringify({ id: "run_1", summary: { total_findings: 0 } }), { status: 200 });
        },
      });

      await client.runText({ text, filename });

      assert.equal(calls.length, 1);
      assert.equal(calls[0].url, "http://openri.test/api/runs");
      assert.deepEqual(JSON.parse(calls[0].options.body), {
        manuscript_text: text,
        title: filename,
        source_metadata: { filename },
      });
    }),
    { numRuns: 100 },
  );
});

test("baseUrl trimming handles repeated slashes without regular expressions", async () => {
  const calls = [];
  const client = createOpenRIClient({
    baseUrl: `http://openri.test/${"/".repeat(5000)}`,
    fetchImpl: async (url) => {
      calls.push(url);
      return new Response(JSON.stringify({ status: "ok" }), { status: 200 });
    },
  });

  await client.health();

  assert.equal(calls[0], "http://openri.test/api/health");
});
