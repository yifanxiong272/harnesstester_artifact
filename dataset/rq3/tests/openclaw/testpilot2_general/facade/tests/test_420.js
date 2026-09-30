let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0014.sanitizeToolResult', function() {
        it('should leave a plain JSON-serializable object unchanged (content equal)', function() {
            const input = {
                id: 123,
                name: "example",
                ok: true,
                nested: {
                    a: [1, 2, 3],
                    b: { c: "d" }
                },
                nil: null
            };

            const result = testpilot_subject.file_0014.sanitizeToolResult(input);

            // The sanitizer should preserve the content of a JSON-safe object.
            assert.deepStrictEqual(result, input);
        });

            })
})