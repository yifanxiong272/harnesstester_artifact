import { it, expect } from 'vitest'
import { ToolRepetitionDetector } from '../../core/tools/ToolRepetitionDetector'

it('limit=1 allows first identical call then blocks the second with askUser payload', () => {
	const detector = new ToolRepetitionDetector(1)
	const toolUse = { name: 't', params: { p: 'v' } }
	const first = detector.check(toolUse as any)
	const second = detector.check(toolUse as any)
	expect({
		firstAllow: first.allowExecution,
		firstAskUserMissing: first.askUser === undefined,
		secondAllow: second.allowExecution,
		secondAskKey: second.askUser?.messageKey,
		secondAskDetailContainsName: typeof second.askUser?.messageDetail === 'string' && second.askUser!.messageDetail.includes('t'),
	}).toEqual({
		firstAllow: true,
		firstAskUserMissing: true,
		secondAllow: false,
		secondAskKey: 'mistake_limit_reached',
		secondAskDetailContainsName: true,
	})
})
