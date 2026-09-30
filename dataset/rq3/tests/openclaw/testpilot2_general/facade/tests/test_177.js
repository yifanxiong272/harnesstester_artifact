let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    this.timeout(5000);

    it('should expose file_0005.processTool.execute as a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0005, 'file_0005 should exist on module');
        assert.strictEqual(typeof testpilot_subject.file_0005.processTool.execute, 'function');
    });

    })