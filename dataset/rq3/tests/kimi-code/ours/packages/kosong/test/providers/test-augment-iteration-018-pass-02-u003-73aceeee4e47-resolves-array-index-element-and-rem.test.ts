import { derefJsonSchema, normalizeKimiToolSchema } from '#/providers/kimi-schema';
import { describe, expect, it, vi } from 'vitest';

describe('derefJsonSchema', () => {








  __testAugmentVitest_9fc805dc4d94.it("resolves_array_index_element_and_removes_defs_round_018_pass_02", async () => {
    const { derefJsonSchema } = await __testAugmentLoadTarget_18b9b2ed0b08();

    // A $ref targeting an array element by numeric index should inline that
    // element when the index is in-range. After full dereference, $defs should
    // be removed if no unresolved refs remain.
    const schema = {
      type: 'object',
      properties: {
        first: { $ref: '#/$defs/Arr/0' },
      },
      $defs: {
        Arr: [{ type: 'string' }],
      },
    } as Record<string, unknown>;

    const result = derefJsonSchema(schema) as Record<string, unknown>;

    // The property should be replaced by the referenced element.
    __testAugmentVitest_9fc805dc4d94.expect((result.properties as any).first).toEqual({ type: 'string' });
    // No unresolved refs into $defs remain, so $defs should be deleted.
    __testAugmentVitest_9fc805dc4d94.expect(result.$defs).toBeUndefined();
  });
});


import * as __testAugmentVitest_9fc805dc4d94 from "vitest";

const __testAugmentLoadTarget_18b9b2ed0b08 = async () => {
  __testAugmentVitest_9fc805dc4d94.vi.doUnmock("../../src/providers/kimi-schema.js");
  __testAugmentVitest_9fc805dc4d94.vi.resetModules();
  return import("../../src/providers/kimi-schema.js");
};
