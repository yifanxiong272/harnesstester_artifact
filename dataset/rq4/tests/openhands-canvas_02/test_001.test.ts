import { test, expect } from 'vitest';
import { withBackendSelectionParams } from "../../../src/api/backend-registry/url-selection";

test("withBackendSelectionParams preserves URL fragment and places query before it", () => {
  const pathNoQuery = "/p#frag";
  const pathWithQuery = "/p?x=1#frag";

  const activeNoOrg = { backend: { id: "B" } } as any;
  const activeWithOrg = { backend: { id: "B" }, orgId: "O" } as any;

  const out1 = withBackendSelectionParams(pathNoQuery, activeNoOrg);
  const out2 = withBackendSelectionParams(pathWithQuery, activeWithOrg);

  const expected1 = "/p?backend=B#frag";
  const expected2 = "/p?x=1&backend=B&org=O#frag";

  expect(out1 === expected1 && out2 === expected2).toBe(true);
});
