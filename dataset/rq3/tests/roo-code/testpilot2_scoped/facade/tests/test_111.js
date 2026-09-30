let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const CacheStrategyProto = testpilot_subject &&
                               testpilot_subject.file_0010 &&
                               testpilot_subject.file_0010.CacheStrategy &&
                               testpilot_subject.file_0010.CacheStrategy.prototype;

    it('has a meetsMinTokenThreshold function on the prototype', function() {
        assert.ok(CacheStrategyProto, 'CacheStrategy prototype should exist on testpilot_subject.file_0010');
        assert.strictEqual(typeof CacheStrategyProto.meetsMinTokenThreshold, 'function', 'meetsMinTokenThreshold should be a function');
    });

    })