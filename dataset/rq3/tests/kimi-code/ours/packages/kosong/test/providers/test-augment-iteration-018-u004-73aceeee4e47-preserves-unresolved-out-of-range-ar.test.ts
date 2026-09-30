import { derefJsonSchema, normalizeKimiToolSchema } from '#/providers/kimi-schema';
import { describe, expect, it, vi } from 'vitest';

describe('derefJsonSchema', () => {








  __testAugmentVitest_9fc805dc4d94.it("preserves_unresolved_out_of_range_array_index_ref_round_018", async () => {
    const { derefJsonSchema } = await __testAugmentLoadTarget_18b9b2ed0b08();

    // The $ref uses a numeric index that is out-of-range (1 >= length 1).
    // resolveLocalJsonPointer should treat this as not found and leave the $ref.
    const schema = {
      type: 'object',
      properties: {
        item: { $ref: '#/$defs/Arr/1' },
      },
      $defs: {
        Arr: ['only'],
      },
    } as Record<string, unknown>;

    const result = derefJsonSchema(schema) as Record<string, unknown>;

    __testAugmentVitest_9fc805dc4d94.expect((result.properties as any).item.$ref).toBe('#/$defs/Arr/1');
    __testAugmentVitest_9fc805dc4d94.expect(result.$defs).toBeDefined();
  });
});


import * as __testAugmentVitest_9fc805dc4d94 from "vitest";

const __testAugmentLoadTarget_18b9b2ed0b08 = async () => {
  __testAugmentVitest_9fc805dc4d94.vi.doUnmock("../../src/providers/kimi-schema.js");
  __testAugmentVitest_9fc805dc4d94.vi.resetModules();
  return import("../../src/providers/kimi-schema.js");
};
