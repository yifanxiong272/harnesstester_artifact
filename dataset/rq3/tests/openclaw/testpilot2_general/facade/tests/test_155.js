let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports file_0002.createAcpReplyProjector as a function', function(done) {
        assert.ok(testpilot_subject, 'module should be present');
        assert.ok(testpilot_subject.file_0002, 'file_0002 namespace should be present');
        assert.strictEqual(typeof testpilot_subject.file_0002.createAcpReplyProjector, 'function',
            'createAcpReplyProjector should be a function');
        done();
    });

    })