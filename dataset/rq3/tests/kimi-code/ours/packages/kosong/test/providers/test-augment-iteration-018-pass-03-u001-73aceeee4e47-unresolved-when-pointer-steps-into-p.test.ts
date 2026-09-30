import { derefJsonSchema, normalizeKimiToolSchema } from '#/providers/kimi-schema';
import { describe, expect, it, vi } from 'vitest';

describe('derefJsonSchema', () => {








  __testAugmentVitest_9fc805dc4d94.it("unresolved_when_pointer_steps_into_primitive_midpath_round_018_pass_03", async () => {
    const { derefJsonSchema } = await __testAugmentLoadTarget_18b9b2ed0b08();

    // root.a is a primitive; pointer '#/a/x' should fail because after resolving
    // '#/a' current becomes a primitive and further path parts cannot be traversed.
    const schema = {
      type: 'object',
      properties: {
        thing: { $ref: '#/$defs/RefToPrimitive/x' },
      },
      $defs: {
        RefToPrimitive: 'just-a-string',
      },
    } as Record<string, unknown>;

    const result = derefJsonSchema(schema) as Record<string, unknown>;

    // The unresolved $ref should remain in place because the pointer could not be fully followed.
    __testAugmentVitest_9fc805dc4d94.expect((result.properties as any).thing.$ref).toBe('#/$defs/RefToPrimitive/x');
    // $defs must be preserved when unresolved refs remain.
    __testAugmentVitest_9fc805dc4d94.expect(result.$defs).toBeDefined();
  });
});


import * as __testAugmentVitest_9fc805dc4d94 from "vitest";

const __testAugmentLoadTarget_18b9b2ed0b08 = async () => {
  __testAugmentVitest_9fc805dc4d94.vi.doUnmock("../../src/providers/kimi-schema.js");
  __testAugmentVitest_9fc805dc4d94.vi.resetModules();
  return import("../../src/providers/kimi-schema.js");
};
