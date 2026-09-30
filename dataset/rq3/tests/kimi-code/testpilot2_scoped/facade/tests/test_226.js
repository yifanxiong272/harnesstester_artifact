let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to call setPermission and normalize sync / promise results.
    async function callAndEnsureResolved(kimiCoreInstance, payload) {
        let result;
        try {
            result = kimiCoreInstance.setPermission(payload);
        } catch (err) {
            // synchronous throw -> fail the test by rethrowing
            throw err;
        }
        // If returned a promise, await it (will throw if rejected).
        if (result && typeof result.then === 'function') {
            return await result;
        }
        // Otherwise return the synchronous result
        return result;
    }

    it('KimiCore has a setPermission function', function() {
        const KimiCore = testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore constructor should exist');

        // Provide a stub rpcClient function so the constructor won't throw "rpcClient is not a function".
        // The stub returns a Proxy that yields no-op functions for any accessed property, making it safe
        // even if the constructor immediately calls methods on the returned object.
        const noop = () => {};
        const rpcClientStub = () => new Proxy({}, { get: () => noop });

        const instance = new KimiCore(rpcClientStub);
        assert.strictEqual(typeof instance.setPermission, 'function', 'setPermission should be a function');
    });

    })