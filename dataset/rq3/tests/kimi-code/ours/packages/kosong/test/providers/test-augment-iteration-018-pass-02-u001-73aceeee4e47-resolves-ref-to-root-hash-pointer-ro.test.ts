import { derefJsonSchema, normalizeKimiToolSchema } from '#/providers/kimi-schema';
import { describe, expect, it, vi } from 'vitest';

describe('derefJsonSchema', () => {








  __testAugmentVitest_9fc805dc4d94.it("resolves_ref_to_root_hash_pointer_round_018_pass_02", async () => {
    const { derefJsonSchema } = await __testAugmentLoadTarget_18b9b2ed0b08();

    // A $ref that points to '#' must resolve to the document root. The root
    // contains a simple bucket which should be visible through the resolved node.
    const schema = {
      base: { const: 'z' },
      properties: {
        refRoot: { $ref: '#' },
      },
    } as Record<string, unknown>;

    const result = derefJsonSchema(schema) as Record<string, unknown>;

    // The resolved node should include the root's `base` bucket merged into the
    // resolved value (sibling keys on the ref site would override but none exist).
    __testAugmentVitest_9fc805dc4d94.expect(result).toBeDefined();
    __testAugmentVitest_9fc805dc4d94.expect((result.properties as any).refRoot.base).toEqual({ const: 'z' });
  });
});


import * as __testAugmentVitest_9fc805dc4d94 from "vitest";

const __testAugmentLoadTarget_18b9b2ed0b08 = async () => {
  __testAugmentVitest_9fc805dc4d94.vi.doUnmock("../../src/providers/kimi-schema.js");
  __testAugmentVitest_9fc805dc4d94.vi.resetModules();
  return import("../../src/providers/kimi-schema.js");
};
