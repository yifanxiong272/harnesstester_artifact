let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0010.CacheStrategy.prototype.messagesToContentBlocks - existence', function(done) {
        const CacheStrategy = testpilot_subject.file_0010 && testpilot_subject.file_0010.CacheStrategy;
        assert.ok(CacheStrategy, 'CacheStrategy constructor should exist on testpilot_subject.file_0010');
        assert.strictEqual(typeof CacheStrategy.prototype.messagesToContentBlocks, 'function',
            'messagesToContentBlocks should be a function on the prototype');
        done();
    });

    })