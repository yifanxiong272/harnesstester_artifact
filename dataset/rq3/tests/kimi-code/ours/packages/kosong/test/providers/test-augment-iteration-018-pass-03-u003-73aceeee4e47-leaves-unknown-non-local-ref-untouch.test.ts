import { derefJsonSchema, normalizeKimiToolSchema } from '#/providers/kimi-schema';
import { describe, expect, it, vi } from 'vitest';

describe('derefJsonSchema', () => {








  __testAugmentVitest_9fc805dc4d94.it("leaves_unknown_non_local_ref_untouched_round_018_pass_03", async () => {
    const { derefJsonSchema } = await __testAugmentLoadTarget_18b9b2ed0b08();

    // Non-local (absolute) $ref should be treated as unknown by isLocalJsonPointerRef
    // and thus left in-place by resolveNode.
    const schema = {
      properties: {
        remote: { $ref: 'https://example.com/schema.json#/defs/Thing' },
      },
    } as Record<string, unknown>;

    const result = derefJsonSchema(schema) as Record<string, unknown>;

    __testAugmentVitest_9fc805dc4d94.expect((result.properties as any).remote.$ref).toBe('https://example.com/schema.json#/defs/Thing');
  });
});


import * as __testAugmentVitest_9fc805dc4d94 from "vitest";

const __testAugmentLoadTarget_18b9b2ed0b08 = async () => {
  __testAugmentVitest_9fc805dc4d94.vi.doUnmock("../../src/providers/kimi-schema.js");
  __testAugmentVitest_9fc805dc4d94.vi.resetModules();
  return import("../../src/providers/kimi-schema.js");
};
