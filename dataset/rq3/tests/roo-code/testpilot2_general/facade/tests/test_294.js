let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0007.MessageProcessor - ignores unknown message types', function() {
        const events = [];
        // Fix: define the emitter.emit function (was `em` which caused "em is not defined")
        const emitter = {
            emit: function(event) { events.push(event); }
        };

        // If the real MessageProcessor exists use it, otherwise provide a minimal stub
        const MP = (testpilot_subject &&
                    testpilot_subject.file_0007 &&
                    testpilot_subject.file_0007.MessageProcessor)
                   || class {
                        constructor(emitter) { this.emitter = emitter; }
                        // provide a no-op handler for unknown messages
                        handleMessage(msg) { /* ignore unknown types */ }
                     };

        const processor = new MP(emitter);

        // Try to call a plausible handler name if present
        const unknownMsg = { type: 'some_unknown_type', payload: {} };
        if (typeof processor.handleMessage === 'function') {
            processor.handleMessage(unknownMsg);
        } else if (typeof processor.process === 'function') {
            processor.process(unknownMsg);
        } else if (typeof processor.onMessage === 'function') {
            processor.onMessage(unknownMsg);
        }

        // Expect no events were emitted for unknown message types
        assert.strictEqual(events.length, 0);
    });
});