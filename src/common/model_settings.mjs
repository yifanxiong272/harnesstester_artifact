/** Shared request settings for the two TypeScript model clients. */

import fs from "node:fs";

/** Read assignments using the supplied value normalizer. */
export function readEnvFile(file, normalizeValue) {
  if (!file || !fs.existsSync(file)) return {};
  const env = {};
  for (const rawLine of fs.readFileSync(file, "utf8").split(/\r?\n/u)) {
    let line = rawLine.trim();
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    if (line.startsWith("export ")) line = line.slice("export ".length).trim();
    const index = line.indexOf("=");
    const key = line.slice(0, index).trim();
    const value = normalizeValue(line.slice(index + 1).trim());
    if (key) env[key] = value;
  }
  return env;
}

export function providerAccess(provider, env) {
  let config;
  if (provider === "openai") {
    config = {
      key: env.OPENAI_API_KEY || env.LLM_API_KEY,
      baseUrl:
        env.OPENAI_BASE_URL || env.LLM_BASE_URL || "https://api.openai.com/v1",
    };
  } else if (provider === "openrouter") {
    config = {
      key: env.OPENROUTER_API_KEY || env.LLM_API_KEY,
      baseUrl:
        env.OPENROUTER_BASE_URL || env.LLM_BASE_URL || "https://openrouter.ai/api/v1",
    };
  } else {
    throw new Error(`unsupported model provider: ${provider}`);
  }
  if (!config.key) {
    throw new Error(`missing API key for model provider: ${provider}`);
  }
  return config;
}

/** Build a JSON-mode completion request with the provider's token-limit field. */
export function completionPayload(model, messages, provider, env) {
  const payload = { model, messages, response_format: { type: "json_object" } };
  const maxTokens = completionTokenLimit(env);
  if (maxTokens) {
    const field = provider === "openai" ? "max_completion_tokens" : "max_tokens";
    payload[field] = maxTokens;
  }
  return payload;
}

export function messageContent(response) {
  const content = response?.choices?.[0]?.message?.content ?? "";
  return typeof content === "string" ? content : JSON.stringify(content);
}

export function shouldRetry(status) {
  return (
    status === 408 ||
    status === 409 ||
    status === 425 ||
    status === 429 ||
    status >= 500
  );
}

export function completionTokenLimit(env) {
  const raw = env.TEST_AUGMENT_MAX_TOKENS || env.LLM_MAX_TOKENS;
  if (!raw) return null;
  const value = Number(raw);
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : null;
}

export function requestTimeoutMs(env, fallback) {
  const value = Number(
    env.TEST_AUGMENT_REQUEST_TIMEOUT_MS || env.LLM_REQUEST_TIMEOUT_MS || fallback,
  );
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : fallback;
}

export function httpsProxyUrl(env) {
  return (
    env.TEST_AUGMENT_HTTPS_PROXY ||
    env.HTTPS_PROXY ||
    env.https_proxy ||
    env.ALL_PROXY ||
    env.all_proxy ||
    null
  );
}
