let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // keep original globals (if any) to restore after tests
    const original_mapAction = global.mapChokidarEventToAction;
    const original_mapKind = global.mapChokidarEventToKind;

    after(function() {
        // restore globals to avoid leaking into other tests
        if (original_mapAction === undefined) delete global.mapChokidarEventToAction;
        else global.mapChokidarEventToAction = original_mapAction;

        if (original_mapKind === undefined) delete global.mapChokidarEventToKind;
        else global.mapChokidarEventToKind = original_mapKind;
    });

    it('returns early when store is disposed (no changes, no timer)', function() {
        // prepare a minimal "service" context and an entry
        const onRawChange = testpilot_subject.file_0001.FsWatcherService.prototype.onRawChange;
        const service = {
            _store: { isDisposed: true },
            // values here shouldn't matter because it should return immediately
            maxChangesPerWindow: 5,
            debounceMs: 1,
            flushWindow: function() { throw new Error('flushWindow should not be called'); }
        };

        const entry = {
            pendingRawCount: 0,
            truncated: false,
            pendingChanges: [],
            debounceTimer: undefined
        };

        // set mapping functions so that if code didn't early-return they would be defined
        global.mapChokidarEventToAction = () => 'any';
        global.mapChokidarEventToKind = () => 'k';

        onRawChange.call(service, 'sess1', entry, 'someEvent', '/abs/path');
        assert.strictEqual(entry.pendingRawCount, 0, 'pendingRawCount should remain 0 when store disposed');
        assert.strictEqual(entry.pendingChanges.length, 0, 'no pendingChanges should be added');
        assert.strictEqual(entry.debounceTimer, undefined, 'no debounceTimer should be set');
    });

    })