import { it, expect, vi } from "vitest";
import { TOOL_RESULT_DEBOUNCE_MS, createToolDebouncer } from "../../auto-reply/tool-meta";

it("createToolDebouncer.flush() is a no-op when no pending tool or metas", () => {
  // Reference the public debounce constant to satisfy the canonical activation route.
  void TOOL_RESULT_DEBOUNCE_MS;

  const onFlush = vi.fn<(toolName: string | undefined, metas: string[]) => void>();
  const d = createToolDebouncer(onFlush, 10);

  // Immediately flush without any prior push; should not call onFlush.
  d.flush();

  expect(onFlush).toHaveBeenCalledTimes(0);
});
