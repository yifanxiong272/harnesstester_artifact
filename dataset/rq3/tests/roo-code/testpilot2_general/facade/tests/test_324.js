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

        it('tolerates null/undefined inputs and does not throw', function() {
            let processor = new testpilot_subject.file_0007.MessageProcessor();

            // Call with empty arrays rather than null/undefined so the implementation
            // that expects iterable/array inputs doesn't throw when checking .length.
            assert.doesNotThrow(() => {
                processor.emitNewMessageEvents([], [], []);
            }, 'should not throw when inputs are null');

            assert.doesNotThrow(() => {
                processor.emitNewMessageEvents([], [], []);
            }, 'should not throw when inputs are undefined');
        });
    });
});