let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const OutputManager = testpilot_subject.file_0002.OutputManager;

    it('removes an existing entry from a Set stored in loggedFirstPartial', function(done) {
        const om = new OutputManager();
        // Ensure we control the loggedFirstPartial structure
        om.loggedFirstPartial = new Set(['a', 'b']);
        const ret = om.clearLoggedFirstPartial('a');

        // method does not return a value (undefined)
        assert.strictEqual(ret, undefined);
        // the 'a' entry should be gone, 'b' should remain
        assert.strictEqual(om.loggedFirstPartial.has('a'), false);
        assert.strictEqual(om.loggedFirstPartial.has('b'), true);
        assert.strictEqual(om.loggedFirstPartial.size, 1);
        done();
    });

    })