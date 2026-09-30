let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0002.createAcpReplyProjector', function() {
    const create = testpilot_subject &&
                   testpilot_subject.file_0002 &&
                   testpilot_subject.file_0002.createAcpReplyProjector;

    it('is exported as a function', function() {
        assert.strictEqual(typeof create, 'function', 'createAcpReplyProjector should be a function');
    });

    })