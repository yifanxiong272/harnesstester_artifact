import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { describe, expect, it } from "vitest";
import {
  ACPX_BUNDLED_BIN,
  ACPX_PINNED_VERSION,
  createAcpxPluginConfigSchema,
  resolveAcpxPluginRoot,
  resolveAcpxPluginConfig,
} from "./config.js";

describe("acpx plugin config parsing", () => {













  __testAugmentVitest_78fbbb17e8c5.it("decodes_html_entities_in_object_round_001_pass_02", async () => {
    const { decodeHtmlEntitiesInObject } = await __testAugmentLoadTarget_22dd75644b97();

    const input = {
      title: "Tom &amp; Jerry &lt;Best&gt;",
      nested: {
        desc: "Fish &amp; Chips &gt; Salad",
        list: ["A &lt; B", "C &amp; D"],
      },
    };

    const out = decodeHtmlEntitiesInObject(input);

    __testAugmentVitest_78fbbb17e8c5.expect(out.title).toBe("Tom & Jerry <Best>");
    __testAugmentVitest_78fbbb17e8c5.expect(out.nested.desc).toBe("Fish & Chips > Salad");
    __testAugmentVitest_78fbbb17e8c5.expect(out.nested.list[0]).toBe("A < B");
    __testAugmentVitest_78fbbb17e8c5.expect(out.nested.list[1]).toBe("C & D");
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_22dd75644b97 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-runner/run/attempt.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-runner/run/attempt.js");
};
