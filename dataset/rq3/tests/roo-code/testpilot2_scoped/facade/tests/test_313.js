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

    it('should support once semantics (listener called only once) if available', function() {
        let EmitterClass = testpilot_subject && testpilot_subject.file_0012 && testpilot_subject.file_0012.MessageQueueService && testpilot_subject.file_0012.MessageQueueService.EventEmitter;
        assert.ok(EmitterClass, 'EventEmitter class not found on testpilot_subject.file_0012.MessageQueueService');

        let emitter = new EmitterClass();
        // If neither once nor a compatible API exists, skip this check by returning early.
        if (typeof emitter.once !== 'function' && typeof emitter.on !== 'function' && typeof emitter.addListener !== 'function' && typeof emitter.addEventListener !== 'function' && typeof emitter.subscribe !== 'function') {
            this && this.skip && this.skip(); // allow mocha to skip when possible
            return;
        }

        let count = 0;
        addOnce(emitter, 'once-event', function() {
            count += 1;
        });

        emitter.em    })
})