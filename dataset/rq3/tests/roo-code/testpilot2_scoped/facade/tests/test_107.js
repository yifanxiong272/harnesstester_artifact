let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('should expose createCachePoint on the prototype and it should be a function', function() {
        assert.ok(testpilot_subject, 'module should be present');
        assert.ok(testpilot_subject.file_0010, 'file_0010 namespace should be present');
        const proto = testpilot_subject.file_0010.CacheStrategy && testpilot_subject.file_0010.CacheStrategy.prototype;
        assert.ok(proto, 'CacheStrategy.prototype should exist');
        assert.strictEqual(typeof proto.createCachePoint, 'function', 'createCachePoint should be a function');
    });

    })