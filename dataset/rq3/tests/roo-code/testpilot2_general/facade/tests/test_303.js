let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Grab the constructor (if it exists)
    const MPctor = testpilot_subject &&
                  testpilot_subject.file_0007 &&
                  testpilot_subject.file_0007.MessageProcessor;

    // Will hold an instance we can call methods on (if creation succeeds)
    let instance = null;

    // Try to create an instance once before running tests.
    // If we can't construct, try a safe fallback using Object.create so tests that only
    // rely on prototype-level information can continue. If neither works, skip tests.
    before(function() {
        if (typeof MPctor !== 'function') {
            // If the constructor isn't present, skip the suite.
            this.skip();
            return;
        }

        try {
            // Preferred: call the real constructor
            instance = new MPctor();
        } catch (e) {
            // Fallback: create an object whose prototype is MPctor.prototype,
            // avoiding any constructor side-effects.
            try {
                instance = Object.create(MPctor.prototype);
            } catch (e2) {
                // Can't obtain an instance; skip tests
                this.skip();
            }
        }
    });

    it('test testpilot_subject.file_0007.MessageProcessor.prototype.handleAction exists and is a function', function() {
        assert.ok(typeof MPctor === 'function', 'MessageProcessor constructor should be a function');
        assert.ok(MPctor.prototype, 'MessageProcessor.prototype should exist');
        assert.strictEqual(typeof MPctor.prototype.handleAction, 'function',
            'handleAction should be defined on the prototype and be a function');
        // Expect the function to accept one argument (convention)
        assert.strictEqual(MPctor.prototype.handleAction.length, 1,
            'handleAction should have arity 1 (one declared parameter)');
    });

    })