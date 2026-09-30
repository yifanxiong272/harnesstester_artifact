let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const collect = testpilot_subject.file_0014.TagMatcher.prototype.collect;

    it('does nothing when cached is empty', function(done) {
        const obj = {
            cached: [],
            chunks: [{ data: 'existing', matched: true }],
            matched: true
        };
        // Should return early and not modify chunks or cached
        collect.call(obj);
        assert.deepStrictEqual(obj.chunks, [{ data: 'existing', matched: true }], 'chunks should be unchanged');
        assert.deepStrictEqual(obj.cached, [], 'cached should remain empty');
        done();
    });

    })