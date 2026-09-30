import { derefJsonSchema, normalizeKimiToolSchema } from '#/providers/kimi-schema';
import { describe, expect, it, vi } from 'vitest';

describe('derefJsonSchema', () => {








  __testAugmentVitest_9fc805dc4d94.it("throws_for_non_json_enum_value_round_018", async () => {
    const { normalizeKimiToolSchema } = await __testAugmentLoadTarget_18b9b2ed0b08();

    // Use a Symbol (non-JSON) inside an enum. inferValueType will return undefined
    // for this item and inferTypeFromValues should throw the specific error.
    const badSymbol = Symbol('bad');
    const schema = {
      type: 'object',
      properties: {
        target: { enum: [badSymbol] as unknown[] },
      },
    } as Record<string, unknown>;

    __testAugmentVitest_9fc805dc4d94.expect(() => normalizeKimiToolSchema(schema)).toThrow(
      'Cannot infer JSON Schema type from non-JSON enum or const value.',
    );
  });
});


import * as __testAugmentVitest_9fc805dc4d94 from "vitest";

const __testAugmentLoadTarget_18b9b2ed0b08 = async () => {
  __testAugmentVitest_9fc805dc4d94.vi.doUnmock("../../src/providers/kimi-schema.js");
  __testAugmentVitest_9fc805dc4d94.vi.resetModules();
  return import("../../src/providers/kimi-schema.js");
};
