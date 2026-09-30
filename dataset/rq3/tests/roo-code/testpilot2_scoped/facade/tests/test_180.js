let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const EPath = testpilot_subject
        && testpilot_subject.file_0012
        && testpilot_subject.file_0012.MessageQueueService
        && testpilot_subject.file_0012.MessageQueueService.EventEmitter
        && testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

    it('precondition: EventEmitterAsyncResource constructor/prototype should exist', function() {
        assert.ok(EPath, 'EventEmitterAsyncResource not found on testpilot_subject at expected path');
        assert.strictEqual(typeof EPath.prototype.prependListener, 'function', 'prependListener should be a function on prototype');
        assert.strictEqual(typeof EPath.prototype.emit, 'function', 'emit should be a function on prototype');
        // at least one other listener-adder should exist
        assert.ok(typeof EPath.prototype.on === 'function' || typeof EPath.prototype.addListener === 'function', 'on/addListener should exist on prototype');
    });

    })