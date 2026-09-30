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

        it('should not mutate the params object passed in', function() {
            let params = {
                tool: 'example-tool',
                nested: {
                    a: 1,
                    b: [1,2,3]
                }
            };
            // shallow copy snapshot for later comparison
            let snapshot = JSON.parse(JSON.stringify(params));
            let result = testpilot_subject.file_0003.makeMissingToolResult(params);
            // original params must remain equal to snapshot
            assert.deepStrictEqual(params, snapshot, 'params object was mutated');
            // result is an object and JSON-serializable
            assert.ok(typeof result === 'object' && result !== null);
            assert.doesNotThrow(() => JSON.stringify(result));
            assertNoFunctions(result);
        });

            })
})