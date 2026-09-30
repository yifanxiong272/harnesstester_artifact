let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0002.KimiCore.prototype.createSession - forwards input and uses empty overrides', async function() {
        const KimiCore = testpilot_subject.file_0002.KimiCore;
        const createSession = KimiCore.prototype.createSession;

        let callCount = 0;
        let lastArgs = null;
        const fakeThis = {
            // mimic an async implementation that echoes what it received
            async createSessionWithOverrides(input, overrides) {
                callCount++;
                lastArgs = [input, overrides];
                // return something that includes what was passed so we can assert
                return { ok: true, inputReceived: input, overridesReceived: overrides };
            }
        };

        const input = { cwd: '/some/dir', meta: { test: true } };
        const result = await createSession.call(fakeThis, input);

        // ensure the proxy method was called exactly once
        assert.strictEqual(callCount, 1, 'createSessionWithOverrides should be called once');

        // ensure the input was forwarded intact (same reference for objects)
        assert.strictEqual(lastArgs[0], input, 'input argument should be forwarded unchanged');
        assert.strictEqual(result.inputReceived, input, 'returned value should reflect forwarded input');

        // ensure overrides object is provided and is empty (no keys)
        const overridesArg = lastArgs[1];
        assert.strictEqual(typeof overridesArg, 'object', 'overrides should be an object');
        assert.deepStrictEqual(Object.keys(overridesArg), [], 'overrides should be an empty object');
        assert.deepStrictEqual(result.overridesReceived, overridesArg, 'returned overrides should match the one passed in');
    });

    })