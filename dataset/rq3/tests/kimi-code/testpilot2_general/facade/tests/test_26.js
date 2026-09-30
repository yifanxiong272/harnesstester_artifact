let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0002.FsSearchService.prototype.search', function() {
  // create a temporary directory to be used as session cwd (realpath will work)
  let tmpDir;
  before(function() {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'fsp-search-test-'));
  });
  after(function() {
    // best-effort cleanup
    try { fs.rmdirSync(tmpDir); } catch (e) {}
  });

  // helper to create service with controlled environment
  function makeServiceWithEntries(entries) {
    // entries: [{relPath, name, kind}]
    const Service = testpilot_subject.file_0002.FsSearchService;
    const mod = testpilot_subject.file_0002;

    // Monkeypatch scoring/matching helpers in the module under test so tests are deterministic.
    // computeFuzzyScore: starts-with gets higher score, contains gets lower positive score, else 0
    mod.computeFuzzyScore = function(name, queryLower) {
      if (!queryLower) return 1;
      const n = String(name).toLowerCase();
      if (n.startsWith(queryLower)) return 10;
      if (n.includes(queryLower)) return 5;
      return 0;
    };
    // computeMatchPositions: return a trivial array to ensure property exists
    mod.computeMatchPositions = function(relPath, queryLower) {
      // for testing the contents are not important
      return [];
    };
    // matchesAnyGlob: simple substring-based glob matcher for tests
    mod.matchesAnyGlob = function(relPath, globs) {
      if (!globs || !globs.length) return false;
      return globs.some(g => relPath.indexOf(g) !== -1);
    };
    // cap for tests
    mod.SEARCH_HARD_CAP = 1000;

    const svc = new Service();

    // sessions.get should return metadata with cwd pointing to tmpDir
    svc.sessions = {
      get: async function(sessionId) {
        return { metadata: { cwd: tmpDir } };
      }
    };

    // stub matcher (not used by our walk but provided)
    svc.matcher = async function(realCwd) {
      return function() { return true; };
    };

    // replace walk to call the callback for our fake entries
    svc.walk = async function(realCwd, empty, matcher, cb) {
      for (let e of entries) {
        // cb signature: async(relPath,name,kind)
        await cb(e.relPath, e.name, e.kind);
      }
    };

    return { svc, mod };
  }

  it('returns matching items and includes expected fields, sorted by score then path', async function() {
    const entries = [
      { relPath: 'a.txt', name: 'a.txt', kind: 'file' },
      { relPath: 'sub/b.txt', name: 'b.txt', kind: 'file' },
      { relPath: 'sub/a2.txt', name: 'a2.txt', kind: 'file' },
      { relPath: 'z.txt', name: 'z.txt', kind: 'file' }
    ];
    const { svc } = makeServiceWithEntries(entries);

    const req = {
      query: 'a',
      follow_gitignore: false,
      include_globs: null,
      exclude_globs: null,
      limit: 10
    };

    const res = await svc.search('sess1', req);
    // Expect items with 'a' in name: a.txt and a2.txt
    const names = res.items.map(i => i.name);
    assert.deepStrictEqual(names, ['a.txt', 'a2.txt'], 'Expected only a.txt and a2.txt in that order');

    // Each item should have required fields
    for (let item of res.items) {
      assert.ok(typeof item.path === 'string');
      assert.ok(typeof item.name === 'string');
      assert.ok(typeof item.kind === 'string');
      assert.ok(typeof item.score === 'number' && item.score > 0);
      assert.ok(Array.isArray(item.match_positions));
    }

    assert.strictEqual(res.truncated, false);
  });

  })