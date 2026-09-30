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

    // Helper to emit/dispatch an event using common method names, with a _events fallback.
    function emitEvent(emitter, event /*, ...args */) {
        let args = Array.prototype.slice.call(arguments, 2);
        if (typeof emitter.emit === 'function') return emitter.emit.apply(emitter, [event].concat(args));
        if (typeof emitter.dispatchEvent === 'function') {
            // Some implementations expect an Event-like object
            let ev = typeof args[0] === 'object' ? args[0] : { type: event, args: args };
            return emitter.dispatchEvent(ev);
        }
        if (typeof emitter.trigger === 'function') return emitter.trigger.apply(emitter, [event].concat(args));
        if (typeof emitter.publish === 'function') return emitter.publish.apply(emitter, [event].concat(args));
        if (typeof emitter.notify === 'function') return emitter.notify.apply(emitter, [event].concat(args));
        if (typeof emitter.send === 'function') return emitter.send.apply(emitter, [event].concat(args));
        // Best-effort fallback: call functions stored in _events
        if (emitter._events && Array.isArray(emitter._events[event])) {
            // copy in case handlers modify the array
            let handlers = emitter._events[event].slice();
            for (let i = 0; i < handlers.length; i++) {
                try { handlers[i].apply(emitter, args); } catch (e) { /* swallow to mimic many emitters */ }
            }
            return;
        }
        // nothing we can do
    }

    it('should call multiple listeners in the order they were added', function(done) {
        let EmitterClass = testpilot_subject && testpilot_subject.file_0012 && testpilot_subject.file_0012.MessageQueueService && testpilot_subject.file_0012.MessageQueueService.EventEmitter;
        assert.ok(EmitterClass, 'EventEmitter class not found on testpilot_subject.file_0012.MessageQueueService');

        let emitter = new EmitterClass();
        let order = [];

        function l1() { order.push('l1'); }
        function l2() { order.push('l2'); }
        function l3() { order.push('l3'); }

        addListener(emitter, 'multi', l1);
        addListener(emitter, 'multi', l2);
        addListener(emitter, 'multi', l3);

        // Emit the event using a best-effort approach and then assert the listener order.
        emitEvent(emitter, 'multi');

        // Some emitter implementations might invoke listeners asynchronously.
        // Schedule the assertion on the next tick to be safe.
        let schedule = typeof setImmediate === 'function' ? setImmediate : function(fn){ setTimeout(fn, 0); };
        schedule(function() {
            try {
                assert.deepStrictEqual(order, ['l1', 'l2', 'l3']);
                done();
            } catch (err) {
                done(err);
            }
        });
    });
});