let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0015.convertToolsForAiSdk', function() {
        it('does not remove function properties from tool objects (functions remain callable on input)', function() {
            let toolWithFunc = {
                id: 'f1',
                name: 'func-tool',
                run: function(x) { return 'ran:' + x; }
            };
            let tools = [toolWithFunc];

            // ensure the function is present before conversion
            assert.strictEqual(typeof tools[0].run, 'function', 'precondition: run should be a function');

            let result = testpilot_subject.file_0015.convertToolsForAiSdk(tools);

            // conversion should not have removed or replaced the original function on the input object
            assert.strictEqual(typeof tools[0].run, 'function', 'input tool.run should remain a function after conversion');

            // Accept either an array of descriptors or a single descriptor object.
            assert.ok(result !== null && result !== undefined, 'result should not be null or undefined');

            if (Array.isArray(result)) {
                // result length should match
                assert.strictEqual(result.length, 1, 'result should contain one element');

                // result element should be an object (the conversion should produce object descriptors)
                assert.ok(result[0] !== null && typeof result[0] === 'object', 'result[0] should be an object');
            } else {
                // If a single object is returned instead of an array, ensure it's an object descriptor.
                assert.ok(typeof result === 'object', 'result should be an object descriptor');
            }
        });
    });
});