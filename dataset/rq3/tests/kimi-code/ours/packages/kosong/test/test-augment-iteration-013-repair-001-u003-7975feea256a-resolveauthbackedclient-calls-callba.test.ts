import {
  APIConnectionError,
  APIContextOverflowError,
  APIProviderRateLimitError,
  APIStatusError,
  APITimeoutError,
  ChatProviderError,
} from '#/errors';
import type { Message, StreamedMessagePart, ToolCall } from '#/message';
import {
  convertGoogleGenAIError,
  GoogleGenAIChatProvider,
  GoogleGenAIStreamedMessage,
  messagesToGoogleGenAIContents,
} from '#/providers/google-genai';
import type { Tool } from '#/tool';
import { describe, it, expect, vi } from 'vitest';

function makeGenerateContentResponse() {
  return {
    candidates: [
      {
        content: { parts: [{ text: 'Hello' }], role: 'model' },
        finishReason: 'STOP',
      },
    ],
    usageMetadata: {
      promptTokenCount: 10,
      candidatesTokenCount: 5,
      totalTokenCount: 15,
    },
    modelVersion: 'gemini-2.5-flash',
  };
}

function createProvider(
  options?: Partial<{ model: string; vertexai: boolean; stream: boolean }>,
): GoogleGenAIChatProvider {
  return new GoogleGenAIChatProvider({
    model: options?.model ?? 'gemini-2.5-flash',
    apiKey: 'test-key',
    vertexai: options?.vertexai,
    stream: options?.stream,
  });
}

/** Capture the request body by mocking the client's generateContentStream. */
async function captureRequestBody(
  provider: GoogleGenAIChatProvider,
  systemPrompt: string,
  tools: Tool[],
  history: Message[],
): Promise<Record<string, unknown>> {
  let capturedBody: Record<string, unknown> | undefined;

  const mockModels = (provider as any)._client.models as Record<string, unknown>;

  async function* mockStream() {
    yield makeGenerateContentResponse();
  }

  mockModels['generateContentStream'] = vi.fn().mockImplementation((params: unknown) => {
    capturedBody = params as Record<string, unknown>;
    return Promise.resolve(mockStream());
  });

  mockModels['generateContent'] = vi.fn().mockImplementation((params: unknown) => {
    capturedBody = params as Record<string, unknown>;
    return Promise.resolve(makeGenerateContentResponse());
  });

  const stream = await provider.generate(systemPrompt, tools, history);
  for await (const part of stream) {
    void part;
  }

  if (capturedBody === undefined) {
    throw new Error('Expected provider.generate() to call a Google GenAI model endpoint');
  }
  return capturedBody;
}

/** Collect all parts from a StreamedMessage. */
async function collectParts(msg: {
  [Symbol.asyncIterator](): AsyncIterator<StreamedMessagePart>;
}): Promise<StreamedMessagePart[]> {
  const parts: StreamedMessagePart[] = [];
  for await (const part of msg) {
    parts.push(part);
  }
  return parts;
}

const ADD_TOOL: Tool = {
  name: 'add',
  description: 'Add two integers.',
  parameters: {
    type: 'object',
    properties: {
      a: { type: 'integer', description: 'First number' },
      b: { type: 'integer', description: 'Second number' },
    },
    required: ['a', 'b'],
  },
};

const MUL_TOOL: Tool = {
  name: 'multiply',
  description: 'Multiply two integers.',
  parameters: {
    type: 'object',
    properties: {
      a: { type: 'integer', description: 'First number' },
      b: { type: 'integer', description: 'Second number' },
    },
    required: ['a', 'b'],
  },
};

describe('GoogleGenAIChatProvider', () => {








  describe('streaming', () => {














    __testAugmentVitest_dcea1c7fe3a9.it("_createClient invokes callback and requireProviderApiKey for non-vertexai_round_013", async () => {
      // Mock the two dependencies the provider relies on so we can force
      // resolveAuthBackedClient to call the provider-supplied callback and
      // observe whether requireProviderApiKey is invoked only for the
      // non-vertexai provider.

      const calls: Array<{ prov: string; auth: unknown; apiKey: string | undefined }> = [];

      __testAugmentVitest_dcea1c7fe3a9.vi.doMock('../src/providers/request-auth', () => ({
        // The provider name passed through by the implementation should be
        // observable here.
        requireProviderApiKey: (providerName: string, auth: unknown, apiKey: string | undefined) => {
          calls.push({ prov: providerName, auth, apiKey });
          // Simulate returning an apiKey when the caller omits one.
          return apiKey ?? 'fallback-key';
        },
        // Make resolveAuthBackedClient execute the callback so the provider's
        // internal branching is exercised.
        resolveAuthBackedClient: (opts: unknown, auth: unknown, cb: (a: unknown) => unknown) => {
          // Call the callback exactly as the real utility would when delegating
          // to the provider-specific client factory.
          return cb(auth);
        },
      }));

      // Mock '@google/genai' to provide a minimal GoogleGenAI constructor so
      // _buildClient can instantiate it without any real network or SDK.
      __testAugmentVitest_dcea1c7fe3a9.vi.doMock('@google/genai', () => {
        class ApiError extends Error {
          status: number;
          constructor(m: string, s = 500) {
            super(m);
            this.status = s;
          }
        }
        class GoogleGenAI {
          models: Record<string, unknown>;
          opts: unknown;
          constructor(opts: unknown) {
            this.opts = opts;
            // Provide both stream and non-stream entrypoints used by provider.generate
            this.models = {
              generateContentStream: async () => {
                async function* s() {
                  yield { candidates: [{ content: { parts: [{ text: 'streamed' }] } }], responseId: 'r1' };
                }
                return Promise.resolve(s());
              },
              generateContent: async () => ({ candidates: [{ content: { parts: [{ text: 'response' }] } }], usageMetadata: { promptTokenCount: 1, candidatesTokenCount: 1 } }),
            };
          }
        }
        return { ApiError, GoogleGenAI };
      });

      // Load the module under test after registering mocks so it picks them up.
      const mod = (await __testAugmentLoadTarget_1ea4df97aef2()) as any;
      const { GoogleGenAIChatProvider } = mod as { GoogleGenAIChatProvider: new (o: any) => any };

      // Create one provider that uses vertexai and one that does not. Both will
      // end up calling resolveAuthBackedClient during generate; our mocked
      // resolveAuthBackedClient will invoke the callback which, for the
      // non-vertexai provider, should call requireProviderApiKey.
      const vProvider = new GoogleGenAIChatProvider({ model: 'm1', apiKey: 'explicit', vertexai: true, stream: true });
      const nvProvider = new GoogleGenAIChatProvider({ model: 'm2', apiKey: 'explicit', vertexai: false, stream: true });

      // Helper to drain the stream returned by generate.
      async function drain(stream: AsyncIterable<unknown> | unknown) {
        const parts: unknown[] = [];
        for await (const p of stream as AsyncIterable<unknown>) parts.push(p);
        return parts;
      }

      // Call generate on both providers to exercise the _createClient -> resolveAuthBackedClient -> callback path.
      const s1 = await vProvider.generate('', [], [{ role: 'user', content: [{ type: 'text', text: 'hi' }], toolCalls: [] }]);
      const p1 = await drain(s1);

      const s2 = await nvProvider.generate('', [], [{ role: 'user', content: [{ type: 'text', text: 'hello' }], toolCalls: [] }]);
      const p2 = await drain(s2);

      // Both streams should have produced output from our mocked GoogleGenAI
      __testAugmentVitest_dcea1c7fe3a9.expect(p1.length).toBeGreaterThan(0);
      __testAugmentVitest_dcea1c7fe3a9.expect(p2.length).toBeGreaterThan(0);

      // requireProviderApiKey should have been called exactly once for the
      // non-vertexai provider. Validate the recorded provider name.
      __testAugmentVitest_dcea1c7fe3a9.expect(calls.length).toBe(1);
      __testAugmentVitest_dcea1c7fe3a9.expect(calls[0]!.prov).toBe('GoogleGenAIChatProvider');
    });
  });


});




import * as __testAugmentVitest_dcea1c7fe3a9 from "vitest";

const __testAugmentLoadTarget_1ea4df97aef2 = async () => {
  __testAugmentVitest_dcea1c7fe3a9.vi.doUnmock("../src/providers/google-genai.js");
  __testAugmentVitest_dcea1c7fe3a9.vi.resetModules();
  return import("../src/providers/google-genai.js");
};
