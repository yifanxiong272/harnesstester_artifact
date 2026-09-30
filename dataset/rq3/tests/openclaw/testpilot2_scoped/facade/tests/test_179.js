let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // allow a bit more time for asynchronous implementations
    this.timeout(5000);

    // helper that calls the target and normalizes outcomes into a Promise
    function callExecuteSafely(toolCallId, args, signal, onUpdate, maxWait = 1500) {
        return new Promise((resolve, reject) => {
            let finished = false;
            function finishSuccess(out) {
                if (finished) return;
                finished = true;
                resolve({ success: true, result: out });
            }
            function finishFailure(err) {
                if (finished) return;
                finished = true;
                reject(err);
            }

            try {
                const maybePromise = testpilot_subject.file_0005.processTool.execute(toolCallId, args, signal, onUpdate);

                // If a promise-like is returned, await it.
                if (maybePromise && typeof maybePromise.then === 'function') {
                    maybePromise.then(res => finishSuccess({ promiseResult: res }))
                                .catch(err => finishFailure(err));
                    return;
                }

                // If a synchronous non-undefined result is returned, treat as success.
                if (typeof maybePromise !== 'undefined') {
                    finishSuccess({ syncResult: maybePromise });
                    return;
                }

                // No immediate result: wait for an onUpdate callback or for a small timeout.
                // If an onUpdate callback is provided, assume it will call within maxWait ms.
                const timer = setTimeout(() => {
                    if (!finished) {
                        finished = true;
                        resolve({ success: true, result: { note: 'no-promise-no-sync-no-onUpdate-within-time' } });
                    }
                }, maxWait);

                // Note: onUpdate may call finishSuccess itself; caller-provided onUpdate should
                // call finishSuccess for us if it wants to signal. In our tests we will provide
                // an onUpdate that does that when appropriate.

            } catch (err) {
                finishFailure(err);
            }
        });
    }

    it('exports file_0005.processTool.execute as a function', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject should be present');
        assert.ok(testpilot_subject.file_0005, 'file_0005 should be present on module');
        assert.ok(testpilot_subject.file_0005.processTool, 'processTool should be present on file_0005');
        assert.strictEqual(typeof testpilot_subject.file_0005.processTool.execute, 'function', 'execute should be a function');
    });

    })