let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('constructor: MessageQueueService can be instantiated', function() {
        let svc = new testpilot_subject.file_0012.MessageQueueService();
        assert.ok(svc && typeof svc === 'object', 'instance should be an object');
    });

    })