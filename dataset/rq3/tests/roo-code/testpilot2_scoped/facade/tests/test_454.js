let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0026.ToolInputSchema.spa', function() {
        it('should exist and be a function with arity 2', function() {
            let spa = testpilot_subject.file_0026.ToolInputSchema.spa;
            assert.strictEqual(typeof spa, 'function', 'spa should be a function');
            // The declared number of formal parameters should be 2
            assert.strictEqual(spa.length, 2, 'spa should declare two parameters');
        });

            })
})