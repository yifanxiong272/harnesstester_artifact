import { derefJsonSchema, normalizeKimiToolSchema } from '#/providers/kimi-schema';
import { describe, expect, it, vi } from 'vitest';

describe('derefJsonSchema', () => {








  __testAugmentVitest_9fc805dc4d94.it("preserves_ref_when_definition_key_missing_round_018_pass_02", async () => {
    const { derefJsonSchema } = await __testAugmentLoadTarget_18b9b2ed0b08();

    // A $ref that targets a missing key in an object bucket should be left
    // unresolved; resolveLocalJsonPointer encounters the hasOwn() negative path.
    const schema = {
      type: 'object',
      properties: {
        missing: { $ref: '#/$defs/NotHere' },
      },
      $defs: {},
    } as Record<string, unknown>;

    const result = derefJsonSchema(schema) as Record<string, unknown>;

    // The property should still be a $ref since the pointer could not be resolved.
    __testAugmentVitest_9fc805dc4d94.expect((result.properties as any).missing.$ref).toBe('#/$defs/NotHere');
    // Because resolution failed, the $defs bucket must be preserved.
    __testAugmentVitest_9fc805dc4d94.expect(result.$defs).toBeDefined();
  });
});


import * as __testAugmentVitest_9fc805dc4d94 from "vitest";

const __testAugmentLoadTarget_18b9b2ed0b08 = async () => {
  __testAugmentVitest_9fc805dc4d94.vi.doUnmock("../../src/providers/kimi-schema.js");
  __testAugmentVitest_9fc805dc4d94.vi.resetModules();
  return import("../../src/providers/kimi-schema.js");
};
