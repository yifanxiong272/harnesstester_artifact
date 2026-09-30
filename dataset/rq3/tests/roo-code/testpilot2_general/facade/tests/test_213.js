let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Keep originals to restore after tests
    const ORIGINAL_NODE_ENV = process.env.NODE_ENV;
    const ORIGINAL_WINDOW = global.window;
    const ORIGINAL_FETCH = global.fetch;
    const ORIGINAL_IMPORT_UTILS = global.import_sourceMapUtils;
    const ORIGINAL_CONSOLE = {
        log: console.log,
        error: console.error,
        debug: console.debug
    };

    afterEach(function() {
        // restore environment
        process.env.NODE_ENV = ORIGINAL_NODE_ENV;
        global.window = ORIGINAL_WINDOW;
        global.fetch = ORIGINAL_FETCH;
        global.import_sourceMapUtils = ORIGINAL_IMPORT_UTILS;
        console.log = ORIGINAL_CONSOLE.log;
        console.error = ORIGINAL_CONSOLE.error;
        console.debug = ORIGINAL_CONSOLE.debug;
    });

    it('does nothing when NODE_ENV !== "production"', function() {
        process.env.NODE_ENV = 'development';
        // ensure window exists but has no markers
        global.window = {};
        // Call function
        const ret = testpilot_subject.file_0005.exposeSourceMapsForDebugging();
        // Should return early (undefined) and not define the utilities
        assert.strictEqual(ret, undefined);
        assert.strictEqual(typeof global.window.__applySourceMaps, 'undefined');
        assert.strictEqual(typeof global.window.__testSourceMaps, 'undefined');
        assert.strictEqual(typeof global.window.__checkSourceMap, 'undefined');
    });

    })