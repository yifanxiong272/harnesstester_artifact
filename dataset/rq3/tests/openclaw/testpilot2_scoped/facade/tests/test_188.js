let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Allow a little extra time for async operations in CI environments
    this.timeout(2000);

    // Helper that normalizes both sync throws and promise-based results into a Promise
    function invokeFetch(params) {
        try {
            const result = testpilot_subject.file_0006.fetchFirecrawlContent(params);
            // If it looks like a Promise, convert to a Promise that resolves with an object describing the outcome
            if (result && typeof result.then === 'function') {
                return result.then(
                    value => ({ outcome: 'resolved', value }),
                    err => ({ outcome: 'rejected', value: err })
                );
            }
            // Synchronous return
            return Promise.resolve({ outcome: 'sync', value: result });
        } catch (err) {
            // Synchronous throw
            return Promise.resolve({ outcome: 'threw', value: err });
        }
    }

    it('exports fetchFirecrawlContent as a function', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject should be present');
        assert.ok(testpilot_subject.file_0006, 'file_0006 should be present on testpilot_subject');
        assert.strictEqual(typeof testpilot_subject.file_0006.fetchFirecrawlContent, 'function',
            'fetchFirecrawlContent should be a function');
    });

    })