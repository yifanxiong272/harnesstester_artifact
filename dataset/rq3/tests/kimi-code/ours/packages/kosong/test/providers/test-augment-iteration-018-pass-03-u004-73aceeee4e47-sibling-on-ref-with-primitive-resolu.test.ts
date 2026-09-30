import { derefJsonSchema, normalizeKimiToolSchema } from '#/providers/kimi-schema';
import { describe, expect, it, vi } from 'vitest';

describe('derefJsonSchema', () => {








  __testAugmentVitest_9fc805dc4d94.it("sibling_on_ref_with_primitive_resolution_round_018_pass_03", async () => {
    const { derefJsonSchema } = await __testAugmentLoadTarget_18b9b2ed0b08();

    // When a $ref resolves to a primitive value the code should return the
    // primitive (not merge sibling keys). Create a def that is a primitive and
    // a ref that also carries a sibling `description` which must be dropped.
    const schema = {
      properties: {
        simple: { $ref: '#/$defs/Prim', description: 'local-desc' },
      },
      $defs: {
        Prim: 'VALUE',
      },
    } as Record<string, unknown>;

    const result = derefJsonSchema(schema) as Record<string, unknown>;

    // The property should be replaced by the primitive 'VALUE' (not an object with description).
    __testAugmentVitest_9fc805dc4d94.expect((result.properties as any).simple).toBe('VALUE');
    // Since the ref was successfully resolved to a primitive, there should be no unresolved refs into $defs.
    __testAugmentVitest_9fc805dc4d94.expect(result.$defs).toBeUndefined();
  });
});


import * as __testAugmentVitest_9fc805dc4d94 from "vitest";

const __testAugmentLoadTarget_18b9b2ed0b08 = async () => {
  __testAugmentVitest_9fc805dc4d94.vi.doUnmock("../../src/providers/kimi-schema.js");
  __testAugmentVitest_9fc805dc4d94.vi.resetModules();
  return import("../../src/providers/kimi-schema.js");
};
