let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // keep tests fast
    this.timeout(5000);

    const runExecProcess = testpilot_subject?.file_0008?.runExecProcess;

    it('runExecProcess should be exported and be a function', function() {
        assert.ok(runExecProcess, 'runExecProcess is not exported');
        assert.strictEqual(typeof runExecProcess, 'function');
    });

    })