let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0001.FsWatcherService.prototype.addPaths', function() {

    // Grab the raw addPaths function from the prototype so we can call it with a custom "this".
    const addPaths = testpilot_subject.file_0001.FsWatcherService.prototype.addPaths;

    // Helper to produce minimal service-like objects satisfying the internal expectations of addPaths.
    function makeSvc(opts = {}) {
        const svc = {};
        svc._store = { isDisposed: !!opts.disposed };
        svc.sessions = new Map();
        svc.maxPathsPerConnection = (typeof opts.max === 'number') ? opts.max : 1000;

        // allow customizing the reported count for a connection
        const baseCount = (typeof opts.count === 'number') ? opts.count : 0;
        svc.countForConnection = function(connectionId) {
            // return a fixed base count unless opts.countFunc provided
            if (typeof opts.countFunc === 'function') return opts.countFunc(connectionId);
            return baseCount;
        };

        // getOrCreateConnection uses an internal map of connectionId -> Map(sessionId->sessionMap)
        svc._conns = new Map();
        svc.getOrCreateConnection = function(connectionId) {
            let m = svc._conns.get(connectionId);
            if (!m) {
                m = new Map();
                svc._conns.set(connectionId, m);
            }
            return m;
        };

        // default createSessionEntry implementation; tests can replace sessions map directly to avoid reliance on deriveSharedCwd
        svc.createSessionEntry = function(sessionId, cwd) {
            return {
                pathRefs: {
                    acquire: function(abs) {
                        // return a simple opaque object representing a "ref"
                        return { acquired: abs };
                    }
                },
                connectionPathRefs: new Map()
            };
        };

        return svc;
    }

    it('should return [] immediately when the store is disposed', function(done) {
        const svc = makeSvc({ disposed: true });
        const res = addPaths.call(svc, 'sessionA', 'connA', ['/path/one']);
        assert.deepStrictEqual(res, []);
        done();
    });

    })