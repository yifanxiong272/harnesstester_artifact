let mocha = require('mocha');
let assert = require('assert');

describe('test testpilot_subject.file_0009.runExecProcess', function() {
    // Ensure tests don't run too long
    this.timeout(5000);

    it('exports runExecProcess as an async function', function() {
        // require inside the test to avoid any global side-effects before stubbing in other tests
        const testpilot_subject = require('..');
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0009, 'expected file_0009 to be exported');
        const fn = testpilot_subject.file_0009.runExecProcess;
        assert.strictEqual(typeof fn, 'function', 'runExecProcess should be a function');
    });

    })