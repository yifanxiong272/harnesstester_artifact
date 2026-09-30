import { derefJsonSchema, normalizeKimiToolSchema } from '#/providers/kimi-schema';
import { describe, expect, it, vi } from 'vitest';

describe('derefJsonSchema', () => {








  __testAugmentVitest_9fc805dc4d94.it("throws_when_root_normalizes_to_non_object_round_018", async () => {
    const { normalizeKimiToolSchema } = await __testAugmentLoadTarget_18b9b2ed0b08();

    // Construct a schema whose top-level node is a $ref to a primitive in $defs.
    // derefJsonSchema will resolve the top-level to a primitive, so
    // ensureKimiPropertyTypes will receive a non-object and must throw.
    const schema = {
      $ref: '#/$defs/Primitive',
      $defs: {
        Primitive: 'just-a-string',
      },
    } as unknown as Record<string, unknown>;

    __testAugmentVitest_9fc805dc4d94.expect(() => normalizeKimiToolSchema(schema)).toThrow(
      'JSON Schema root must normalize to an object.',
    );
  });
});


import * as __testAugmentVitest_9fc805dc4d94 from "vitest";

const __testAugmentLoadTarget_18b9b2ed0b08 = async () => {
  __testAugmentVitest_9fc805dc4d94.vi.doUnmock("../../src/providers/kimi-schema.js");
  __testAugmentVitest_9fc805dc4d94.vi.resetModules();
  return import("../../src/providers/kimi-schema.js");
};
