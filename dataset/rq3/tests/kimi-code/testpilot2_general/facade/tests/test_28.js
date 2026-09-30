let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Grab the grep function from the prototype so we can call it with a fake "this"
    const grepFn = testpilot_subject.file_0002.FsSearchService.prototype.grep;

    // Helper to create and cleanup a temp directory for tests
    function makeTempDir(prefix = 'fps-test-') {
        const d = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
        return d;
    }
    function removeTempDir(d) {
        // best-effort cleanup
        try {
            fs.rmSync(d, { recursive: true, force: true });
        } catch (e) {
            try { fs.rmdirSync(d, { recursive: true }); } catch (_) {}
        }
    }

    it('uses grepWithRg when probeRg returns non-null and passes expected args', async function() {
        const tmpDir = makeTempDir();
        try {
            const expectedReal = await fs.promises.realpath(tmpDir);
            let probeRgCalled = false;
            let grepWithRgCalled = false;

            const fakeThis = {
                sessions: {
                    get: async (id) => {
                        assert.strictEqual(id, 'session-rg');
                        return { metadata: { cwd: tmpDir } };
                    }
                },
                probeRg: async () => {
                    probeRgCalled = true;
                    return { name: 'fake-rg' }; // non-null -> grepWithRg path
                },
                // this implementation will assert the signature and return a sentinel result
                grepWithRg: async (rg, realCwd, req, signal, startedAt) => {
                    grepWithRgCalled = true;
                    // basic checks
                    assert.deepStrictEqual(rg, { name: 'fake-rg' });
                    assert.strictEqual(realCwd, expectedReal);
                    assert.deepStrictEqual(req, { pattern: 'hello' });
                    assert.ok(typeof startedAt === 'number' && startedAt > 0);
                    // should receive an AbortSignal-like object
                    assert.ok(signal && typeof signal.aborted === 'boolean');
                    return { via: 'rg', found: [] };
                },
                // should not be called in this test
                grepWithNode: async () => {
                    throw new Error('grepWithNode should not be called when probeRg returns non-null');
                }
            };

            const res = await grepFn.call(fakeThis, 'session-rg', { pattern: 'hello' });
            assert.deepStrictEqual(res, { via: 'rg', found: [] });
            assert.ok(probeRgCalled, 'probeRg was not called');
            assert.ok(grepWithRgCalled, 'grepWithRg was not called');
        } finally {
            removeTempDir(tmpDir);
        }
    });

    })