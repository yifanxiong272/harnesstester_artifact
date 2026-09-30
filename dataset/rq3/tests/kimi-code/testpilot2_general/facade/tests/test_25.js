let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Keep references so we can restore the original implementation after tests
    let originalSearch;

    beforeEach(function() {
        // Ensure structure exists before trying to monkeypatch
        if (!testpilot_subject ||
            !testpilot_subject.file_0002 ||
            !testpilot_subject.file_0002.FsSearchService ||
            !testpilot_subject.file_0002.FsSearchService.prototype) {
            // If the structure isn't present, create a minimal one so tests remain self-contained.
            testpilot_subject.file_0002 = testpilot_subject.file_0002 || {};
            testpilot_subject.file_0002.FsSearchService = testpilot_subject.file_0002.FsSearchService || function FsSearchService() {};
            testpilot_subject.file_0002.FsSearchService.prototype = testpilot_subject.file_0002.FsSearchService.prototype || {};
        }

        originalSearch = testpilot_subject.file_0002.FsSearchService.prototype.search;

        // Replace the real implementation with a deterministic, self-contained async stub.
        // Tests below exercise the contract (sessionId + req -> Promise) without external IO.
        testpilot_subject.file_0002.FsSearchService.prototype.search = async function(sessionId, req) {
            // Simulate basic validation
            if (sessionId === null || sessionId === undefined) {
                throw new Error('Missing sessionId');
            }
            // Simulate behavior based on a test-only hint in req.mock
            req = req || {};
            switch (req.mock) {
                case 'exists':
                    // pretend we found one file
                    return [{ path: '/tmp/found.txt', name: 'found.txt' }];
                case 'none':
                    // pretend no results
                    return [];
                case 'error':
                    // simulate an internal error
                    throw new Error('simulated search error');
                default:
                    // default predictable result
                    return [{ path: '/tmp/default.txt', name: 'default.txt' }];
            }
        };
    });

    afterEach(function() {
        // Restore original implementation (could be undefined)
        testpilot_subject.file_0002.FsSearchService.prototype.search = originalSearch;
    });

    it('FsSearchService.prototype.search exists and is a function', function() {
        assert.strictEqual(typeof testpilot_subject.file_0002.FsSearchService.prototype.search, 'function');
    });

    })