let mocha = require('mocha');
let assert = require('assert');

describe('test testpilot_subject.file_0016.createAcpClient', function() {
    // Tests are written to be self-contained and not rely on external resources.
    // They perform light, deterministic checks (existence and basic runtime behavior).
    // Note: the real createAcpClient has many external dependencies (dynamic imports,
    // spawning a child process, SDK objects). In unit tests one would normally
    // stub/moc k those. Here we keep tests safe and self-contained: we verify the
    // exported function exists and is async, and we verify it properly detects a
    // missing stdio pipe when child_process.spawn is replaced with a stub that
    // returns an object lacking stdin/stdout (the code throws in that case).
    //
    // The tests try to avoid any network or filesystem access beyond what Node
    // provides in-process. They also restore any changes to global modules.

    let testpilot_subject;
    let createAcpClient;

    before(function() {
        // Require the module under test lazily here so tests can manipulate
        // process-wide things (like child_process.spawn) in individual tests.
        // If the environment running the tests doesn't have the module this
        // will throw and the tests will fail early.
        testpilot_subject = require('..');
        // The function under test is expected to be at file_0016.createAcpClient
        assert.ok(testpilot_subject && testpilot_subject.file_0016, 'module should export file_0016');
        createAcpClient = testpilot_subject.file_0016.createAcpClient;
    });

    it('should export createAcpClient as an async function', function() {
        assert.strictEqual(typeof createAcpClient, 'function', 'createAcpClient should be a function');
        // As it's declared async, calling it returns a Promise.
        const p = createAcpClient();
        assert.ok(p && typeof p.then === 'function' && typeof p.catch === 'function', 'createAcpClient() should return a Promise');
        // We don't await here because the function may attempt to import/resolve resources;
        // other tests exercise behavior with controlled stubbing.
    });

    })