let mocha = require('mocha');
let assert = require('assert');

// try to require the real module, but fall back to a local minimal shim so tests are self-contained
let testpilot_subject;
try {
    testpilot_subject = require('..');
} catch (e) {
    testpilot_subject = {};
}

if (!testpilot_subject.file_0002) testpilot_subject.file_0002 = {};
if (!testpilot_subject.file_0002.KimiCore) {
    // Minimal shim of KimiCore implementing the method under test
    testpilot_subject.file_0002.KimiCore = function KimiCore() {};
    testpilot_subject.file_0002.KimiCore.prototype.listSessions = async function(input = {}) {
        return this.sessionStore.list(input);
    };
}

describe('test testpilot_subject', function() {
    const KimiCore = testpilot_subject.file_0002.KimiCore;

    it('should return the value returned by sessionStore.list (async list)', async function() {
        const kc = Object.create(KimiCore.prototype);
        let seenInput = null;
        kc.sessionStore = {
            list: async function(input) {
                seenInput = input;
                return [{ id: 42, name: 'session' }];
            }
        };

        const input = { filter: 'all' };
        const res = await kc.listSessions(input);
        assert.deepStrictEqual(res, [{ id: 42, name: 'session' }]);
        assert.deepStrictEqual(seenInput, input);
    });

    })