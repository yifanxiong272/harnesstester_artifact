let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0001.FsWatcherService.prototype.getOrCreateConnection', function() {
    let FsWatcherService;

    before(function() {
        // Ensure the class exists on the module
        FsWatcherService = testpilot_subject &&
                         testpilot_subject.file_0001 &&
                         testpilot_subject.file_0001.FsWatcherService;
        if (!FsWatcherService) {
            throw new Error('FsWatcherService class not found on testpilot_subject.file_0001');
        }
    });

    it('returns an object for a new connection id', function() {
        // Some FsWatcherService implementations expect constructor options;
        // constructing them may throw when those options are absent. To make
        // this test robust we try to construct normally and fall back to
        // creating an object with the correct prototype (skipping the ctor).
        let svc;
        try {
            svc = new FsWatcherService();
        } catch (e) {
            svc = Object.create(FsWatcherService.prototype);
            // Provide commonly-used internal containers so prototype methods
            // that expect them won't fail. Use both possible names.
            svc._connections = svc.connections = new Map();
        }

        let conn = svc.getOrCreateConnection('conn-alpha');
        assert.ok(conn !== null && typeof conn === 'object', 'expected an object to be returned');
    });

});