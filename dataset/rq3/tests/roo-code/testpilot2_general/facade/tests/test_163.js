let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // basic convenience reference to the function under test
    let convert = null;
    before(function() {
        if (!testpilot_subject || !testpilot_subject.file_0003) {
            this.skip(); // skip whole suite if module shape is unexpected
            return;
        }
        convert = testpilot_subject.file_0003.convertToZAiFormat;
        if (typeof convert !== 'function') {
            this.skip();
        }
    });

    it('should handle an empty messages array without throwing and return an empty representation', function(done) {
        let messages = [];
        let snapshot = JSON.parse(JSON.stringify(messages));
        let result = convert(messages, { whatever: true });

        // result must exist (not undefined/null)
        assert.ok(result !== undefined && result !== null, 'result is undefined or null');

        // Accept either an array or a string representation like "[]"
        if (Array.isArray(result)) {
            assert.strictEqual(result.length, 0, 'expected returned array to be empty');
        } else if (typeof result === 'string') {
            // try to parse it as JSON; if it's valid JSON, it should represent an empty array
            try {
                let parsed = JSON.parse(result);
                assert.ok(Array.isArray(parsed), 'string result did not parse to an array');
                assert.strictEqual(parsed.length, 0, 'parsed array from string result not empty');
            } catch (e) {
                // if not JSON, at least it should be an empty-ish string
                assert.ok(result.length === 0 || result === '[]', 'string result for empty input is unexpected');
            }
        } else {
            // accept other types but fail because unexpected
            assert.fail('unexpected result type for empty input: ' + typeof result);
        }

        // ensure the original input was not mutated
        assert.deepStrictEqual(messages, snapshot, 'original messages array was mutated');

        done();
    });

    })