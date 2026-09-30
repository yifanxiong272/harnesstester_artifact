let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('should expose ToolCallComponent constructor', function(done) {
        assert.ok(testpilot_subject, 'module testpilot_subject is present');
        assert.ok(testpilot_subject.file_0003, 'module.file_0003 is present');
        assert.strictEqual(typeof testpilot_subject.file_0003.ToolCallComponent, 'function',
            'ToolCallComponent should be a constructor function');
        done();
    });

    })