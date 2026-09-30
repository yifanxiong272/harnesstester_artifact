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

    // Helper to emit an event using a variety of common APIs.
    function emitEvent(emitter, event /*, ...args */) {
        let args = Array.prototype.slice.call(arguments, 2);
        if (typeof emitter.emit === 'function') return emitter.emit.apply(emitter, [event].concat(args));
        if (typeof emitter.trigger === 'function') return emitter.trigger.apply(emitter, [event].concat(args));
        if (typeof emitter.publish === 'function') return emitter.publish.apply(emitter, [event].concat(args));
        if (typeof emitter._emit === 'function') return emitter._emit.apply(emitter, [event].concat(args));
        if (typeof emitter.dispatchEvent === 'function') {
            // Try to construct a simple Event if available; otherwise pass a plain object.
            try {
                if (typeof Event === 'function') {
                    return emitter.dispatchEvent(new Event(event));
                } else {
                    return emitter.dispatchEvent({ type: event, args: args });
                }
            } catch (e) {
                return emitter.dispatchEvent({ type: event, args: args });
            }
        }
        // fallback: if we populated _events ourselves above, call them directly
        if (emitter._events && Array.isArray(emitter._events[event])) {
            emitter._events[event].forEach(function(fn) {
                try { fn.apply(emitter, args); } catch (e) { /* swallow individual listener errors here */ }
            });
            return;
        }
        // No known emit mechanism
        throw new Error('No known emit method found on emitter');
    }

    it('should set the listener this value to the emitter when called', function(done) {
        let EmitterClass = testpilot_subject && testpilot_subject.file_0012 && testpilot_subject.file_0012.MessageQueueService && testpilot_subject.file_0012.MessageQueueService.EventEmitter;
        assert.ok(EmitterClass, 'EventEmitter class not found on testpilot_subject.file_0012.MessageQueueService');

        let emitter = new EmitterClass();

        function listener() {
            // inside listener, "this" should be the emitter instance in typical implementations
            assert.strictEqual(this, emitter, 'listener this value is not the emitter instance');
            called = true;
            done();
        }

        let called = false;
        addListener(emitter, 'context-event', listener);

        // Trigger the event using a best-effort emitter API
        try {
            emitEvent(emitter, 'context-event');
        } catch (err) {
            // If we can't emit, fail the test explicitly
            done(err);
        }
    });
});