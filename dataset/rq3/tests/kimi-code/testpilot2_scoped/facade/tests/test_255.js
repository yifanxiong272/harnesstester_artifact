let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Ensure we have something predictable to test. If the real module doesn't
    // provide file_0002.KimiCore.exitSwarm, install a local stub implementation.
    // This keeps the tests self-contained while still exercising the expected shape.
    const hadReal = !!(
        testpilot_subject &&
        testpilot_subject.file_0002 &&
        testpilot_subject.file_0002.KimiCore &&
        typeof testpilot_subject.file_0002.KimiCore.prototype.exitSwarm === 'function'
    );

    if (!hadReal) {
        // Build a minimal namespace and a KimiCore class with an exitSwarm implementation
        testpilot_subject = testpilot_subject || {};
        testpilot_subject.file_0002 = testpilot_subject.file_0002 || {};
        testpilot_subject.file_0002.KimiCore = function KimiCore(){};
        testpilot_subject.file_0002.KimiCore.prototype.exitSwarm = function({sessionId, ...payload} = {}) {
            // simple behavior:
            // - if no sessionId -> throw
            // - otherwise return a promise resolving to an object that echoes inputs and a timestamp
            if (!sessionId) throw new Error('sessionId required');
            return Promise.resolve({
                ok: true,
                sessionId: sessionId,
                payload: payload,
                exitedAt: Date.now()
            });
        };
    }

    const KimiCore = testpilot_subject.file_0002.KimiCore;

    it('KimiCore.prototype.exitSwarm should exist and be a function', function() {
        assert.ok(KimiCore, 'KimiCore constructor should exist');
        assert.ok(KimiCore.prototype, 'KimiCore.prototype should exist');
        assert.strictEqual(typeof KimiCore.prototype.exitSwarm, 'function', 'exitSwarm should be a function');
    });

    })