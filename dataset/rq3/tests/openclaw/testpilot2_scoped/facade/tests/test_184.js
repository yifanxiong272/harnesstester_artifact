let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0006.createWebFetchTool - function exists and returns a value', function() {
        assert.strictEqual(typeof testpilot_subject.file_0006.createWebFetchTool, 'function', 'createWebFetchTool should be a function');
        let tool;
        assert.doesNotThrow(() => {
            tool = testpilot_subject.file_0006.createWebFetchTool();
        }, Error, 'Calling createWebFetchTool() should not throw');

        assert.ok(tool !== null && (typeof tool === 'function' || typeof tool === 'object'),
            'createWebFetchTool should return a non-null function or object');
    });

    })