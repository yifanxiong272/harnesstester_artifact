let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0003.ToolCallComponent.prototype.resolvePlanBoxStatus - exists', function(done) {
        // verify the namespace and the prototype method exist
        assert.ok(testpilot_subject, 'testpilot_subject should be defined');
        assert.ok(testpilot_subject.file_0003, 'testpilot_subject.file_0003 should be defined');
        let proto = testpilot_subject.file_0003.ToolCallComponent && testpilot_subject.file_0003.ToolCallComponent.prototype;
        assert.ok(proto, 'ToolCallComponent.prototype should be defined');
        assert.strictEqual(typeof proto.resolvePlanBoxStatus, 'function', 'resolvePlanBoxStatus should be a function');
        done();
    });

    })