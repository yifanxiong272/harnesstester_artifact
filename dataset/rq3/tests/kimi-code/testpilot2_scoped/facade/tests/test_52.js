let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.FsWatcherService.prototype.bindSessionCwd', function() {
        it('creates and stores a session entry when none exists', function() {
            // Create a "bare" instance backed by the prototype so we don't invoke constructor
            const service = Object.create(testpilot_subject.file_0001.FsWatcherService.prototype);
            service.sessions = new Map();

            // spy for createSessionEntry
            let createCalled = false;
            let createArgs = null;
            const fakeEntry = { cwd: '/some/path' };
            service.createSessionEntry = function(sessionId, cwd) {
                createCalled = true;
                createArgs = [sessionId, cwd];
                return fakeEntry;
            };

            // logger should not be called in this path
            service.logger = {
                debug: function() { throw new Error('logger.debug should not be called when creating entry'); }
            };

            service.bindSessionCwd('session-1', '/some/path');

            assert.strictEqual(createCalled, true, 'createSessionEntry should be called');
            assert.deepStrictEqual(createArgs, ['session-1', '/some/path']);
            assert.strictEqual(service.sessions.get('session-1'), fakeEntry, 'the returned entry should be stored in sessions map');
        });

            })
})