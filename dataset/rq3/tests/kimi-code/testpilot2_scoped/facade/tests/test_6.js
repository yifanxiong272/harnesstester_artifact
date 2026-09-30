let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    it('first dependency should have an id property with a toString function', function() {
        let id = testpilot_subject.file_0001.FsWatcherService.$di$dependencies[0].id;
        assert.ok(id !== undefined && id !== null, 'id should be defined and not null');

        // toString may come from prototype, so check it's callable on the value
        assert.ok(typeof id.toString === 'function', 'id.toString should be a function');
    });

    })