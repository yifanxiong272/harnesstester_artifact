let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const FsWatcherService = testpilot_subject.file_0001.FsWatcherService;
    const baseProto = Object.getPrototypeOf(FsWatcherService.prototype);
    let originalBaseDispose;

    before(function() {
        // Save original base dispose so we can restore later.
        originalBaseDispose = baseProto.dispose;
    });

    after(function() {
        // Restore original base dispose after all tests.
        baseProto.dispose = originalBaseDispose;
    });

    describe('test testpilot_subject.file_0001.FsWatcherService.prototype.dispose', function() {
        let baseDisposeCalled;
        beforeEach(function() {
            // Replace the base class dispose with a spy to monitor calls.
            baseDisposeCalled = false;
            baseProto.dispose = function() {
                baseDisposeCalled = true;
            };
        });

        afterEach(function() {
            // Ensure we put back the spy (will be restored in after())
            baseProto.dispose = function() { baseDisposeCalled = true; };
        });

        it('does nothing (does not clear connections or call super) when _store.isDisposed is true', function() {
            // Create a plain object that inherits FsWatcherService.prototype so dispose can be called.
            const inst = Object.create(FsWatcherService.prototype);
            let connectionsCleared = false;
            inst._store = { isDisposed: true };
            inst.connections = {
                clear: function() { connectionsCleared = true; }
            };

            // Call dispose in the context of our instance.
            FsWatcherService.prototype.dispose.call(inst);

            // Because _store.isDisposed is true, connections.clear should NOT be called
            // and the base class dispose should NOT be called.
            assert.strictEqual(connectionsCleared, false, 'connections.clear should not have been called');
            assert.strictEqual(baseDisposeCalled, false, 'super.dispose should not have been called');
        });

            })
})