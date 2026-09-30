let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0003.ToolCallComponent.prototype.appendSubToolCall', function() {
        // Helper to create a ToolCallComponent instance robustly.
        function makeComponent() {
            let Ctor = testpilot_subject &&
                      testpilot_subject.file_0003 &&
                      testpilot_subject.file_0003.ToolCallComponent;
            assert.ok(Ctor, 'ToolCallComponent constructor not found on testpilot_subject.file_0003');

            // Try to construct normally; if it throws, fall back to creating an object from the prototype.
            try {
                return new Ctor();
            } catch (e) {
                // Create a lightweight instance with the same prototype so prototype methods exist.
                let obj = Object.create(Ctor.prototype);
                return obj;
            }
        }

        it('should exist as a function on the prototype', function() {
            let proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
            assert.ok(proto, 'Prototype for ToolCallComponent missing');
            assert.strictEqual(typeof proto.appendSubToolCall, 'function',
                'appendSubToolCall should be a function on the prototype');
        });

            })
})