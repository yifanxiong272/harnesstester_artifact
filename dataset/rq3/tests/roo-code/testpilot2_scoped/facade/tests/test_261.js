let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to obtain add/remove methods safely
    function getAddMethod(inst) {
        return inst.on || inst.addListener || inst.add || null;
    }
    function getRemoveMethod(inst) {
        return inst.removeListener || inst.off || inst.remove || null;
    }

    it('has listenerCount function and returns 0 when there are no listeners', function() {
        const E = testpilot_subject &&
                  testpilot_subject.file_0012 &&
                  testpilot_subject.file_0012.MessageQueueService &&
                  testpilot_subject.file_0012.MessageQueueService.EventEmitter &&
                  testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;

        assert.ok(E, 'EventEmitterAsyncResource constructor not found on testpilot_subject');
        // Provide a name option to satisfy the constructor's requirement
        const inst = new E({ name: 'EventEmitterAsyncResource' });

        assert.strictEqual(typeof inst.listenerCount, 'function', 'listenerCount should be a function');
        // no listeners yet
        assert.strictEqual(inst.listenerCount('some-event'), 0);
    });

    })