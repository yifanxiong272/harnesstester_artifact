import { derefJsonSchema, normalizeKimiToolSchema } from '#/providers/kimi-schema';
import { describe, expect, it, vi } from 'vitest';

describe('derefJsonSchema', () => {








  __testAugmentVitest_9fc805dc4d94.it("leaves_primitive_items_in_combinator_untouched_round_018_pass_02", async () => {
    const { normalizeKimiToolSchema } = await __testAugmentLoadTarget_18b9b2ed0b08();

    // anyOf contains a primitive item. visitChildSchemas will call the visitor
    // for each array item; normalizeProperty must early-return for non-record
    // items (recurseSchema no-op). The primitive should remain unchanged.
    const schema = {
      anyOf: ['plain', { enum: ['x'] }],
    } as Record<string, unknown>;

    const result = normalizeKimiToolSchema(schema) as Record<string, unknown>;

    // The primitive branch must be preserved verbatim while object branches are normalized.
    __testAugmentVitest_9fc805dc4d94.expect(result.anyOf).toBeDefined();
    __testAugmentVitest_9fc805dc4d94.expect(result.anyOf[0]).toBe('plain');
    // The object branch should have been normalized (enum -> type added).
    __testAugmentVitest_9fc805dc4d94.expect(result.anyOf[1]).toEqual({ enum: ['x'], type: 'string' });
  });
});


import * as __testAugmentVitest_9fc805dc4d94 from "vitest";

const __testAugmentLoadTarget_18b9b2ed0b08 = async () => {
  __testAugmentVitest_9fc805dc4d94.vi.doUnmock("../../src/providers/kimi-schema.js");
  __testAugmentVitest_9fc805dc4d94.vi.resetModules();
  return import("../../src/providers/kimi-schema.js");
};
