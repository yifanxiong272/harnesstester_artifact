import { it, expect } from 'vitest';
import { parseGitRemoteUrl } from '../../../src/utils/parse-git-remote-url';

it('normalizes URL- and scp-style remotes to the same host and owner/repo path', () => {
  const inputs = [
    'git@github.com:owner/repo.git',
    '  https://github.com/owner/repo.git  ',
    'git://github.com/owner/repo.git/',
    'https://github.com//owner/repo.git',
  ];

  const parsed = inputs.map((s) => parseGitRemoteUrl(s));

  const actualProjected = parsed.map((p) =>
    p == null
      ? null
      : { url: p.url, host: p.host, path: (p as any).path }
  );

  const expectedProjected = inputs.map((s) => ({
    url: s.trim(),
    host: 'github.com',
    path: 'owner/repo',
  }));

  expect(actualProjected).toEqual(expectedProjected);
});
