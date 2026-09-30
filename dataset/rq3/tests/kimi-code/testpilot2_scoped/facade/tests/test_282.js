let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('forwards sessionId to sessionApi and strips sessionId from payload (sync)', function() {
        // Grab prototype where getBackgroundOutput is defined
        const proto = testpilot_subject.file_0002.KimiCore.prototype;

        // Capture calls for verification
        const calls = [];

        // Create an object whose prototype is the KimiCore prototype,
        // and provide a fake sessionApi implementation.
        const obj = {
            sessionApi: function(sid) {
                calls.push(sid);
                return {
                    getBackgroundOutput: function(payload) {
                        // sessionId must be removed from payload by destructuring
                        assert.strictEqual(payload.sessionId, undefined);
                        // remaining payload should match what we passed
                        assert.deepStrictEqual(payload, { foo: 1, bar: 2 });
                        return 'SYNC_OK';
                    }
                };
            }
        };
        Object.setPrototypeOf(obj, proto);

        // Call the method under test
        const result = obj.getBackgroundOutput({ sessionId: 'abc123', foo: 1, bar: 2 });

        // Assertions
        assert.strictEqual(calls.length, 1);
        assert.strictEqual(calls[0], 'abc123');
        assert.strictEqual(result, 'SYNC_OK');
    });

    })