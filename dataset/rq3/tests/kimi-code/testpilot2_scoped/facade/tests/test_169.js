let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create a proxy 'this' so the tested method can freely get/set arbitrary properties.
    // We pre-populate some likely property names that a removeKimiProvider implementation might use.
    function createProxyWithProviders() {
        const storage = new Map();

        // Pre-populate a few plausible provider-holding properties so the implementation
        // will find at least one that's meaningful to act on.
        storage.set('providers', [{ id: 'p1' }, { id: 'p2' }]);
        storage.set('kimiProviders', [{ id: 'pA' }, { id: 'p1' }]);
        storage.set('_providers', [{ name: 'pX' }, { name: 'pY' }]);

        const handler = {
            get(target, prop) {
                // Allow access to a helper to inspect internal storage from tests.
                if (prop === '_getInternalStorage') return () => storage;
                // Return anything already stored, otherwise initialize a default array.
                if (storage.has(prop)) return storage.get(prop);
                const defaultVal = [];
                storage.set(prop, defaultVal);
                return defaultVal;
            },
            set(target, prop, value) {
                storage.set(prop, value);
                return true;
            },
            has(target, prop) {
                return storage.has(prop);
            },
            ownKeys() {
                return Array.from(storage.keys());
            },
            getOwnPropertyDescriptor() {
                return { enumerable: true, configurable: true };
            }
        };

        return new Proxy({}, handler);
    }

    it('should export removeKimiProvider as a function and return a Promise when called', function() {
        const KimiCore = testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore constructor should exist');
        const fn = KimiCore.prototype.removeKimiProvider;
        assert.strictEqual(typeof fn, 'function', 'removeKimiProvider should be a function');

        const proxyThis = createProxyWithProviders();

        // Call the function and ensure a Promise-like is returned (async function or returns thenable)
        const result = fn.call(proxyThis, 'some-id');
        assert.ok(result && typeof result.then === 'function', 'removeKimiProvider should return a Promise/thenable');
        // We don't await resolution here; this test only checks immediate return value type.
    });

    })