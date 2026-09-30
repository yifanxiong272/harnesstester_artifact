let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0012.isValidCloudCodeAssistToolId basic behavior', function() {
        it('should return a boolean for a variety of input types (no throws)', function() {
            const samples = [
                "tool-123",
                "ABC_def.456",
                "",
                null,
                undefined,
                0,
                42,
                3.14,
                true,
                false,
                [],
                ["a","b"],
                {},
                { id: "x" },
                function(){},
                Symbol("sym"),
                // BigInt literal (may not be present in very old Node versions)
                (typeof BigInt !== 'undefined') ? BigInt(123) : "no-bigint"
            ];

            samples.forEach((s) => {
                // ensure the call does not throw
                assert.doesNotThrow(() => {
                    const res = testpilot_subject.file_0012.isValidCloudCodeAssistToolId(s);
                    // and that the result is a boolean
                    assert.strictEqual(typeof res, 'boolean', `expected boolean for input ${String(s)}`);
                }, `function threw for input: ${String(s)}`);
            });
        });

            })
})