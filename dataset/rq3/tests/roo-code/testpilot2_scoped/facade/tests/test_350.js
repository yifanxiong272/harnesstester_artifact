let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0014.TagMatcher.prototype.update', function() {
        it('calls _update with the chunk and returns the result of pop', function() {
            const update = testpilot_subject.file_0014.TagMatcher.prototype.update;
            let seenChunk = null;
            const obj = {
                _update: function(chunk) { seenChunk = chunk; },
                pop: function() { return {ok: true, chunk: seenChunk}; },
                update: update
            };

            const chunk = { some: 'data' };
            const result = obj.update(chunk);

            assert.strictEqual(seenChunk, chunk, '_update should receive the exact chunk argument');
            assert.deepStrictEqual(result, {ok: true, chunk: chunk}, 'update should return the value returned by pop');
        });

            })
})