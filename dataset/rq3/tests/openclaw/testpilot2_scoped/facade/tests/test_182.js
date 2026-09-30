let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Ensure Mocha has enough time if something goes async internally
    this.timeout(5000);

    const execute = testpilot_subject?.file_0005?.processTool?.execute;

    it('exists and is a function', function() {
        assert.ok(execute, 'execute should be exported');
        assert.strictEqual(typeof execute, 'function');
    });

    })