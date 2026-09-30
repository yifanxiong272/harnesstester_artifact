let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('test testpilot_subject.file_0007.MessageProcessor.prototype.notifyTaskCleared', function() {
        it('should call store.clear once and then emit "taskCleared" with undefined', function() {
            // Locate the MessageProcessor prototype
            let MP = testpilot_subject && testpilot_subject.file_0007 && testpilot_subject.file_0007.MessageProcessor;
            assert.ok(MP, "Expected testpilot_subject.file_0007.MessageProcessor to exist");

            // Create an object that uses the prototype but does not run any constructor
            let mp = Object.create(MP.prototype);

            // Instrumentation to verify call order and arguments
            let calls = [];
            let clearCount = 0;
            mp.store = {
                clear: function() {
                    clearCount++;
                    calls.push({ type: 'clear' });
                }
            };
            mp.emitter = {
                emit: function(eventName, payload) {
                    calls.push({ type: 'emit', eventName: eventName, payload: payload });
                }
            };

            // Call the method
            let result = mp.notifyTaskCleared();

            // verify return value is undefined
            assert.strictEqual(result, undefined);

            // verify clear was called exactly once
            assert.strictEqual(clearCount, 1, "store.clear should be called exactly once");

            // verify the order: clear then emit
            assert.ok(calls.length >= 2, "Expected at least two recorded calls (clear then emit)");
            assert.strictEqual(calls[0].type, 'clear', "First action should be clear");
            assert.strictEqual(calls[1].type, 'emit', "Second action should be emit");

            // verify event name and payload (payload should be undefined)
            assert.strictEqual(calls[1].eventName, 'taskCleared');
            // The code emits void 0 which is undefined
            assert.strictEqual(calls[1].payload, undefined);
        });

            })
})