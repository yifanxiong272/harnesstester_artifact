let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.FsWatcherService.prototype.createSessionEntry', function() {
    // Keep original SessionEntry (if any) to restore after tests
    const file0001 = testpilot_subject.file_0001 || {};
    const OrigSessionEntry = file0001.SessionEntry;

    afterEach(function() {
        // restore original if it existed
        if (OrigSessionEntry !== undefined) {
            file0001.SessionEntry = OrigSessionEntry;
        } else if (file0001.SessionEntry !== undefined) {
            // if test replaced it and originally it wasn't defined, delete it
            delete file0001.SessionEntry;
        }
    });

    it('registers "all" and "error" handlers on watcher and returns the created SessionEntry instance', function() {
        // Prepare a fake watcher that records handlers registered via .on()
        const handlers = {};
        const onCalls = [];
        const fakeWatcher = {
            on: function(eventName, cb) {
                onCalls.push(eventName);
                handlers[eventName] = cb;
            }
        };

        // Fake SessionEntry constructor so we can inspect the created object
        function FakeSessionEntry(sessionId, watcher, cwd, logger) {
            this._constructed = true;
            this.sessionId = sessionId;
            this.watcher = watcher;
            this.cwd = cwd;
            this.logger = logger;
        }

        // Monkeypatch SessionEntry in the module under test (if the module exposes it)
        file0001.SessionEntry = FakeSessionEntry;

        // Prepare the 'this' context for calling the prototype method
        const capturedOnRawChange = [];
        const fakeThis = {
            makeWatcher: function() { return fakeWatcher; },
            logger: { warn: function() {} },
            onRawChange: function() {
                capturedOnRawChange.push(Array.from(arguments));
            }
        };

        const svcProto = testpilot_subject.file_0001.FsWatcherService.prototype;
        const sessionId = 's-123';
        const cwd = '/some/cwd';

        const entry = svcProto.createSessionEntry.call(fakeThis, sessionId, cwd);

        // Ensure we got an object back and it has the expected properties
        assert.ok(entry && typeof entry === 'object', 'returned entry is an object');
        assert.strictEqual(entry.sessionId, sessionId);
        assert.strictEqual(entry.watcher, fakeWatcher);
        assert.strictEqual(entry.cwd, cwd);
        assert.strictEqual(entry.logger, fakeThis.logger);

        // Ensure the watcher.on has been called for both 'all' and 'error'
        assert.ok(onCalls.indexOf('all') !== -1, 'registered handler for "all" event');
        assert.ok(onCalls.indexOf('error') !== -1, 'registered handler for "error" event');

        // Ensure the handlers are stored
        assert.strictEqual(typeof handlers.all, 'function', '"all" handler is a function');
        assert.strictEqual(typeof handlers.error, 'function', '"error" handler is a function');
    });

    })