import {
  APIContextOverflowError,
  APIProviderRateLimitError,
  APIStatusError,
  ChatProviderError,
} from '#/errors';
import { generate } from '#/generate';
import type { ContentPart, Message, StreamedMessagePart, ToolCall } from '#/message';
import {
  OpenAIResponsesChatProvider,
  OpenAIResponsesStreamedMessage,
} from '#/providers/openai-responses';
import type { Tool } from '#/tool';
import { describe, it, expect, vi } from 'vitest';

function makeResponsesAPIResponse() {
  return {
    id: 'resp_test123',
    object: 'response',
    created_at: 1234567890,
    status: 'completed',
    model: 'gpt-4.1',
    output: [
      {
        type: 'message',
        id: 'msg_test',
        role: 'assistant',
        content: [{ type: 'output_text', text: 'Hello', annotations: [] }],
      },
    ],
    usage: { input_tokens: 10, output_tokens: 5, total_tokens: 15 },
  };
}

function createProvider(): OpenAIResponsesChatProvider {
  return new OpenAIResponsesChatProvider({
    model: 'gpt-4.1',
    apiKey: 'test-key',
  });
}

/** Capture the request body sent to the Responses API by mocking the client. */
async function captureRequestBody(
  provider: OpenAIResponsesChatProvider,
  systemPrompt: string,
  tools: Tool[],
  history: Message[],
): Promise<Record<string, unknown>> {
  let capturedBody: Record<string, unknown> | undefined;

  (provider as any)._stream = false;

  ((provider as any)._client.responses as unknown as Record<string, unknown>)['create'] = vi
    .fn()
    .mockImplementation((params: unknown) => {
      capturedBody = params as Record<string, unknown>;
      return Promise.resolve(makeResponsesAPIResponse());
    });

  const stream = await provider.generate(systemPrompt, tools, history);
  for await (const part of stream) {
    void part;
  }

  if (capturedBody === undefined) {
    throw new Error('Expected provider.generate() to call responses.create');
  }
  return capturedBody;
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

describe('OpenAIResponsesChatProvider', () => {






  describe('streaming', () => {





















    __testAugmentVitest_d5f3efd218ca.it("throws_on_function_call_arguments_done_without_prior_round_008", async () => {
      const events = [
        {
          type: 'response.function_call_arguments.done',
          arguments: '{"ok":true}',
        },
      ];

      const stream = new OpenAIResponsesStreamedMessage(makeAsyncIterable(events), true);

      // Final-arguments frames without a prior registered index should cause a
      // decode error referencing the unindexed marker.
      await __testAugmentVitest_d5f3efd218ca.expect(collectStreamParts(stream)).rejects.toThrow(
        /received final function-call arguments for unknown stream index <unindexed>/,
      );
    });
  });
});

async function collectStreamParts(
  stream: OpenAIResponsesStreamedMessage,
): Promise<StreamedMessagePart[]> {
  const parts: StreamedMessagePart[] = [];
  for await (const part of stream) {
    parts.push(part);
  }
  return parts;
}

function makeAsyncIterable(
  events: Record<string, unknown>[],
): AsyncIterable<Record<string, unknown>> {
  return {
    [Symbol.asyncIterator](): AsyncIterator<Record<string, unknown>> {
      let index = 0;
      return {
        next(): Promise<IteratorResult<Record<string, unknown>>> {
          if (index < events.length) {
            return Promise.resolve({ value: events[index++]!, done: false });
          }
          return Promise.resolve({
            value: undefined as unknown as Record<string, unknown>,
            done: true,
          });
        },
      };
    },
  };
}

import * as __testAugmentVitest_d5f3efd218ca from "vitest";

const __testAugmentLoadTarget_caf723cd3437 = async () => {
  __testAugmentVitest_d5f3efd218ca.vi.doUnmock("../src/providers/openai-responses.js");
  __testAugmentVitest_d5f3efd218ca.vi.resetModules();
  return import("../src/providers/openai-responses.js");
};
