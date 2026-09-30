let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0010.CacheStrategy.prototype.createCachePoint', function() {
        let CacheStrategyProto = testpilot_subject &&
                                 testpilot_subject.file_0010 &&
                                 testpilot_subject.file_0010.CacheStrategy &&
                                 testpilot_subject.file_0010.CacheStrategy.prototype;

        it('is present on the prototype', function() {
            assert.ok(CacheStrategyProto, 'CacheStrategy prototype should exist');
            assert.strictEqual(typeof CacheStrategyProto.createCachePoint, 'function',
                               'createCachePoint should be a function');
        });

            })
})