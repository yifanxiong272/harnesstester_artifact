let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const pathParts = [
        'file_0012',
        'MessageQueueService',
        'EventEmitter',
        'EventEmitterAsyncResource'
    ];

    function getCtor() {
        // Walk the nested path to the constructor
        let cur = testpilot_subject;
        for (let part of pathParts) {
            if (!cur) return undefined;
            cur = cur[part];
        }
        return cur;
    }

    it('has the EventEmitterAsyncResource constructor and getMaxListeners method', function() {
        const Ctor = getCtor();
        assert.ok(Ctor, 'Constructor not found at expected path');
        assert.ok(Ctor.prototype, 'Constructor has no prototype');
        assert.strictEqual(typeof Ctor.prototype.getMaxListeners, 'function', 'getMaxListeners is not a function');
    });

    })