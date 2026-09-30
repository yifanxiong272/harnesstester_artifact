import { derefJsonSchema, normalizeKimiToolSchema } from '#/providers/kimi-schema';
import { describe, expect, it, vi } from 'vitest';

describe('derefJsonSchema', () => {








  __testAugmentVitest_9fc805dc4d94.it("preserves_unresolved_invalid_array_index_ref_round_018", async () => {
    const { derefJsonSchema } = await __testAugmentLoadTarget_18b9b2ed0b08();

    // The $ref targets an array index using a non-numeric segment ('two').
    // parseJsonPointerArrayIndex should return null and resolveLocalJsonPointer
    // should report not found; deref should leave the $ref as-is and preserve $defs.
    const schema = {
      type: 'object',
      properties: {
        p: { $ref: '#/$defs/Arr/two' },
      },
      $defs: {
        Arr: ['first'],
      },
    } as Record<string, unknown>;

    const result = derefJsonSchema(schema) as Record<string, unknown>;

    // The unresolved $ref should remain unchanged on the property.
    __testAugmentVitest_9fc805dc4d94.expect((result.properties as any).p.$ref).toBe('#/$defs/Arr/two');
    // Because the $ref was unresolved, the $defs bucket must be preserved.
    __testAugmentVitest_9fc805dc4d94.expect(result.$defs).toBeDefined();
  });
});


import * as __testAugmentVitest_9fc805dc4d94 from "vitest";

const __testAugmentLoadTarget_18b9b2ed0b08 = async () => {
  __testAugmentVitest_9fc805dc4d94.vi.doUnmock("../../src/providers/kimi-schema.js");
  __testAugmentVitest_9fc805dc4d94.vi.resetModules();
  return import("../../src/providers/kimi-schema.js");
};
