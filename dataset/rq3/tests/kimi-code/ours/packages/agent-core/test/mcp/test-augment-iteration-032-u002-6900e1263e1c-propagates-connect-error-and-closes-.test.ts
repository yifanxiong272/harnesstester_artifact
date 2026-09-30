import { createServer, type Server } from 'node:http';
import type { AddressInfo } from 'node:net';

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import { SseError } from '@modelcontextprotocol/sdk/client/sse.js';
import { afterEach, describe, expect, it } from 'vitest';
import { z } from 'zod';

import { SseMcpClient, isTerminalSseTransportError } from '../../src/mcp/client-sse';

const cleanups: Array<() => Promise<void> | void> = [];

afterEach(async () => {
  for (const cleanup of cleanups.splice(0)) {
    await cleanup();
  }
});

async function startInProcessSseMcpServer(opts?: {
  authToken?: string;
}): Promise<{ url: string; close: () => Promise<void> }> {
  const transports = new Map<string, SSEServerTransport>();
  const httpServer: Server = createServer((req, res) => {
    if (opts?.authToken !== undefined) {
      const auth = req.headers['authorization'];
      if (auth !== `Bearer ${opts.authToken}`) {
        res.writeHead(401, { 'content-type': 'text/plain' });
        res.end('unauthorized');
        return;
      }
    }

    const url = new URL(req.url ?? '/', 'http://127.0.0.1');
    if (req.method === 'GET' && url.pathname === '/mcp') {
      const mcpServer = new McpServer({ name: 'mock-sse', version: '0.0.1' });
      mcpServer.registerTool(
        'echo',
        { description: 'Echoes text', inputSchema: { text: z.string() } },
        ({ text }) => ({ content: [{ type: 'text', text }] }),
      );
      const transport = new SSEServerTransport('/messages', res);
      transports.set(transport.sessionId, transport);
      transport.onclose = () => {
        transports.delete(transport.sessionId);
      };
      void mcpServer.connect(transport);
      return;
    }

    if (req.method === 'POST' && url.pathname === '/messages') {
      const sessionId = url.searchParams.get('sessionId');
      const transport = sessionId === null ? undefined : transports.get(sessionId);
      if (transport === undefined) {
        res.writeHead(404).end('Session not found');
        return;
      }
      void transport.handlePostMessage(req, res);
      return;
    }

    res.writeHead(404).end('not found');
  });

  await new Promise<void>((resolve) => {
    httpServer.listen(0, '127.0.0.1', resolve);
  });
  const port = (httpServer.address() as AddressInfo).port;

  return {
    url: `http://127.0.0.1:${port}/mcp`,
    async close() {
      await Promise.all([...transports.values()].map((transport) => transport.close()));
      await new Promise<void>((resolve, reject) => {
        httpServer.close((err) => {
          if (err) {
            reject(err);
            return;
          }
          resolve();
        });
      });
    },
  };
}

describe('SseMcpClient', () => {


  __testAugmentVitest_5aee1ab402f9.it("propagates_connect_error_and_closes_client_round_032", async () => {
    const createdClients: any[] = [];

    __testAugmentVitest_5aee1ab402f9.vi.doMock("@modelcontextprotocol/sdk/client/index.js", () => {
      return {
        Client: class {
          closeCalled = 0;
          constructor() {
            createdClients.push(this);
          }
          async connect() {
            throw new Error('connect-failed');
          }
          async close() {
            this.closeCalled++;
          }
          async listTools() { return { tools: [] }; }
          async callTool() { return {}; }
        },
      };
    });

    __testAugmentVitest_5aee1ab402f9.vi.doMock("@modelcontextprotocol/sdk/client/sse.js", () => {
      class SSEClientTransport { constructor(_url: URL, _opts?: unknown) {} }
      class SseError extends Error {}
      return { SSEClientTransport, SseError };
    });

    __testAugmentVitest_5aee1ab402f9.vi.doMock("../../src/mcp/client-remote", () => ({ buildMcpRemoteHeaders: (_c:any,_e:any) => undefined }));
    __testAugmentVitest_5aee1ab402f9.vi.doMock("../../src/mcp/client-shared", () => ({
      buildRequestOptions: () => ({}),
      KIMI_MCP_CLIENT_NAME: 'kimi',
      KIMI_MCP_CLIENT_VERSION: 'v',
      toMcpToolDefinition: (t:any)=>t,
      toMcpToolResult: (r:any)=>r,
    }));

    const mod = await __testAugmentLoadTarget_0685929a9f6d();
    const { SseMcpClient } = mod as { SseMcpClient: any };

    const client = new SseMcpClient({ url: 'http://example.local/mcp' });

    await __testAugmentVitest_5aee1ab402f9.expect(client.connect()).rejects.toThrow('connect-failed');

    // underlying client should have been closed as part of cleanup on connect failure
    __testAugmentVitest_5aee1ab402f9.expect(createdClients.length).toBeGreaterThan(0);
    __testAugmentVitest_5aee1ab402f9.expect(createdClients[0].closeCalled).toBeGreaterThanOrEqual(1);
  });
});

import * as __testAugmentVitest_5aee1ab402f9 from "vitest";

const __testAugmentLoadTarget_0685929a9f6d = async () => {
  __testAugmentVitest_5aee1ab402f9.vi.doUnmock("../../src/mcp/client-sse.js");
  __testAugmentVitest_5aee1ab402f9.vi.resetModules();
  return import("../../src/mcp/client-sse.js");
};
