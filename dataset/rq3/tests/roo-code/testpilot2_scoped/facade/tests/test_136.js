let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0012.MessageQueueService.getEventListeners - EventEmitter path', function() {
        const svc = testpilot_subject.file_0012.MessageQueueService;
        // Fake EventEmitter-like object with listeners function
        const fakeEmitter = {
            listeners: function(type) {
                return ['listenerA', 'listenerB', type];
            }
        };
        const result = svc.getEventListeners(fakeEmitter, 'myType');
        assert.deepStrictEqual(result, ['listenerA', 'listenerB', 'myType']);
    });

    })