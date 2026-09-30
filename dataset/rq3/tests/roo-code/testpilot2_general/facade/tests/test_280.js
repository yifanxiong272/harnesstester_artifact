let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0006.WorktreeService.prototype.getAvailableBranches', function() {
        it('should exist on the prototype and be a function', function() {
            assert.ok(testpilot_subject, 'module loaded');
            assert.ok(testpilot_subject.file_0006, 'file_0006 namespace exists');
            const proto = testpilot_subject.file_0006.WorktreeService && testpilot_subject.file_0006.WorktreeService.prototype;
            assert.ok(proto, 'WorktreeService.prototype exists');
            const fn = proto.getAvailableBranches;
            assert.strictEqual(typeof fn, 'function', 'getAvailableBranches is a function');
        });

            })
})