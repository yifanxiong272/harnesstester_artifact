import { it, expect } from 'vitest';
import { resolveExecApprovalCommandDisplay } from '../../infra/exec-approval-command-display';

it('falls back to request.command when host is node and systemRunPlan.commandText is missing', () => {
  const request = {
    host: 'node',
    command: 'fallback-cmd',
    // systemRunPlan is present but intentionally missing commandText
    systemRunPlan: {
      commandPreview: 'preview',
    },
  } as any;

  const result = resolveExecApprovalCommandDisplay(request);

  // Single assertion: commandText must be a non-empty string equal to request.command
  expect(
    typeof result.commandText === 'string' &&
      result.commandText === request.command &&
      result.commandText.length > 0,
  ).toBe(true);
});
