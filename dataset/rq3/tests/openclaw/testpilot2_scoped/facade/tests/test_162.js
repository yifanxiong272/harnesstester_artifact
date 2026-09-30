let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper to deep clone simple JSON-safe structures
    function deepClone(obj) {
        return JSON.parse(JSON.stringify(obj));
    }

    it('test preserves message keys (does not drop keys) for each message object', function() {
        let messages = [
            { role: 'tool', name: 't1', content: 'raw' },
            { role: 'user', content: { nested: true }, metadata: { id: 42 } }
        ];
        // Keep a clone to detect accidental mutation
        let original = deepClone(messages);

        let resultRaw = testpilot_subject.file_0003.repairToolCallInputs(messages, { debug: true });
        // allow implementations that return either an array directly or an object containing the array as `.messages`
        let result = resultRaw;
        if (!Array.isArray(result) && result && Array.isArray(result.messages)) {
            result = result.messages;
        }
        assert.ok(Array.isArray(result), 'expected an array result');

        // For each message ensure the returned corresponding message contains at least the keys present in the input message
        for (let i = 0; i < messages.length; i++) {
            let inputMsg = messages[i];
            let outMsg = result[i];
            assert.ok(outMsg && typeof outMsg === 'object', `expected result[${i}] to be an object`);

            Object.keys(inputMsg).forEach(key => {
                assert.ok(Object.prototype.hasOwnProperty.call(outMsg, key),
                    `expected key "${key}" from input message[${i}] to be present in output`);
            });
        }

        // Ensure original wasn't mutated
        assert.deepStrictEqual(messages, original, 'original messages were mutated in this operation');
    });
});