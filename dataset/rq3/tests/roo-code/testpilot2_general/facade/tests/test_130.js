let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('should expose OutputManager on testpilot_subject.file_0002', function() {
        assert.ok(testpilot_subject, 'testpilot_subject should be present');
        assert.ok(testpilot_subject.file_0002, 'file_0002 namespace should be present');
        const OM = testpilot_subject.file_0002.OutputManager;
        assert.ok(OM, 'OutputManager should be exported');
        assert.strictEqual(typeof OM, 'function', 'OutputManager should be a constructor function');
    });

    })