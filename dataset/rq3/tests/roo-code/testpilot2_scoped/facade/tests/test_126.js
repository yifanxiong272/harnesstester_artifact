let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper to provide an AbortController-like object (uses native if available)
    function makeController() {
        if (typeof AbortController !== 'undefined') {
            const c = new AbortController();
            return {
                signal: c.signal,
                abort: () => c.abort()
            };
        }
        // simple polyfill for environments without AbortController
        let listeners = [];
        let aborted = false;
        const signal = {
            aborted: false,
            addEventListener: (ev, fn) => {
                if (ev === 'abort') listeners.push(fn);
            },
            removeEventListener: (ev, fn) => {
                if (ev === 'abort') listeners = listeners.filter(f => f !== fn);
            }
        };
        return {
            signal,
            abort: () => {
                if (aborted) return;
                aborted = true;
                signal.aborted = true;
                // call listeners (copy to avoid mutation issues)
                listeners.slice().forEach(fn => {
                    try { fn(); } catch (e) { /* swallow listener errors for test harness */ }
                });
            }
        };
    }

    // obtain a usable reference to addAbortListener, try instance method first then static
    let addAbortListener;
    let MQS = testpilot_subject && testpilot_subject.file_0012 && testpilot_subject.file_0012.MessageQueueService;
    if (!MQS) {
        throw new Error('MessageQueueService not found on testpilot_subject.file_0012');
    }
    // Try to make an instance; if construction fails, treat MQS as the object that may have the method
    let serviceInstance = null;
    if (typeof MQS === 'function') {
        try {
            serviceInstance = new MQS();
        } catch (e) {
            // ignore - maybe it's not constructible / requires args; we'll fallback to static
            serviceInstance = null;
        }
    } else {
        serviceInstance = MQS;
    }

    if (serviceInstance && typeof serviceInstance.addAbortListener === 'function') {
        addAbortListener = serviceInstance.addAbortListener.bind(serviceInstance);
    } else if (typeof MQS.addAbortListener === 'function') {
        addAbortListener = MQS.addAbortListener.bind(MQS);
    } else {
        throw new Error('addAbortListener method not found on MessageQueueService');
    }

    it('invokes listener when signal aborts', function(done) {
        const ctrl = makeController();
        let called = 0;
        addAbortListener(ctrl.signal, () => { called += 1; });

        // abort asynchronously to emulate normal usage
        setImmediate(() => {
            ctrl.abort();
            setImmediate(() => {
                try {
                    assert.strictEqual(called, 1, 'listener should be called exactly once on abort');
                    done();
                } catch (err) {
                    done(err);
                }
            });
        });
    });

    })