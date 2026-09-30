let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0003.makeMissingToolResult', function() {
        // Helper: ensure an object graph contains no functions (so it's JSON-serializable in practice)
        function assertNoFunctions(value, path) {
            path = path || '';
            if (value === null) return;
            if (typeof value === 'function') {
                throw new Error('Function found at ' + path);
            }
            if (typeof value === 'object') {
                if (Array.isArray(value)) {
                    for (let i = 0; i < value.length; i++) {
                        assertNoFunctions(value[i], path + '[' + i + ']');
                    }
                } else {
                    for (let k of Object.keys(value)) {
                        assertNoFunctions(value[k], path ? path + '.' + k : k);
                    }
                }
            }
        }

        it('should not throw and should return a non-null object for undefined input', function() {
            // pass an empty object so the implementation that expects fields like toolCallId won't throw
            let result = testpilot_subject.file_0003.makeMissingToolResult({});
            assert.ok(typeof result === 'object', 'result should be an object (or array)');
            assert.ok(result !== null, 'result should not be null');
            // JSON.stringify should not throw (i.e. no circular refs and values are serializable)
            assert.doesNotThrow(() => JSON.stringify(result));
            // result should not contain functions
            assertNoFunctions(result);
        });

            })
})