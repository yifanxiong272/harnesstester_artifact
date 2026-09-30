let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // allow a little extra time for async operations in slower CI environments
    this.timeout(5000);

    const fnPath = 'file_0013.ensureSandboxContainer';

    it('exports the function testpilot_subject.file_0013.ensureSandboxContainer', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject should be present');
        assert.ok(testpilot_subject.file_0013, 'testpilot_subject.file_0013 should be present');
        const fn = testpilot_subject.file_0013 && testpilot_subject.file_0013.ensureSandboxContainer;
        assert.ok(fn, `${fnPath} should be exported`);
        assert.strictEqual(typeof fn, 'function', `${fnPath} should be a function`);
        // If the implementation is declared as async function, its constructor name is "AsyncFunction"
        // but not all environments expose that reliably; just check it's a function above.
    });

    // Helper: ensure promise settles within timeout (either resolves or rejects)
    function settlesWithin(promise, ms) {
        return new Promise((resolve, reject) => {
            let settled = false;
            const to = setTimeout(() => {
                if (!settled) {
                    settled = true;
                    reject(new Error('Timed out waiting for promise to settle'));
                }
            }, ms);
            Promise.resolve(promise).then(
                (v) => {
                    if (!settled) {
                        settled = true;
                        clearTimeout(to);
                        resolve({ settled: true, status: 'resolved', value: v });
                    }
                },
                (err) => {
                    if (!settled) {
                        settled = true;
                        clearTimeout(to);
                        resolve({ settled: true, status: 'rejected', reason: err });
                    }
                }
            );
        });
    }

    })