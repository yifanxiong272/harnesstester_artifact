import { test, expect } from 'vitest';
import { extractShellCommandFromArgv } from '../../infra/system-run-command';

test('extractShellCommandFromArgv treats whitespace-only sh -c argv[2] as absent', () => {
  const argv = ['/bin/sh', '-c', '   '];
  const res = extractShellCommandFromArgv(argv);
  expect(res).toBe(null);
});
