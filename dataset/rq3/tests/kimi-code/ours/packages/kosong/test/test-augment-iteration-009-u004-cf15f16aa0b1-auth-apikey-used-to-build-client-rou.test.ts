import { ChatProviderError } from '#/errors';
import type { ContentPart, Message, StreamedMessagePart, ToolCall } from '#/message';
import { AnthropicChatProvider, resolveDefaultMaxTokens } from '#/providers/anthropic';
import type { Tool } from '#/tool';
import { describe, it, expect, vi } from 'vitest';

function makeAnthropicResponse(model: string = 'k25') {
  return {
    id: 'msg_test_123',
    type: 'message',
    role: 'assistant',
    model,
    content: [{ type: 'text', text: 'Hello' }],
    stop_reason: 'end_turn',
    usage: { input_tokens: 10, output_tokens: 5 },
  };
}

function createProvider(
  model: string = 'k25',
  metadata?: Record<string, string>,
): AnthropicChatProvider {
  return new AnthropicChatProvider({
    model,
    apiKey: 'test-key',
    defaultMaxTokens: 1024,
    metadata,
    stream: false,
  });
}

function createStreamProvider(model: string = 'k25'): AnthropicChatProvider {
  return new AnthropicChatProvider({
    model,
    apiKey: 'test-key',
    defaultMaxTokens: 1024,
    stream: true,
  });
}

type AnthropicGenerationState = {
  max_tokens?: number | undefined;
  temperature?: number | undefined;
  top_k?: number | undefined;
  top_p?: number | undefined;
  thinking?:
    | { type: 'disabled' }
    | { type: 'adaptive'; display?: string | undefined }
    | { type: 'enabled'; budget_tokens: number }
    | undefined;
  output_config?: { effort: string } | undefined;
  betaFeatures?: string[] | undefined;
};

function getGenerationState(provider: AnthropicChatProvider): AnthropicGenerationState {
  return Reflect.get(provider, '_generationKwargs') as AnthropicGenerationState;
}

/** Capture the request body sent to Anthropic by mocking the client (non-stream mode). */
async function captureRequestBody(
  provider: AnthropicChatProvider,
  systemPrompt: string,
  tools: Tool[],
  history: Message[],
): Promise<Record<string, unknown>> {
  let capturedParams: Record<string, unknown> | undefined;
  let capturedOptions: Record<string, unknown> | undefined;

  (provider as any)._client.messages.create = vi
    .fn()
    .mockImplementation((params: unknown, options?: unknown) => {
      capturedParams = params as Record<string, unknown>;
      capturedOptions = options as Record<string, unknown> | undefined;
      return Promise.resolve(makeAnthropicResponse());
    });

  const stream = await provider.generate(systemPrompt, tools, history);
  for await (const part of stream) {
    void part;
  }

  if (capturedParams === undefined) {
    throw new Error('Expected provider.generate() to call messages.create');
  }

  const result = { ...capturedParams };
  if (capturedOptions !== undefined && capturedOptions['headers'] !== undefined) {
    result['_extra_headers'] = capturedOptions['headers'];
  }
  return result;
}

/** Create a mock stream that yields the given events as an async iterable. */
function mockStream(events: unknown[]) {
  return {
    async *[Symbol.asyncIterator]() {
      for (const event of events) {
        yield event;
      }
    },
  };
}

/** Collect all parts from a StreamedMessage. */
async function collectParts(
  streamedMessage: AsyncIterable<StreamedMessagePart>,
): Promise<StreamedMessagePart[]> {
  const parts: StreamedMessagePart[] = [];
  for await (const part of streamedMessage) {
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

const B64_PNG =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAA' +
  'DUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
describe('AnthropicChatProvider', () => {












  __testAugmentVitest_b2e1d68bafdb.it("per-request auth.apiKey is used to build a client when constructor has none_round_009", async () => {
    // Create provider without constructor apiKey
    const { AnthropicChatProvider } = await __testAugmentLoadTarget_34a1203bd379();
    const prov = new AnthropicChatProvider({ model: 'k25', stream: false });

    // Replace _buildClient to observe the apiKey used to construct a client
    const fakeMessagesCreate = __testAugmentVitest_b2e1d68bafdb.vi.fn().mockResolvedValue(makeAnthropicResponse());
    const fakeBuild = __testAugmentVitest_b2e1d68bafdb.vi.fn().mockReturnValue({ messages: { create: fakeMessagesCreate } });
    (prov as any)._buildClient = fakeBuild;

    // Provide per-request auth with apiKey - this should be passed to _buildClient
    const options = { auth: { apiKey: 'per-request-key' } } as any;

    const stream = await prov.generate('', [], [{ role: 'user', content: [{ type: 'text', text: 'Hi' }], toolCalls: [] }], options);
    // consume to ensure messages.create is awaited
    for await (const _ of stream) { /* noop */ }

    __testAugmentVitest_b2e1d68bafdb.expect(fakeBuild).toHaveBeenCalled();
    // first arg with which _buildClient was called should equal the per-request api key
    __testAugmentVitest_b2e1d68bafdb.expect(fakeBuild.mock.calls[0]![0]).toBe('per-request-key');
    __testAugmentVitest_b2e1d68bafdb.expect(fakeMessagesCreate).toHaveBeenCalled();
  });
});



import * as __testAugmentVitest_b2e1d68bafdb from "vitest";

const __testAugmentLoadTarget_34a1203bd379 = async () => {
  __testAugmentVitest_b2e1d68bafdb.vi.doUnmock("../src/providers/anthropic.js");
  __testAugmentVitest_b2e1d68bafdb.vi.resetModules();
  return import("../src/providers/anthropic.js");
};
