let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout in case the implementation does small async work
    this.timeout(2000);

    it('does not throw or reject when shell is not provided (accepts null)', async function() {
        // The function is async; ensure it does not reject or throw when shell is null.
        let threw = false;
        try {
            // call with null shell - implementation currently accepts null
            await testpilot_subject.file_0015.usesSlowDynamicCompletion(null);
        } catch (e) {
            threw = true;
        }
        assert.strictEqual(threw, false, 'expected function not to throw or reject when shell is null');
    });

    })