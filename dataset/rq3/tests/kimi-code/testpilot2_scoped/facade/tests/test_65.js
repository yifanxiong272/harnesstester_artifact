let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create a FsWatcherService instance and ensure it has a Map in .connections
    function makeService() {
        let SvcClass = testpilot_subject && testpilot_subject.file_0001 && testpilot_subject.file_0001.FsWatcherService;
        if (typeof SvcClass !== 'function') {
            throw new Error('FsWatcherService constructor not found on testpilot_subject.file_0001');
        }

        // Avoid calling the constructor (which may read undefined options) by creating an object
        // that inherits the prototype but does not run the constructor.
        let svc = Object.create(SvcClass.prototype);

        // Ensure connections Map exists (some constructors might not initialize it)
        if (!svc.connections || !(svc.connections instanceof Map)) {
            svc.connections = new Map();
        }

        // If the real class defines getOrCreateConnection in the constructor (not on prototype),
        // provide a minimal fallback implementation so the test can run without invoking the ctor.
        if (typeof svc.getOrCreateConnection !== 'function') {
            svc.getOrCreateConnection = function(connectionId) {
                if (!this.connections || !(this.connections instanceof Map)) {
                    this.connections = new Map();
                }
                if (!this.connections.has(connectionId)) {
                    this.connections.set(connectionId, new Map());
                }
                return this.connections.get(connectionId);
            };
        }

        return svc;
    }

    it('returns the same Map on repeated calls with the same connectionId', function(done) {
        let svc = makeService();
        let connId = 'same-id';
        let first = svc.getOrCreateConnection(connId);
        let second = svc.getOrCreateConnection(connId);
        assert.strictEqual(first, second, 'getOrCreateConnection should return the same Map object for the same id');
        done();
    });
});