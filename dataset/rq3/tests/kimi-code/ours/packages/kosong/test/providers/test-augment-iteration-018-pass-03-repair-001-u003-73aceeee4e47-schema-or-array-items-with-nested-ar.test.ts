import { derefJsonSchema, normalizeKimiToolSchema } from '#/providers/kimi-schema';
import { describe, expect, it, vi } from 'vitest';

describe('derefJsonSchema', () => {








  __testAugmentVitest_9fc805dc4d94.it("schema_or_array_items_with_nested_array_element_round_018_pass_03", async () => {
    const { normalizeKimiToolSchema } = await __testAugmentLoadTarget_18b9b2ed0b08();

    // `items` is a schema-or-array. Provide an array where the first element is
    // itself an array (non-record) and the second is an object that should be
    // normalized. The visitor must skip (early-return) non-record items while
    // normalizing object items.
    const schema = {
      properties: {
        list: {
          items: [
            [ { enum: ['x'] } ], // nested array: visitor will call normalizeProperty on this array (non-record) -> early return
            { enum: ['y'] },     // object: should be normalized to include type
          ],
        },
      },
    } as Record<string, unknown>;

    const result = normalizeKimiToolSchema(schema) as Record<string, unknown>;

    const items = (result.properties as any).list.items;
    __testAugmentVitest_9fc805dc4d94.expect(Array.isArray(items)).toBe(true);
    // The nested-array element should remain an array (unchanged).
    __testAugmentVitest_9fc805dc4d94.expect(Array.isArray(items[0])).toBe(true);
    // The object element should have been normalized to include an inferred type.
    __testAugmentVitest_9fc805dc4d94.expect(items[1]).toEqual({ enum: ['y'], type: 'string' });
  });
});


import * as __testAugmentVitest_9fc805dc4d94 from "vitest";

const __testAugmentLoadTarget_18b9b2ed0b08 = async () => {
  __testAugmentVitest_9fc805dc4d94.vi.doUnmock("../../src/providers/kimi-schema.js");
  __testAugmentVitest_9fc805dc4d94.vi.resetModules();
  return import("../../src/providers/kimi-schema.js");
};
