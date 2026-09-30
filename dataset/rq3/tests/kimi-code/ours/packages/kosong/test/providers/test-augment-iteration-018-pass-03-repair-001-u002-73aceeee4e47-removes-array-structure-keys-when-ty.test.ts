import { derefJsonSchema, normalizeKimiToolSchema } from '#/providers/kimi-schema';
import { describe, expect, it, vi } from 'vitest';

describe('derefJsonSchema', () => {








  __testAugmentVitest_9fc805dc4d94.it("removes_array_structure_keys_when_type_changed_to_string_round_018_pass_03", async () => {
    const { normalizeKimiToolSchema } = await __testAugmentLoadTarget_18b9b2ed0b08();

    // A provider may emit an explicit type of 'array' while an enum shows the
    // values are strings. Normalization should change the type to 'string' and
    // strip array-specific structure keys like minItems.
    const schema = {
      type: 'object',
      properties: {
        field: {
          type: 'array',
          minItems: 1,
          enum: ['a', 'b'],
        },
      },
    } as Record<string, unknown>;

    const result = normalizeKimiToolSchema(schema) as Record<string, unknown>;

    const field = (result.properties as any).field;
    // Type must be repaired to 'string' and array-specific keys removed.
    __testAugmentVitest_9fc805dc4d94.expect(field.type).toBe('string');
    __testAugmentVitest_9fc805dc4d94.expect(field.enum).toEqual(['a', 'b']);
    __testAugmentVitest_9fc805dc4d94.expect(field.minItems).toBeUndefined();
  });
});


import * as __testAugmentVitest_9fc805dc4d94 from "vitest";

const __testAugmentLoadTarget_18b9b2ed0b08 = async () => {
  __testAugmentVitest_9fc805dc4d94.vi.doUnmock("../../src/providers/kimi-schema.js");
  __testAugmentVitest_9fc805dc4d94.vi.resetModules();
  return import("../../src/providers/kimi-schema.js");
};
