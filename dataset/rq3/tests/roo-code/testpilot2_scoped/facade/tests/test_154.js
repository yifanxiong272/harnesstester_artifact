let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const C = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('constructs and exposes asyncResource and ids', function() {
        // provide a name so AsyncResource/options.name is a string
        const inst = new C('test');
        // basic shape checks
        assert.strictEqual(typeof inst.emit, 'function', 'has emit method');
        assert.ok(inst.asyncResource, 'has asyncResource property');
        // asyncId and triggerAsyncId should be numbers (finite)
        assert.strictEqual(typeof inst.asyncId, 'number');
        assert.ok(Number.isFinite(inst.asyncId));
        assert.strictEqual(typeof inst.triggerAsyncId, 'number');
        assert.ok(Number.isFinite(inst.triggerAsyncId));
    });

    })