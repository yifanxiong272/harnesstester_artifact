let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const KimiCore = testpilot_subject.file_0002.KimiCore;

    // Helper to create an instance without running the real constructor
    function createBareInstance() {
        const inst = Object.create(KimiCore.prototype);
        // set defaults that many methods expect to exist
        inst.sessions = new Map();
        return inst;
    }

    it('getCoreInfo returns an object with a version string', function() {
        const inst = createBareInstance();
        const info = inst.getCoreInfo();
        assert.strictEqual(typeof info, 'object');
        assert.strictEqual(typeof info.version, 'string');
        assert.ok(info.version.length > 0, 'version should be a non-empty string');
    });

    })