let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0014.TagMatcher.prototype.final', function() {
    it('calls _update when chunk is truthy, then calls collect, and returns pop() result', function() {
        // Grab the final function from the prototype
        const finalFn = testpilot_subject.file_0014.TagMatcher.prototype.final;

        // Prepare a fake instance with spies/stubs for _update, collect, pop
        const calls = [];
        const chunkObj = { some: 'data' };
        const popReturn = { popped: true };

        const fake = {
            _update: function(chunk) {
                calls.push({ name: '_update', arg: chunk });
            },
            collect: function() {
                calls.push({ name: 'collect' });
            },
            pop: function() {
                calls.push({ name: 'pop' });
                return popReturn;
            }
        };

        // Call final with chunk (truthy)
        const result = finalFn.call(fake, chunkObj);

        // Ensure update was called with the same chunk, then collect, then pop was called and its result returned
        assert.strictEqual(result, popReturn, 'final should return the value returned by pop()');
        assert.strictEqual(calls.length, 3, 'expected three internal calls (_update, collect, pop)');
        assert.strictEqual(calls[0].name, '_update', 'first call should be _update when chunk is truthy');
        assert.strictEqual(calls[0].arg, chunkObj, '_update should be called with the provided chunk');
        assert.strictEqual(calls[1].name, 'collect', 'second call should be collect');
        assert.strictEqual(calls[2].name, 'pop', 'third call should be pop');
    });

    })