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














    __testAugmentVitest_dcea1c7fe3a9.it("maps GoogleApiError to APIStatusError_round_013", async () => {
      // Mock the @google/genai export used by the module so we can produce an
      // ApiError instance that passes the `instanceof` check inside the
      // implementation. Register the mock before loading the target.
      __testAugmentVitest_dcea1c7fe3a9.vi.doMock('@google/genai', () => {
        class ApiError extends Error {
          status: number;
          constructor(message: string, status: number) {
            super(message);
            this.status = status;
          }
        }
        // Minimal stub for GoogleGenAI class (not used in this test)
        class GoogleGenAI {}
        return { ApiError, GoogleGenAI };
      });

      // Load the target after setting up the mock so the module picks up our
      // mocked ApiError class.
      const mod = await __testAugmentLoadTarget_1ea4df97aef2();
      const { convertGoogleGenAIError } = mod as unknown as {
        convertGoogleGenAIError: (e: unknown) => unknown;
      };

      // Construct an instance of the mocked ApiError and convert it.
      const mocked = (await import('@google/genai')) as any;
      const ApiError = mocked.ApiError as new (m: string, s: number) => Error & { status: number };
      const err = new ApiError('upstream failure', 418);

      const result = convertGoogleGenAIError(err);

      // The module should call normalizeAPIStatusError and return an object
      // carrying the numeric status. Assert that the normalized result exposes
      // the numeric statusCode we passed.
      __testAugmentVitest_dcea1c7fe3a9.expect((result as any).statusCode).toBe(418);
    });
  });


});




import * as __testAugmentVitest_dcea1c7fe3a9 from "vitest";

const __testAugmentLoadTarget_1ea4df97aef2 = async () => {
  __testAugmentVitest_dcea1c7fe3a9.vi.doUnmock("../src/providers/google-genai.js");
  __testAugmentVitest_dcea1c7fe3a9.vi.resetModules();
  return import("../src/providers/google-genai.js");
};
