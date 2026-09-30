import { derefJsonSchema, normalizeKimiToolSchema } from '#/providers/kimi-schema';
import { describe, expect, it, vi } from 'vitest';

describe('derefJsonSchema', () => {








  __testAugmentVitest_9fc805dc4d94.it("normalizes_items_array_schema_or_array_round_018_pass_03", async () => {
    const { normalizeKimiToolSchema } = await __testAugmentLoadTarget_18b9b2ed0b08();

    // The `items` keyword may be a schema-or-array. Provide an array form where
    // the first element is an object (should be normalized) and the second is a
    // primitive (should be left intact).
    const schema = {
      properties: {
        mix: {
          items: [
            { enum: ['a', 'b'] },
            'plain',
          ],
        },
      },
    } as Record<string, unknown>;

    const result = normalizeKimiToolSchema(schema) as Record<string, unknown>;

    // The object branch should gain a type; the primitive branch should be unchanged.
    __testAugmentVitest_9fc805dc4d94.expect(result.properties).toBeDefined();
    const items = (result.properties as any).mix.items;
    __testAugmentVitest_9fc805dc4d94.expect(Array.isArray(items)).toBe(true);
    __testAugmentVitest_9fc805dc4d94.expect(items[0]).toEqual({ enum: ['a', 'b'], type: 'string' });
    __testAugmentVitest_9fc805dc4d94.expect(items[1]).toBe('plain');
  });
});


import * as __testAugmentVitest_9fc805dc4d94 from "vitest";

const __testAugmentLoadTarget_18b9b2ed0b08 = async () => {
  __testAugmentVitest_9fc805dc4d94.vi.doUnmock("../../src/providers/kimi-schema.js");
  __testAugmentVitest_9fc805dc4d94.vi.resetModules();
  return import("../../src/providers/kimi-schema.js");
};
