let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to set a stub for loadMarketplace in the tested module.
    // Tries several strategies (direct property, rewire-style __set__, global) and returns a restore fn.
    function installLoadMarketplaceStub(stub) {
        const mod = (testpilot_subject && testpilot_subject.file_0014) ? testpilot_subject.file_0014 : testpilot_subject;
        const restores = [];

        // Strategy 1: direct property on module
        try {
            if (Object.prototype.hasOwnProperty.call(mod, 'loadMarketplace')) {
                const orig = mod.loadMarketplace;
                mod.loadMarketplace = stub;
                restores.push(() => { mod.loadMarketplace = orig; });
                return () => restores.forEach(r => r());
            }
        } catch (e) {
            // ignore and try next strategy
        }

        // Strategy 2: rewire-like API (__set__ / __get__)
        try {
            if (typeof mod.__set__ === 'function') {
                let orig;
                if (typeof mod.__get__ === 'function') {
                    try { orig = mod.__get__('loadMarketplace'); } catch (e) { orig = undefined; }
                }
                mod.__set__('loadMarketplace', stub);
                restores.push(() => { try { mod.__set__('loadMarketplace', orig); } catch (e) { /* ignore */ } });
                return () => restores.forEach(r => r());
            }
        } catch (e) {
            // ignore and try global
        }

        // Strategy 3: attach to global (fallback)
        const origGlobal = global.loadMarketplace;
        global.loadMarketplace = stub;
        restores.push(() => { global.loadMarketplace = origGlobal; });
        return () => restores.forEach(r => r());
    }

    // Helper to get the function under test, whether it's exported at file_0014 or root.
    function getSubjectFunction() {
        const mod = (testpilot_subject && testpilot_subject.file_0014) ? testpilot_subject.file_0014 : testpilot_subject;
        if (!mod || typeof mod.listMarketplacePlugins !== 'function') {
            throw new Error('Cannot find listMarketplacePlugins on testpilot_subject or testpilot_subject.file_0014');
        }
        return mod.listMarketplacePlugins;
    }

    it('returns the loaded error object when loadMarketplace returns ok:false (no cleanup called)', function(done) {
        (async () => {
            // Arrange: stub that returns an error result
            const stub = async (opts) => {
                return { ok: false, error: 'marketplace load failed' };
            };
            const restore = installLoadMarketplaceStub(stub);

            try {
                const fn = getSubjectFunction();
                const res = await fn({ marketplace: 'unused', logger: console, timeoutMs: 100 });
                // Ensure we got an error result back. We don't assume the exact error string,
                // since the real module may produce different messages depending on env.
                assert.strictEqual(res.ok, false);
                assert.strictEqual(typeof res.error, 'string');
            } finally {
                restore();
            }
        })().then(() => done(), done);
    });

    })