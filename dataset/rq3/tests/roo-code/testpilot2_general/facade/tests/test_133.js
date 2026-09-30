let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0002.OutputManager.prototype.hasLoggedFirstPartial', function() {
    const OutputManager = testpilot_subject.file_0002.OutputManager;

    it('returns false when the timestamp is not present in loggedFirstPartial (empty Set)', function() {
        // create an object that uses the prototype method without calling constructor
        let obj = Object.create(OutputManager.prototype);
        obj.loggedFirstPartial = new Set();

        assert.strictEqual(obj.hasLoggedFirstPartial('ts1'), false);
        assert.strictEqual(obj.hasLoggedFirstPartial(123), false);
    });

    })