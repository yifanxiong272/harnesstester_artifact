let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0004.FsService', function() {
    // Helper: get FsService constructor/function
    const FsService = (testpilot_subject && testpilot_subject.file_0004)
        ? testpilot_subject.file_0004.FsService
        : undefined;

    it('module should expose file_0004.FsService', function() {
        assert.ok(FsService !== undefined, 'FsService is not exported at testpilot_subject.file_0004.FsService');
        assert.ok(typeof FsService === 'function', 'FsService should be a function or constructor');
    });

    // Helper that tries to construct or call the service safely
    function createInstance(sessions) {
        // Try to construct with new; if that fails try calling as function.
        try {
            return new FsService(sessions);
        } catch (e) {
            // If FsService is not constructable, try calling it as plain function.
            try {
                return FsService(sessions);
            } catch (e2) {
                // Re-throw original for clearer diagnostics
                throw e;
            }
        }
    }

    })