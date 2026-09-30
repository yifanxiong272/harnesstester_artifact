let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports file_0005.createProcessTool as a function', function(done) {
        assert.ok(testpilot_subject, 'module should be present');
        assert.ok(testpilot_subject.file_0005, 'file_0005 should be present on module');
        assert.strictEqual(typeof testpilot_subject.file_0005.createProcessTool, 'function',
            'createProcessTool should be a function');
        done();
    });

    })