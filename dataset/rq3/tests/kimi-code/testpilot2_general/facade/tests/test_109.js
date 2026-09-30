let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Save originals so we can restore later
    let originalSetInterval = global.setInterval;
    let originalClearInterval = global.clearInterval;

    // Fake timer storage
    let fakeNextId;
    let fakeCallbacks;
    let fakeSetIntervalCallCount;
    let fakeClearIntervalCallCount;

    beforeEach(function() {
        // initialize fake timer state
        fakeNextId = 1;
        fakeCallbacks = {}; // id -> callback
        fakeSetIntervalCallCount = 0;
        fakeClearIntervalCallCount = 0;

        // Replace global setInterval / clearInterval with fakes
        global.setInterval = function(cb, ms) {
            fakeSetIntervalCallCount++;
            let id = fakeNextId++;
            fakeCallbacks[id] = cb;
            return id;
        };
        global.clearInterval = function(id) {
            fakeClearIntervalCallCount++;
            delete fakeCallbacks[id];
        };
    });

    afterEach(function() {
        // Restore originals
        global.setInterval = originalSetInterval;
        global.clearInterval = originalClearInterval;
    });

    it('calls stopStreamingProgressTimer and does not set timer when not streaming', function() {
        let inst = Object.create(testpilot_subject.file_0003.ToolCallComponent.prototype);
        let stopCalled = false;
        inst.isStreamingEditPreview = function() { return false; };
        inst.stopStreamingProgressTimer = function() { stopCalled = true; };
        // ensure no ui present and no existing timer
        inst.ui = undefined;
        inst.streamingProgressTimer = undefined;

        inst.syncStreamingProgressTimer();

        assert.strictEqual(stopCalled, true, 'stopStreamingProgressTimer should be called when not streaming');
        assert.strictEqual(inst.streamingProgressTimer, undefined, 'streamingProgressTimer must remain undefined');
        assert.strictEqual(fakeSetIntervalCallCount, 0, 'setInterval must not be called');
    });

    })