let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('listeners returns an array (empty when no listeners)', function() {
        // Obtain constructor
        let EER = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;
        assert.strictEqual(typeof EER, 'function', 'Expected constructor function');

        // Create instance - provide a name so AsyncResource/constructor doesn't throw
        let ee = new EER({ name: 'EventEmitterAsyncResource' });

        // Should return an array when there are no listeners
        let empty = ee.listeners('no_such_event');
        assert.ok(Array.isArray(empty), 'listeners should return an array');
        assert.strictEqual(empty.length, 0);
    });

    })