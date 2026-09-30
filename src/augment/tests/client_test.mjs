import assert from "node:assert/strict";
import http from "node:http";
import net from "node:net";
import { once } from "node:events";
import { test } from "node:test";
import { chatCompletion } from "../typescript/run/client.mjs";

async function endpoint(t, handler) {
  const server = http.createServer(handler);
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  t.after(() => { server.closeAllConnections(); server.close(); });
  return {
    OPENAI_API_KEY: "fixture-key",
    OPENAI_BASE_URL: `http://127.0.0.1:${server.address().port}/v1`,
  };
}

test("model request preserves the generation payload and token limit", async t => {
  const env = await endpoint(t, async (req, res) => {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    assert.equal(req.url, "/v1/chat/completions");
    assert.equal(req.headers.authorization, "Bearer fixture-key");
    assert.deepEqual(JSON.parse(Buffer.concat(chunks)), {
      model: "fixture-model",
      messages: [
        { role: "system", content: "Return only valid JSON that matches the requested schema." },
        { role: "user", content: "fixture prompt" },
      ],
      response_format: { type: "json_object" }, max_completion_tokens: 100,
    });
    res.end(JSON.stringify({ choices: [{ message: { content: "{}" } }] }));
  });
  const result = await chatCompletion({
    model: "fixture-model", provider: "openai", prompt: "fixture prompt",
    env: { ...env, TEST_AUGMENT_MAX_TOKENS: "100" }, retries: 0,
  });
  assert.equal(result.choices[0].message.content, "{}");
});

test("authentication failures are not retried and secrets are redacted", async t => {
  let calls = 0;
  const env = await endpoint(t, (_req, res) => {
    calls += 1;
    res.writeHead(401);
    res.end("invalid key fixture-key");
  });
  await assert.rejects(chatCompletion({
    model: "fixture", prompt: "fixture", env,
  }), error => error.retryable === false && !error.message.includes("fixture-key"));
  assert.equal(calls, 1);
});

test("the transport honors the total request deadline", async t => {
  const env = await endpoint(t, () => {});
  await assert.rejects(chatCompletion({
    model: "fixture", prompt: "fixture", env, totalTimeoutMs: 30, retries: 0,
  }));
});

test("model requests use the configured HTTP CONNECT proxy", async t => {
  const env = await endpoint(t, (_req, res) => {
    res.end(JSON.stringify({ choices: [{ message: { content: "{}" } }] }));
  });
  const proxy = http.createServer();
  const sockets = new Set();
  let tunnels = 0;
  proxy.on("connect", (request, client, head) => {
    tunnels += 1;
    const target = new URL(`http://${request.url}`);
    const upstream = net.connect(Number(target.port), target.hostname, () => {
      client.write("HTTP/1.1 200 Connection Established\r\n\r\n");
      upstream.write(head);
      client.pipe(upstream).pipe(client);
    });
    for (const socket of [client, upstream]) {
      sockets.add(socket);
      socket.on("close", () => sockets.delete(socket));
    }
  });
  proxy.listen(0, "127.0.0.1");
  await once(proxy, "listening");
  t.after(() => { for (const socket of sockets) socket.destroy(); proxy.close(); });
  const result = await chatCompletion({
    model: "fixture", prompt: "fixture", retries: 0, totalTimeoutMs: 2000,
    env: { ...env, TEST_AUGMENT_HTTPS_PROXY: `http://127.0.0.1:${proxy.address().port}` },
  });
  assert.equal(result.choices[0].message.content, "{}");
  assert.equal(tunnels, 1);
});
