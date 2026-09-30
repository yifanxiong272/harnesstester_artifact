let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('returns listeners for a DOM-style EventTarget (addEventListener/removeEventListener)', function(done) {
        // Create a simple DOM-like EventTarget mock that is a real EventTarget instance
        function makeDomLikeTarget() {
            // store listeners so tests can introspect them
            const listeners = Object.create(null);

            // Use the global EventTarget if available. Subclass it so instanceof checks pass.
            class MyTarget extends EventTarget {
                addEventListener(type, listener, options) {
                    if (!listeners[type]) listeners[type] = [];
                    listeners[type].push(listener);
                    // call the real EventTarget behavior as well
                    super.addEventListener(type, listener, options);
                }
                removeEventListener(type, listener, options) {
                    if (!listeners[type]) return;
                    const idx = listeners[type].indexOf(listener);
                    if (idx !== -1) listeners[type].splice(idx, 1);
                    super.removeEventListener(type, listener, options);
                }
                // expose for potential introspection by getEventListeners impls
                get __listenersForTest() { return listeners; }
            }

            return new MyTarget();
        }

        const target = makeDomLikeTarget();

        function l1() {}
        function l2() {}

        target.addEventListener('ping', l1);
        target.addEventListener('ping', l2);

        const res = testpilot_subject.file_0012.MessageQueueService.getEventListeners(target, 'ping');

        // Expect an array containing the listeners we added
        assert.ok(Array.isArray(res), 'result should be an array');
        assert.strictEqual(res.length, 2, 'should have two listeners for "ping"');
        assert.ok(res.indexOf(l1) !== -1, 'should contain l1');
        assert.ok(res.indexOf(l2) !== -1, 'should contain l2');

        done();
    });

});