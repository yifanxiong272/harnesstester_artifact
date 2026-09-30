let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0004.PromptManager.prototype.beforePrompt', function() {
    // Helper: get the constructor (if present) and create an instance in a forgiving way.
    function getCtor() {
        if (!testpilot_subject) return null;
        if (testpilot_subject.file_0004 && testpilot_subject.file_0004.PromptManager) {
            return testpilot_subject.file_0004.PromptManager;
        }
        return null;
    }

    function createInstance() {
        const Ctor = getCtor();
        assert.ok(Ctor, 'PromptManager constructor must be available at testpilot_subject.file_0004.PromptManager');
        // Try normal construction; if that fails, create a plain object inheriting the prototype.
        try {
            return new Ctor();
        } catch (e) {
            // Fallback: create a bare object with the prototype to allow calling prototype methods.
            return Object.create(Ctor.prototype);
        }
    }

    // Helper: call beforePrompt and normalize sync/async returns into a Promise.
    function callBeforePrompt(instance, arg) {
        // the method might be defined on prototype or instance
        const fn = instance.beforePrompt || (instance.__proto__ && instance.__proto__.beforePrompt);
        assert.strictEqual(typeof fn, 'function', 'beforePrompt must be a function on the instance or its prototype');

        try {
            const ret = fn.call(instance, arg);
            if (ret && (typeof ret === 'object' || typeof ret === 'function') && typeof ret.then === 'function') {
                return ret; // a Promise-like value
            } else {
                return Promise.resolve(ret); // synchronous result
            }
        } catch (err) {
            return Promise.reject(err);
        }
    }

    it('exists and is a function', function() {
        const Ctor = getCtor();
        assert.ok(Ctor, 'PromptManager constructor should exist');
        const proto = Ctor.prototype;
        assert.ok(proto, 'PromptManager.prototype should exist');
        assert.strictEqual(typeof proto.beforePrompt, 'function', 'beforePrompt should be a function on the prototype');
    });

    })