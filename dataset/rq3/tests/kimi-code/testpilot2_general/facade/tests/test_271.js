let mocha = require('mocha');
let assert = require('assert');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('should expose resolvePlanPath on ToolCallComponent.prototype', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0003, 'expected file_0003 namespace');
        assert.ok(testpilot_subject.file_0003.ToolCallComponent, 'expected ToolCallComponent constructor');
        let fn = testpilot_subject.file_0003.ToolCallComponent.prototype.resolvePlanPath;
        assert.strictEqual(typeof fn, 'function', 'resolvePlanPath should be a function');
    });

    })