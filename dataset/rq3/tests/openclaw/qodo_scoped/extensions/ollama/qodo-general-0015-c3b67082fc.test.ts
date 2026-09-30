import { describe, expect, it, vi } from "vitest";
import { createTestPluginApi } from "../../test/helpers/extensions/plugin-api.js";
import plugin from "./index.js";
import { buildOllamaChatRequest } from "./src/stream.js";
import { parseNdjsonStream } from "./src/stream.js";
import { wrapOllamaCompatNumCtx } from "./src/stream.js";
import { isOllamaCompatProvider } from "./src/stream.js";
import {
  resolveOllamaBaseUrlForRun,
  OLLAMA_NATIVE_BASE_URL,
} from "./src/stream.js";

const promptAndConfigureOllamaMock = vi.hoisted(() =>
  vi.fn(async () => ({
    config: {
      models: {
        providers: {
          ollama: {
            baseUrl: "http://127.0.0.1:11434",
            api: "ollama",
            models: [],
          },
        },
      },
    },
  })),
);
const ensureOllamaModelPulledMock = vi.hoisted(() => vi.fn(async () => {}));

vi.mock("openclaw/plugin-sdk/provider-setup", () => ({
  promptAndConfigureOllama: promptAndConfigureOllamaMock,
  ensureOllamaModelPulled: ensureOllamaModelPulledMock,
  configureOllamaNonInteractive: vi.fn(),
  buildOllamaProvider: vi.fn(),
}));

function registerProvider() {
  const registerProviderMock = vi.fn();

  plugin.register(
    createTestPluginApi({
      id: "ollama",
      name: "Ollama",
      source: "test",
      config: {},
      runtime: {} as never,
      registerProvider: registerProviderMock,
    }),
  );

  expect(registerProviderMock).toHaveBeenCalledTimes(1);
  return registerProviderMock.mock.calls[0]?.[0];
}

describe("ollama plugin", () => {
  it("does not preselect a default model during provider auth setup", async () => {
    const provider = registerProvider();

    const result = await provider.auth[0].run({
      config: {},
      prompter: {} as never,
      isRemote: false,
      openUrl: vi.fn(async () => undefined),
    });

    expect(promptAndConfigureOllamaMock).toHaveBeenCalledWith({
      cfg: {},
      prompter: {},
      isRemote: false,
      openUrl: expect.any(Function),
    });
    expect(result.configPatch).toEqual({
      models: {
        providers: {
          ollama: {
            baseUrl: "http://127.0.0.1:11434",
            api: "ollama",
            models: [],
          },
        },
      },
    });
    expect(result.defaultModel).toBeUndefined();
  });

  it("pulls the model the user actually selected", async () => {
    const provider = registerProvider();
    const config = {
      models: {
        providers: {
          ollama: {
            baseUrl: "http://127.0.0.1:11434",
            models: [],
          },
        },
      },
    };
    const prompter = {} as never;

    await provider.onModelSelected?.({
      config,
      model: "ollama/glm-4.7-flash",
      prompter,
    });

    expect(ensureOllamaModelPulledMock).toHaveBeenCalledWith({
      config,
      model: "ollama/glm-4.7-flash",
      prompter,
    });
  });

  it("wraps OpenAI-compatible payloads with num_ctx for Ollama compat routes", () => {
    const provider = registerProvider();
    let payloadSeen: Record<string, unknown> | undefined;
    const baseStreamFn = vi.fn((_model, _context, options) => {
      const payload: Record<string, unknown> = { options: { temperature: 0.1 } };
      options?.onPayload?.(payload, _model);
      payloadSeen = payload;
      return {} as never;
    });

    const wrapped = provider.wrapStreamFn?.({
      config: {
        models: {
          providers: {
            ollama: {
              api: "openai-completions",
              baseUrl: "http://127.0.0.1:11434/v1",
              models: [],
            },
          },
        },
      },
      provider: "ollama",
      modelId: "qwen3:32b",
      model: {
        api: "openai-completions",
        provider: "ollama",
        id: "qwen3:32b",
        baseUrl: "http://127.0.0.1:11434/v1",
        contextWindow: 202_752,
      },
      streamFn: baseStreamFn,
    });

    expect(typeof wrapped).toBe("function");
    void wrapped?.({} as never, {} as never, {});
    expect(baseStreamFn).toHaveBeenCalledTimes(1);
    expect((payloadSeen?.options as Record<string, unknown> | undefined)?.num_ctx).toBe(202752);
  });

  it("wraps native Ollama payloads with top-level think=false when thinking is off", () => {
    const provider = registerProvider();
    let payloadSeen: Record<string, unknown> | undefined;
    const baseStreamFn = vi.fn((_model, _context, options) => {
      const payload: Record<string, unknown> = {
        messages: [],
        options: { num_ctx: 65536 },
        stream: true,
      };
      options?.onPayload?.(payload, _model);
      payloadSeen = payload;
      return {} as never;
    });

    const wrapped = provider.wrapStreamFn?.({
      config: {
        models: {
          providers: {
            ollama: {
              api: "ollama",
              baseUrl: "http://127.0.0.1:11434",
              models: [],
            },
          },
        },
      },
      provider: "ollama",
      modelId: "qwen3.5:9b",
      thinkingLevel: "off",
      model: {
        api: "ollama",
        provider: "ollama",
        id: "qwen3.5:9b",
        baseUrl: "http://127.0.0.1:11434",
        contextWindow: 131_072,
      },
      streamFn: baseStreamFn,
    });

    expect(typeof wrapped).toBe("function");
    void wrapped?.(
      {
        api: "ollama",
        provider: "ollama",
        id: "qwen3.5:9b",
      } as never,
      {} as never,
      {},
    );
    expect(baseStreamFn).toHaveBeenCalledTimes(1);
    expect(payloadSeen?.think).toBe(false);
    expect((payloadSeen?.options as Record<string, unknown> | undefined)?.think).toBeUndefined();
  });

  it("buildOllamaChatRequest includes tools and options only when present and defaults stream true", () => {
    const messages = [{ role: "user", content: "hi" }];
    const tools = [
      {
        type: "function",
        function: { name: "t", description: "d", parameters: {} },
      },
    ];
  
    const reqWithAll = buildOllamaChatRequest({
      modelId: "m1",
      messages: messages as any,
      tools,
      options: { foo: "bar" },
      stream: false,
    });
    expect(reqWithAll.model).toBe("m1");
    expect(reqWithAll.messages).toBe(messages);
    expect(reqWithAll.tools).toBe(tools);
    expect(reqWithAll.options).toEqual({ foo: "bar" });
    expect(reqWithAll.stream).toBe(false);
  
    const reqMin = buildOllamaChatRequest({
      modelId: "m2",
      messages: messages as any,
    });
    expect(reqMin.model).toBe("m2");
    expect(reqMin.messages).toBe(messages);
    // tools/options should be omitted when not provided
    expect((reqMin as any).tools).toBeUndefined();
    expect((reqMin as any).options).toBeUndefined();
    // default stream true
    expect(reqMin.stream).toBe(true);
  });


  it("parseNdjsonStream preserves unsafe integer literals as strings and parses trailing buffer", async () => {
    const big = String(Number.MAX_SAFE_INTEGER + 2); // unsafe
    const small = String(Number.MAX_SAFE_INTEGER); // safe
    // Build a single NDJSON line without a trailing newline to exercise final-buffer parsing
    const line = `{"model":"m","created_at":"t","message":{"role":"assistant","content":"hi"},"done":true,"big":${big},"small":${small}}`;
  
    // simple reader mock matching ReadableStreamDefaultReader interface
    function makeReader(chunks: string[]) {
      let idx = 0;
      return {
        read: async () => {
          if (idx >= chunks.length) {
            return { done: true, value: undefined } as const;
          }
          const val = new TextEncoder().encode(chunks[idx++]);
          return { done: false, value: val } as const;
        },
      };
    }
  
    const reader = makeReader([line]); // no newline -> trailing buffer path used
    const results: any[] = [];
    for await (const obj of parseNdjsonStream(reader as any)) {
      results.push(obj);
    }
  
    expect(results.length).toBe(1);
    const parsed = results[0];
    // big should be turned into a string by the preservation logic
    expect(typeof parsed.big).toBe("string");
    expect(parsed.big).toBe(big);
    // small should remain a number
    expect(typeof parsed.small).toBe("number");
    expect(parsed.small).toBe(Number(small));
  });


  it("wrapOllamaCompatNumCtx injects num_ctx into payload.options when base stream emits payload", () => {
    let seenPayload: Record<string, unknown> | undefined;
    // base Fn simulates a provider stream function that calls options.onPayload with a payload it constructs
    const baseFn = (_model: any, _context: any, options?: any) => {
      const payload: Record<string, unknown> = {}; // no .options initially
      options?.onPayload?.(payload, _model);
      // return a dummy stream-like object (not used)
      return {} as any;
    };
  
    const wrapped = wrapOllamaCompatNumCtx(baseFn, 2027);
    expect(typeof wrapped).toBe("function");
  
    // call the wrapped function and capture the payload forwarded to consumer of onPayload
    wrapped(
      { id: "m", api: "openai-completions", provider: "ollama" } as any,
      {} as any,
      {
        onPayload: (payload: Record<string, unknown>) => {
          seenPayload = payload;
        },
      } as any,
    );
  
    // The wrapper should ensure payload.options exists and carry num_ctx
    expect(seenPayload).toBeDefined();
    expect(typeof seenPayload!.options === "object").toBe(true);
    expect((seenPayload!.options as any).num_ctx).toBe(2027);
  });


  it("isOllamaCompatProvider recognizes Ollama hints, localhost, paths and rejects invalid URLs", () => {
    // provider id explicitly 'ollama' should be true even with no baseUrl
    expect(isOllamaCompatProvider({ provider: "ollama" })).toBe(true);
  
    // localhost with Ollama port -> true, regardless of provider hint
    expect(
      isOllamaCompatProvider({ provider: "something", baseUrl: "http://127.0.0.1:11434" }),
    ).toBe(true);
    expect(
      isOllamaCompatProvider({ provider: "something", baseUrl: "http://[::1]:11434" }),
    ).toBe(true);
  
    // provider hint contains 'ollama' and remote host uses port 11434 and root path -> true
    expect(
      isOllamaCompatProvider({ provider: "my-ollama-provider", baseUrl: "http://remote:11434/" }),
    ).toBe(true);
  
    // provider hint contains 'ollama' and path /v1 (case-insensitive) -> true
    expect(
      isOllamaCompatProvider({ provider: "my-ollama", baseUrl: "http://remote:11434/v1" }),
    ).toBe(true);
    expect(
      isOllamaCompatProvider({ provider: "my-ollama", baseUrl: "http://remote:11434/V1/" }),
    ).toBe(true);
  
    // wrong port -> false
    expect(
      isOllamaCompatProvider({ provider: "my-ollama", baseUrl: "http://remote:11435/v1" }),
    ).toBe(false);
  
    // malformed URL -> false (caught)
    expect(isOllamaCompatProvider({ provider: "x", baseUrl: "not-a-url" })).toBe(false);
  });


  it("resolves base url precedence and default correctly", () => {
    // providerBaseUrl should take precedence and be trimmed
    expect(
      resolveOllamaBaseUrlForRun({
        providerBaseUrl: "  http://provider.example/ ",
        modelBaseUrl: "http://model.example/",
      }),
    ).toBe("http://provider.example/");
  
    // when no providerBaseUrl, modelBaseUrl is used (trimmed)
    expect(
      resolveOllamaBaseUrlForRun({
        modelBaseUrl: "  http://model.example/v1  ",
      }),
    ).toBe("http://model.example/v1");
  
    // when neither provided, the native default is returned
    expect(resolveOllamaBaseUrlForRun({})).toBe(OLLAMA_NATIVE_BASE_URL);
  });

});
