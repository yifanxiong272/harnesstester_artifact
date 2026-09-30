import { derefJsonSchema, normalizeKimiToolSchema } from '#/providers/kimi-schema';
import { describe, expect, it, vi } from 'vitest';

describe('derefJsonSchema', () => {








  __testAugmentVitest_9fc805dc4d94.it("preserves_definitions_when_cyclic_refs_in_definitions_round_018_pass_03", async () => {
    const { derefJsonSchema } = await __testAugmentLoadTarget_18b9b2ed0b08();

    // Create a cycle inside draft-7 `definitions` (A -> B -> A). The deref
    // implementation must preserve the `definitions` bucket when unresolved
    // cyclic refs remain so validators can resolve them.
    const schema = {
      type: 'object',
      properties: {
        a: { $ref: '#/definitions/A' },
      },
      definitions: {
        A: { properties: { next: { $ref: '#/definitions/B' } } },
        B: { properties: { back: { $ref: '#/definitions/A' } } },
      },
    } as Record<string, unknown>;

    const result = derefJsonSchema(schema) as Record<string, unknown>;

    // The `definitions` bucket must be preserved for cyclic refs.
    __testAugmentVitest_9fc805dc4d94.expect(result.definitions).toBeDefined();
    const json = JSON.stringify(result);
    __testAugmentVitest_9fc805dc4d94.expect(json).toContain('"$ref":"#/definitions/');
  });
});


import * as __testAugmentVitest_9fc805dc4d94 from "vitest";

const __testAugmentLoadTarget_18b9b2ed0b08 = async () => {
  __testAugmentVitest_9fc805dc4d94.vi.doUnmock("../../src/providers/kimi-schema.js");
  __testAugmentVitest_9fc805dc4d94.vi.resetModules();
  return import("../../src/providers/kimi-schema.js");
};
