let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    function makeManager() {
        // Try to construct normally; if constructor has side-effects or isn't present,
        // fall back to creating an object with the correct prototype.
        let ManagerCtor = testpilot_subject && testpilot_subject.file_0002 && testpilot_subject.file_0002.OutputManager;
        if (!ManagerCtor) throw new Error('OutputManager constructor not found on testpilot_subject.file_0002');
        try {
            return new ManagerCtor();
        } catch (e) {
            // If constructor throws, create an object with the prototype so we can still test the method.
            return Object.create(ManagerCtor.prototype);
        }
    }

    it('clears collections, flags and resets currentlyStreamingTs', function(done) {
        let mgr = makeManager();

        // Provide collection-like objects that implement clear()
        mgr.displayedMessages = new Set([1,2,3]);
        mgr.streamedContent = new Map([['a', 1]]);
        mgr.loggedFirstPartial = new Set(['x']);

        // Set non-default scalar values
        mgr.currentlyStreamingTs = 12345;
        mgr.completionResultStreamed = true;

        // Mock streamingState.next to observe the argument passed
        let observed = { called: 0, lastArg: null };
        mgr.streamingState = {
            next: function(arg) { observed.called += 1; observed.lastArg = arg; }
        };

        // Call the method under test
        mgr.clear();

        // Assertions: sets/maps should be cleared
        assert.strictEqual(mgr.displayedMessages.size, 0, 'displayedMessages should be cleared to size 0');
        assert.strictEqual(mgr.streamedContent.size, 0, 'streamedContent should be cleared to size 0');
        assert.strictEqual(mgr.loggedFirstPartial.size, 0, 'loggedFirstPartial should be cleared to size 0');

        // Scalars should be reset
        assert.strictEqual(mgr.currentlyStreamingTs, null, 'currentlyStreamingTs should be null');
        assert.strictEqual(mgr.completionResultStreamed, false, 'completionResultStreamed should be false');

        // streamingState.next should have been called once with the expected payload
        assert.strictEqual(observed.called, 1, 'streamingState.next should be called exactly once');
        assert.deepStrictEqual(observed.lastArg, { ts: null, isStreaming: false }, 'streamingState.next should be called with {ts:null,isStreaming:false}');

        done();
    });

    })