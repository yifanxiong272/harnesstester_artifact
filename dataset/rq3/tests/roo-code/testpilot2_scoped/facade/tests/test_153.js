let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const C = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('constructor accepts a string name without throwing', function() {
        // Should be allowed to pass a string as the name
        const inst = new C('MyCustomName');
        assert.ok(inst instanceof C);
        // still exposes asyncResource and ids
        assert.ok(inst.asyncResource);
        assert.strictEqual(typeof inst.asyncId, 'number');
    });

    })