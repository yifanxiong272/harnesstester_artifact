import { test, expect } from 'vitest';
import { resolveExecApprovalCommandDisplay } from '../../infra/exec-approval-command-display';

test('when host is node and systemRunPlan exists without commandText, fallback to request.command and return valid types', () => {
  const request = {
    host: 'node',
    command: 'fallback-command --do-thing',
    commandPreview: null,
    systemRunPlan: { unrelatedKey: 'present' },
  } as any;

  const result = resolveExecApprovalCommandDisplay(request);

  expect(
    typeof result.commandText === 'string' &&
      result.commandText === request.command &&
      result.commandText.length > 0 &&
      (typeof result.commandPreview === 'string' || result.commandPreview === null)
  ).toBe(true);
});
