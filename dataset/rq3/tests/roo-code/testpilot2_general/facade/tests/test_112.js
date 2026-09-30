let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0002.OutputManager.prototype.isCurrentlyStreaming - method exists and returns a boolean', function() {
        const OM = testpilot_subject.file_0002.OutputManager;
        assert.ok(typeof OM === 'function', 'OutputManager constructor should exist');

        const om = new OM();
        assert.ok(typeof om.isCurrentlyStreaming === 'function', 'isCurrentlyStreaming should be a function');

        const res = om.isCurrentlyStreaming();
        assert.strictEqual(typeof res, 'boolean', 'isCurrentlyStreaming() should return a boolean');
    });

    })