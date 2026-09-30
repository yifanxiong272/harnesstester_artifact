let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('listeners() returns empty array when no listeners are registered', function(done) {
        const EER = testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource;
        // Provide a name so AsyncResource/options.name is defined
        const ee = new EER('test');

        const listeners = ee.listeners('noSuchEvent');
        assert.ok(Array.isArray(listeners), 'listeners should return an array');
        assert.strictEqual(listeners.length, 0, 'no listeners should be present');
        done();
    });

    })