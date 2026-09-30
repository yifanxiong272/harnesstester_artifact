let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const applyPatch = testpilot_subject?.file_0008?.applyPatch;

    it('exports applyPatch as a function', function() {
        assert.ok(applyPatch, 'applyPatch should be exported');
        assert.strictEqual(typeof applyPatch, 'function');
    });

    })