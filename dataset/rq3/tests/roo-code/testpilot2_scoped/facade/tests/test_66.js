let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0008.OpenAICompatibleHandler.prototype.mapToolChoice - method exists', function(done) {
        const Handler = testpilot_subject.file_0008 && testpilot_subject.file_0008.OpenAICompatibleHandler;
        assert.ok(Handler, 'OpenAICompatibleHandler constructor should exist');
        assert.strictEqual(typeof Handler.prototype.mapToolChoice, 'function', 'mapToolChoice should be a function on the prototype');
        done();
    });

    })