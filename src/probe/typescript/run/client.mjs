import http from "node:http";
import https from "node:https";
import tls from "node:tls";
import {
  completionPayload,
  httpsProxyUrl,
  providerAccess,
  readEnvFile,
  requestTimeoutMs,
  shouldRetry,
} from "../../../common/model_settings.mjs";
import { CaseBudgetExceeded, limitTimeout } from "./deadline.mjs";

export { messageContent } from "../../../common/model_settings.mjs";

export function parseEnvFile(file) {
  return readEnvFile(file, (value) => {
    while (value.length > 0 && ['"', "'"].includes(value[0])) {
      value = value.slice(1).trimStart();
    }
    while (value.length > 0 && ['"', "'"].includes(value.at(-1))) {
      value = value.slice(0, -1).trimEnd();
    }
    return value;
  });
}

export function loadModelEnv(envFile = null) {
  return Object.assign({}, process.env, parseEnvFile(envFile));
}

function isSensitiveEnvKey(key) {
  return /(?:^|_)(?:API_KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|PRIVATE_KEY)(?:_|$)/u.test(
    key,
  );
}

export class ModelRequestError extends Error {
  constructor(message, { status = 0, retryable = false } = {}) {
    super(message);
    this.name = "ModelRequestError";
    this.status = status;
    this.retryable = retryable;
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function proxyAuthHeader(proxy) {
  if (!proxy.username && !proxy.password) {
    return null;
  }
  const raw = `${decodeURIComponent(proxy.username)}:${decodeURIComponent(proxy.password)}`;
  return `Basic ${Buffer.from(raw).toString("base64")}`;
}

function postJson({ url, headers, body, env, timeoutMs }) {
  return new Promise((resolve, reject) => {
    const target = new URL(url);
    const isHttp = target.protocol === "http:";
    const transport = isHttp ? http : https;
    const proxyUrl = isHttp ? null : httpsProxyUrl(env);
    const proxy = proxyUrl ? new URL(proxyUrl) : null;
    const agent = new transport.Agent({ keepAlive: false });
    let settled = false;
    let request, connectRequest, tunnel;
    const finish = (callback, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      request?.destroy();
      connectRequest?.destroy();
      tunnel?.destroy();
      agent.destroy();
      callback(value);
    };
    const fail = (error) => finish(reject, error);
    const timer = setTimeout(
      () => fail(new Error("model request timed out")),
      timeoutMs,
    );
    const send = () => {
      request = transport.request(
        {
          hostname: target.hostname,
          port: Number(target.port || (isHttp ? 80 : 443)),
          path: `${target.pathname}${target.search}`,
          method: "POST",
          agent,
          headers: {
            ...headers,
            "Content-Length": String(Buffer.byteLength(body)),
          },
        },
        (response) => {
          const chunks = [];
          response.on("data", (chunk) => chunks.push(chunk));
          response.once("error", fail);
          response.once("end", () => {
            const status = Number(response.statusCode ?? 0);
            finish(resolve, {
              ok: status >= 200 && status < 300,
              status,
              text: Buffer.concat(chunks).toString("utf8"),
              headers: new Map(
                Object.entries(response.headers).map(([key, value]) => [
                  key.toLowerCase(),
                  String(value || ""),
                ]),
              ),
            });
          });
        },
      );
      request.once("error", fail);
      request.end(body);
    };
    if (!proxy) {
      send();
      return;
    }
    if (proxy.protocol !== "http:") {
      fail(new Error(`unsupported proxy protocol: ${proxy.protocol}`));
      return;
    }
    const tunnelHost = `${target.hostname}:${target.port || 443}`;
    const connectHeaders = {
      Host: tunnelHost,
      "Proxy-Connection": "Keep-Alive",
    };
    const auth = proxyAuthHeader(proxy);
    if (auth) connectHeaders["Proxy-Authorization"] = auth;
    connectRequest = http.request({
      host: proxy.hostname,
      port: Number(proxy.port || 80),
      method: "CONNECT",
      path: tunnelHost,
      headers: connectHeaders,
    });
    connectRequest.once("connect", (response, socket, head) => {
      tunnel = socket;
      if (settled) {
        socket.destroy();
        return;
      }
      if (response.statusCode !== 200) {
        fail(new Error(`proxy CONNECT failed: HTTP ${response.statusCode}`));
        return;
      }
      if (head?.length) socket.unshift(head);
      socket.once("error", fail);
      // Node handles TLS verification, HTTP framing, and chunked responses.
      agent.createConnection = (options) =>
        tls.connect({
          ...options,
          socket,
          servername: target.hostname,
          ALPNProtocols: ["http/1.1"],
        });
      send();
    });
    connectRequest.once("error", fail);
    connectRequest.end();
  });
}

function retryDelay(response, attempt) {
  const retryAfter = Number(response?.headers?.get?.("retry-after") || 0);
  if (Number.isFinite(retryAfter) && retryAfter > 0) {
    return Math.min(60_000, retryAfter * 1000);
  }
  return Math.min(20_000, 1500 * (attempt + 1) ** 2);
}

function redactKnownSecrets(text, env) {
  let result = String(text ?? "");
  for (const [key, value] of Object.entries(env)) {
    if (
      isSensitiveEnvKey(key) &&
      typeof value === "string" &&
      value.length >= 6
    ) {
      result = result.split(value).join("[REDACTED]");
    }
  }
  return result;
}

export async function chatCompletion({
  prompt,
  model,
  provider = "openai",
  env = process.env,
  timeoutMs = 120_000,
  retries = 5,
}) {
  const requestTimeout = requestTimeoutMs(env, timeoutMs);
  const { key, baseUrl } = providerAccess(provider, env);
  const payload = completionPayload(
    model,
    [
      {
        role: "system",
        content: "Return only valid JSON that matches the requested schema.",
      },
      { role: "user", content: prompt },
    ],
    provider,
    env,
  );

  let lastError = null;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    limitTimeout();
    try {
      const response = await postJson({
        url: `${baseUrl.replace(/\/$/u, "")}/chat/completions`,
        headers: {
          Authorization: `Bearer ${key}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
        env,
        timeoutMs: Math.max(1, Math.ceil(limitTimeout(requestTimeout))),
      });
      if (!response.ok) {
        const retryable = shouldRetry(response.status);
        const error = new ModelRequestError(
          `model request failed: HTTP ${response.status} ${redactKnownSecrets(response.text, env).slice(0, 1000)}`,
          { status: response.status, retryable },
        );
        if (!retryable || attempt === retries) {
          throw error;
        }
        lastError = error;
        await sleep(Math.ceil(limitTimeout(retryDelay(response, attempt))));
        limitTimeout();
        continue;
      } else {
        const result = JSON.parse(response.text);
        limitTimeout();
        return result;
      }
    } catch (error) {
      if (error instanceof CaseBudgetExceeded) {
        throw error;
      }
      limitTimeout();
      const detail = error?.cause?.message
        ? `${error.message}: ${error.cause.message}`
        : error.message;
      lastError =
        error instanceof ModelRequestError
          ? error
          : new ModelRequestError(detail || "model request failed", {
              retryable: true,
            });
      if (!lastError.retryable) {
        throw lastError;
      }
      if (attempt === retries) {
        throw lastError;
      }
    }
    await sleep(
      Math.ceil(limitTimeout(Math.min(20_000, 1500 * (attempt + 1) ** 2))),
    );
    limitTimeout();
  }
  throw lastError ?? new Error("model request failed");
}
