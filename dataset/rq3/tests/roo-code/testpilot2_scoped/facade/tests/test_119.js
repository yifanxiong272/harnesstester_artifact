let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('formatResult with no arguments returns an object with an empty system array and undefined messages', function(done) {
        let result = testpilot_subject.file_0010.CacheStrategy.prototype.formatResult();
        assert.strictEqual(typeof result, 'object');
        assert.ok(Array.isArray(result.system), 'system should be an array');
        assert.strictEqual(result.system.length, 0, 'default system array should be empty');
        assert.strictEqual(result.messages, undefined, 'messages should be undefined when not provided');
        done();
    });

    })