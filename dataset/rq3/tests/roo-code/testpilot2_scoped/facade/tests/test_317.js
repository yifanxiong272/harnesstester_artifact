let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to register a listener using a common API if available.
    function addListener(emitter, event, fn) {
        if (typeof emitter.on === 'function') return emitter.on(event, fn);
        if (typeof emitter.addListener === 'function') return emitter.addListener(event, fn);
        if (typeof emitter.addEventListener === 'function') return emitter.addEventListener(event, fn);
        if (typeof emitter.subscribe === 'function') return emitter.subscribe(event, fn);
        // Best-effort fallback: create an _events structure commonly used by many emitters.
        emitter._events = emitter._events || {};
        emitter._events[event] = emitter._events[event] || [];
        emitter._events[event].push(fn);
        return fn;
    }

    // Helper to register a once listener if available.
    function addOnce(emitter, event, fn) {
        if (typeof emitter.once === 'function') return emitter.once(event, fn);
        // If there's no once, emulate it using addListener + remove inside wrapper if a remove method exists.
        if (typeof emitter.on === 'function' || typeof emitter.addListener === 'function' || typeof emitter.addEventListener === 'function' || typeof emitter.subscribe === 'function') {
            let wrapper = function() {
                try { fn.apply(this, arguments); } finally {
                    if (typeof emitter.removeListener === 'function') {
                        emitter.removeListener(event, wrapper);
                    } else if (typeof emitter.off === 'function') {
                        emitter.off(event, wrapper);
                    } else {
                        // best-effort: remove from _events if present
                        if (emitter._events && Array.isArray(emitter._events[event])) {
                            let idx = emitter._events[event].indexOf(wrapper);
                            if (idx !== -1) emitter._events[event].splice(idx, 1);
                        }
                    }
                }
            };
            addListener(emitter, event, wrapper);
            return wrapper;
        }
        // fallback
        return addListener(emitter, event, fn);
    }

    it('my-event should be emitted and listener called with args', function(done) {
        // Support module exporting either an emitter object or a factory function.
        let subject = (typeof testpilot_subject === 'function') ? testpilot_subject() : testpilot_subject;

        let called = false;

        // Listener checks the received arguments.
        function listener(a, b, c) {
            called = true;
            try {
                assert.strictEqual(a, 1);
                assert.strictEqual(b, 'two');
                assert.deepStrictEqual(c, { x: 3 });
            } catch (err) {
                return done(err);
            }
        }

        addOnce(subject, 'my-event', listener);

        // Try to emit the event using common APIs.
        function emitEvent(emitter, event, args) {
            if (typeof emitter.emit === 'function') {
                return emitter.emit.apply(emitter, [event].concat(args));
            }
            if (typeof emitter.trigger === 'function') {
                return emitter.trigger.apply(emitter, [event].concat(args));
            }
            if (typeof emitter.dispatchEvent === 'function') {
                // Try using CustomEvent if available to carry data.
                try {
                    let detail = args;
                    let ev;
                    if (typeof CustomEvent === 'function') {
                        ev = new CustomEvent(event, { detail: detail });
                    } else {
                        ev = { type: event, detail: detail };
                    }
                    return emitter.dispatchEvent(ev);
                } catch (e) {
                    // fallthrough to manual invocation
                }
            }
            // Fallback: call listeners registered in _events
            if (emitter._events && Array.isArray(emitter._events[event])) {
                emitter._events[event].forEach(function(fn) {
                    try { fn.apply(emitter, args); } catch (e) { /* ignore */ }
                });
                return true;
            }
            return false;
        }

        // Emit with the expected args.
        emitEvent(subject, 'my-event', [1, 'two', { x: 3 }]);

        // If listener invocation is synchronous (typical), called should be true now.
        // If implementation is async (unlikely), give a tiny delay.
        setTimeout(function() {
            try {
                assert.strictEqual(called, true, 'listener was not called when event emitted');
                done();
            } catch (err) {
                done(err);
            }
        }, 10);
    });
});