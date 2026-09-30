let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');
let EventEmitter = require('events').EventEmitter;

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0007.MessageProcessor.prototype.emitNewMessageEvents', function() {
        let originalEmit;
        let calls;

        beforeEach(function() {
            // Capture EventEmitter.emit calls so we can observe any emitted events.
            originalEmit = EventEmitter.prototype.emit;
            calls = [];
            EventEmitter.prototype.emit = function(...args) {
                // record the call (store reference to "this" and the args)
                calls.push({ thisRef: this, args: args });
                // still call the original implementation to avoid changing behavior
                return originalEmit.apply(this, args);
            };
        });

        afterEach(function() {
            // restore original emit to avoid side effects on other tests
            EventEmitter.prototype.emit = originalEmit;
        });

        it('does not emit any events when messages array is empty', function() {
            let processor = new testpilot_subject.file_0007.MessageProcessor();
            // clear any emits that may have occurred during construction
            calls.length = 0;

            let previousState = {};
            let currentState = {};
            let messages = [];

            processor.emitNewMessageEvents(previousState, currentState, messages);

            // No calls should have been made to EventEmitter.emit
            assert.strictEqual(calls.length, 0, 'expected no events to be emitted when messages array is empty');
        });

    })
})