let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0006.createWebFetchTool', function() {
    it('should be a function', function() {
        const create = testpilot_subject.file_0006.createWebFetchTool;
        assert.strictEqual(typeof create, 'function');
    });

    })