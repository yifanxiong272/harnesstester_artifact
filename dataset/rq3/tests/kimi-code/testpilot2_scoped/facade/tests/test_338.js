let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Grab the prototype function so we don't need to instantiate the real class (which may have side effects).
    const addAdditionalDirFn = testpilot_subject && testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore
        ? testpilot_subject.file_0002.KimiCore.prototype.addAdditionalDir
        : null;

    it('forwards sessionId, path and persist and returns the underlying result', function() {
        if (!addAdditionalDirFn) this.skip();

        let seen = { called: false };
        const ctx = {
            requireSession(sessionId) {
                assert.strictEqual(sessionId, 'session-123');
                return {
                    addAdditionalDir(path, persist) {
                        seen.called = true;
                        assert.strictEqual(path, '/some/path');
                        assert.strictEqual(persist, true);
                        return { ok: true, path, persist };
                    }
                };
            }
        };

        const result = addAdditionalDirFn.call(ctx, { sessionId: 'session-123', path: '/some/path', persist: true });
        assert.strictEqual(seen.called, true);
        assert.deepStrictEqual(result, { ok: true, path: '/some/path', persist: true });
    });

    })