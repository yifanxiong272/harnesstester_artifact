let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0006.MultiPointStrategy.prototype.determineMessageCachePoints', function() {

    // Helper to create a fresh strategy-like object with needed methods
    function makeStrategy(messages, previousCachePointPlacements) {
        const proto = testpilot_subject.file_0006.MultiPointStrategy.prototype;
        const strategy = Object.create(proto);

        // config with messages and optionally previous placements
        strategy.config = {
            messages: messages,
            previousCachePointPlacements: previousCachePointPlacements
        };

        // simple token estimation: each message is expected to be an object {tokens: number}
        strategy.estimateTokenCount = function(msg) {
            return (msg && typeof msg.tokens === 'number') ? msg.tokens : 0;
        };

        // findOptimalPlacementForRange: find first index in [start..end] where cumulative tokens (from start) >= minTokens
        strategy.findOptimalPlacementForRange = function(start, end, minTokens) {
            let cum = 0;
            for (let i = start; i <= end; i++) {
                cum += this.estimateTokenCount(this.config.messages[i]);
                if (cum >= minTokens) {
                    return { index: i };
                }
            }
            return null;
        };

        return strategy;
    }

    it('returns empty array when there is <= 1 message', function(done) {
        const messages = [{ tokens: 5 }]; // length == 1
        const strategy = makeStrategy(messages, undefined);
        const result = strategy.determineMessageCachePoints(2, 3);
        assert.deepStrictEqual(result, []);
        done();
    });

    })