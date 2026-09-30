let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('has ToolCallComponent.upsertSubToolActivity as a function with arity 5', function(done) {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0003, 'file_0003 should exist on module');
        assert.ok(testpilot_subject.file_0003.ToolCallComponent, 'ToolCallComponent should exist');
        let protoFn = testpilot_subject.file_0003.ToolCallComponent.prototype.upsertSubToolActivity;
        assert.strictEqual(typeof protoFn, 'function', 'upsertSubToolActivity should be a function');
        // function should accept five parameters (id,name,args,phase,output)
        assert.strictEqual(protoFn.length, 5);
        done();
    });

    })