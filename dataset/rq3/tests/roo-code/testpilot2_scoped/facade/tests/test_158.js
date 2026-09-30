let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports the init function at the expected path', function(done) {
        // Locate the init function safely through the nested path
        let initFn;
        try {
            initFn = testpilot_subject
                && testpilot_subject.file_0012
                && testpilot_subject.file_0012.MessageQueueService
                && testpilot_subject.file_0012.MessageQueueService.EventEmitter
                && testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource
                && testpilot_subject.file_0012.MessageQueueService.EventEmitter.EventEmitterAsyncResource.init;
        } catch (e) {
            initFn = undefined;
        }

        assert.ok(initFn, 'init function should be present at the expected path');
        assert.strictEqual(typeof initFn, 'function', 'init should be a function');
        done();
    });

    })