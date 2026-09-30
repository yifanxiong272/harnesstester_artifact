import { Agent, ProxyAgent, request } from "undici";
import {
  completionPayload,
  httpsProxyUrl,
  providerAccess,
  readEnvFile,
  requestTimeoutMs,
  shouldRetry,
} from "../../../common/model_settings.mjs";

export { messageContent, providerAccess } from "../../../common/model_settings.mjs";

function parseEnvFile(file) {
  return readEnvFile(file, (value) =>
    value.replace(/^["']+/u, "").replace(/["']+$/u, "").trim(),
  );
}

export function loadModelEnv(envFile = null) {
  return { ...process.env, ...parseEnvFile(envFile) };
}

function isSensitiveEnvKey(key) {
  return /(?:^|_)(?:API_KEY|KEY|TOKEN|SECRET|PASSWORD|CREDENTIALS?|PRIVATE_KEY)(?:_|$)/u.test(
    key,
  );
}

export function sanitizeEnvForSubprocess(env = process.env) {
  const clean = {};
  for (const [key, value] of Object.entries(env)) {
    if (!isSensitiveEnvKey(key)) {
      clean[key] = value;
    }
  }
  return clean;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function postJson({ url, headers, body, env, timeoutMs }) {
  const proxy = httpsProxyUrl(env);
  const dispatcher = proxy
    ? new ProxyAgent({ uri: proxy, proxyTunnel: true })
    : new Agent();
  try {
    const response = await request(url, {
      method: "POST",
      headers,
      body,
      dispatcher,
      signal: AbortSignal.timeout(timeoutMs),
      headersTimeout: timeoutMs,
      bodyTimeout: timeoutMs,
      maxRedirections: 0,
    });
    return {
      ok: response.statusCode >= 200 && response.statusCode < 300,
      status: response.statusCode,
      text: await response.body.text(),
    };
  } finally {
    await dispatcher.destroy();
  }
}

function redactKnownSecrets(text, env) {
  let result = String(text ?? "");
  result = result.replace(
    /https:\/\/openrouter\.ai\/workspaces\/[^"'\s]+\/keys\/[A-Za-z0-9_-]+/gu,
    "[OPENROUTER_KEY_URL]",
  );
  for (const [key, value] of Object.entries(env)) {
    if (
      !isSensitiveEnvKey(key) ||
      typeof value !== "string" ||
      value.length < 6
    ) {
      continue;
    }
    result = result.split(value).join("[REDACTED]");
  }
  return result;
}

export async function chatCompletion({
  prompt = null,
  messages = null,
  model,
  provider = "openai",
  env = process.env,
  timeoutMs = 120_000,
  totalTimeoutMs = null,
  retries = 4,
}) {
  if ((prompt === null) === (messages === null)) {
    throw new Error("provide exactly one of prompt or messages");
  }
  const configuredRequestTimeout = requestTimeoutMs(env, timeoutMs);
  const deadline =
    Number.isFinite(totalTimeoutMs) && totalTimeoutMs > 0
      ? Date.now() + totalTimeoutMs
      : Number.POSITIVE_INFINITY;
  const { key, baseUrl } = providerAccess(provider, env);
  if (!model) {
    throw new Error("model is required for model-backed generation");
  }

  const conversation = messages
    ? messages.map((message) => ({ ...message }))
    : [{ role: "user", content: String(prompt) }];
  if (conversation[0]?.role !== "system") {
    conversation.unshift({
      role: "system",
      content: "Return only valid JSON that matches the requested schema.",
    });
  }
  const payload = completionPayload(model, conversation, provider, env);

  let lastError = null;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    const remaining = deadline - Date.now();
    if (remaining <= 0) {
      throw new Error("model request exceeded its total timeout");
    }
    try {
      const response = await postJson({
        url: `${baseUrl.replace(/\/$/u, "")}/chat/completions`,
        headers: {
          Authorization: `Bearer ${key}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
        env,
        timeoutMs: Math.max(
          1,
          Math.floor(Math.min(configuredRequestTimeout, remaining)),
        ),
      });
      if (!response.ok) {
        const error = new Error(
          `model request failed: HTTP ${response.status} ${redactKnownSecrets(response.text, env).slice(0, 1000)}`,
        );
        error.retryable = shouldRetry(response.status);
        error.status = response.status;
        if (!error.retryable || attempt === retries) {
          throw error;
        }
        lastError = error;
      } else {
        return JSON.parse(response.text);
      }
    } catch (error) {
      const detail = error?.cause?.message
        ? `${error.message}: ${error.cause.message}`
        : error.message;
      lastError = new Error(detail || "model request failed");
      lastError.retryable = error?.retryable !== false;
      lastError.status = error?.status ?? null;
      if (!lastError.retryable || attempt === retries) {
        throw lastError;
      }
    }
    const retryDelay = Math.min(8000, 1500 * (attempt + 1));
    const remainingAfterAttempt = deadline - Date.now();
    if (remainingAfterAttempt <= 0) {
      throw lastError ?? new Error("model request exceeded its total timeout");
    }
    await sleep(Math.min(retryDelay, remainingAfterAttempt));
  }
  throw lastError ?? new Error("model request failed");
}
