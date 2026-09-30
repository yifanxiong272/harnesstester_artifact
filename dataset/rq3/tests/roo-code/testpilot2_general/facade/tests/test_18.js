let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to try deep equality for several likely property names where credentials may be stored
    function findCredentialProperty(obj) {
        const candidates = [
            'credentials', '_credentials', 'creds', '_creds',
            'oauthCredentials', '_oauthCredentials', 'auth', '_auth', 'token', '_token'
        ];
        for (const name of candidates) {
            if (Object.prototype.hasOwnProperty.call(obj, name)) return name;
            // also check nested prototype chain
            if (name in obj) return name;
        }
        // fallback: try to find any property that looks like it contains token-like keys
        for (const key of Object.keys(obj)) {
            const val = obj[key];
            if (val && typeof val === 'object' &&
                (('access_token' in val) || ('refresh_token' in val) || ('token' in val))) {
                return key;
            }
        }
        return null;
    }

    // Helper to stub potential side-effect methods on the instance so tests don't touch external resources.
    function stubOutIO(manager) {
        const proto = Object.getPrototypeOf(manager) || {};
        const names = new Set([
            ...Object.getOwnPropertyNames(manager),
            ...Object.getOwnPropertyNames(proto)
        ]);
        const stubs = [];
        // match method names that likely perform IO or persistence
        const ioRegex = /(write|save|store|persist|set|put|upload|fs|file|writeFile|saveTo|persistTo)/i;
        names.forEach(name => {
            try {
                const val = manager[name];
                if (typeof val === 'function' && name !== 'saveCredentials' && ioRegex.test(name)) {
                    const original = val;
                    const record = { name, original, calls: [] };
                    manager[name] = function() {
                        record.calls.push(Array.from(arguments));
                        // if original expected a callback style, try to detect and call it with success
                        const last = arguments[arguments.length - 1];
                        if (typeof last === 'function') {
                            // call callback with no error
                            last(null, {});
                            return;
                        }
                        // return a resolved promise to satisfy async code paths
                        return Promise.resolve({});
                    };
                    stubs.push(record);
                }
            } catch (e) {
                // ignore properties that throw on access
            }
        });
        return stubs;
    }

    // Restore stubs
    function restoreStubs(manager, stubs) {
        for (const s of stubs) {
            try { manager[s.name] = s.original; } catch (e) { /* ignore */ }
        }
    }

    it('saveCredentials should exist and be a function', function() {
        assert.ok(testpilot_subject, 'testpilot_subject should be present');
        assert.ok(testpilot_subject.file_0001, 'file_0001 should be present');
        const ctor = testpilot_subject.file_0001.OpenAiCodexOAuthManager;
        assert.ok(typeof ctor === 'function', 'OpenAiCodexOAuthManager constructor should exist');
        assert.ok(typeof ctor.prototype.saveCredentials === 'function', 'saveCredentials should be a function on the prototype');
    });

    })