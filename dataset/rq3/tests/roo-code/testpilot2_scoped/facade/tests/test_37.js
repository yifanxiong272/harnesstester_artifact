let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const MultiPointStrategy = testpilot_subject.file_0006.MultiPointStrategy;

    it('returns formatWithoutCachePoints when usePromptCache is false or messages empty', function() {
        const inst = Object.create(MultiPointStrategy.prototype);

        // Case A: usePromptCache = false
        inst.config = { usePromptCache: false, messages: ['m1'], modelInfo: {} };
        let called = 0;
        inst.formatWithoutCachePoints = function() { called++; return {noCache: true}; };

        let res = inst.determineOptimalCachePoints();
        assert.strictEqual(called, 1, 'formatWithoutCachePoints should be called once when usePromptCache is false');
        assert.deepStrictEqual(res, {noCache: true});

        // Case B: usePromptCache true but messages empty -> should also call formatWithoutCachePoints
        inst.config.usePromptCache = true;
        inst.config.messages = [];
        called = 0;
        res = inst.determineOptimalCachePoints();
        assert.strictEqual(called, 1, 'formatWithoutCachePoints should be called once when messages array is empty');
        assert.deepStrictEqual(res, {noCache: true});
    });

    })