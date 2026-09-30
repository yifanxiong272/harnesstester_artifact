let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0002.createAcpReplyProjector', function() {
    // Sanity: ensure the function exists
    it('exports createAcpReplyProjector', function() {
        assert.ok(typeof testpilot_subject.file_0002.createAcpReplyProjector === 'function');
    });

    })