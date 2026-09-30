import { it, expect } from "vitest"
import { ToolRepetitionDetector } from "../../core/tools/ToolRepetitionDetector"

it("allows first identical call and blocks second when consecutiveIdenticalToolCallLimit=1", () => {
	// Public construction with minimal nonzero limit
	const detector = new ToolRepetitionDetector(1)

	// Deterministic, plain-object ToolUse-like value
	const toolUse = { name: "probe-tool", params: { x: 1 } }

	// First call: should be allowed
	const firstResult = detector.check(toolUse)

	// Second call with an equivalent object (same primitives/structure): should be blocked
	const secondResult = detector.check({ name: "probe-tool", params: { x: 1 } })

	// Single combined assertion (exactly one expect in the file)
	expect(
		firstResult.allowExecution === true &&
		firstResult.askUser === undefined &&
		secondResult.allowExecution === false &&
		typeof secondResult.askUser === "object" &&
		secondResult.askUser?.messageKey === "mistake_limit_reached"
	).toBe(true)
})
