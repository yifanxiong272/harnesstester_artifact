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














    __testAugmentVitest_dcea1c7fe3a9.it("SAFETY finishReason maps to filtered_round_013_pass_02", async () => {
      const { GoogleGenAIStreamedMessage } = __testAugmentTarget_1ea4df97aef2 as unknown as {
        GoogleGenAIStreamedMessage: typeof Object;
      };

      const response = {
        candidates: [
          {
            content: { parts: [{ text: 'sensitive' }] },
            finishReason: 'SAFETY',
          },
        ],
      } as unknown as Record<string, unknown>;

      const msg = new (GoogleGenAIStreamedMessage as any)(response, false);
      const collected: unknown[] = [];
      for await (const p of msg) collected.push(p);

      __testAugmentVitest_dcea1c7fe3a9.expect(collected).toEqual([{ type: 'text', text: 'sensitive' }]);
      __testAugmentVitest_dcea1c7fe3a9.expect(msg.rawFinishReason).toBe('SAFETY');
      __testAugmentVitest_dcea1c7fe3a9.expect(msg.finishReason).toBe('filtered');
    });
  });


});




import * as __testAugmentVitest_dcea1c7fe3a9 from "vitest";

import * as __testAugmentTarget_1ea4df97aef2 from "../src/providers/google-genai.js";

const __testAugmentLoadTarget_1ea4df97aef2 = async () => {
  __testAugmentVitest_dcea1c7fe3a9.vi.doUnmock("../src/providers/google-genai.js");
  __testAugmentVitest_dcea1c7fe3a9.vi.resetModules();
  return import("../src/providers/google-genai.js");
};
