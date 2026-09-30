let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Allow some reasonable timeout in case underlying implementation is async
    this.timeout(5000);

    let WorkspaceAPI = testpilot_subject.file_0009.WorkspaceAPI;

    it('registerTextDocumentContentProvider returns a disposable with dispose() that can be called repeatedly', function() {
        // Try to construct workspace instance
        let ws;
        try {
            ws = new WorkspaceAPI();
        } catch (e) {
            // Some implementations expect a path argument — try a sensible default before failing
            try {
                ws = new WorkspaceAPI(process.cwd());
            } catch (e2) {
                // As a last resort, try __dirname
                try {
                    ws = new WorkspaceAPI(__dirname);
                } catch (e3) {
                    // If the subject cannot be constructed, fail fast with clear message
                    throw new Error('Could not construct WorkspaceAPI: ' + e + ' / ' + e2 + ' / ' + e3);
                }
            }
        }

        // Create a trivial provider
        const provider = {
            provideTextDocumentContent: function(uri) {
                return 'content-for-' + (uri && uri.toString ? uri.toString() : String(uri));
            }
        };

        // Register and verify return shape
        let disposable;
        try {
            disposable = ws.registerTextDocumentContentProvider('test-scheme', provider);
        } catch (e) {
            throw new Error('registerTextDocumentContentProvider threw unexpectedly: ' + e);
        }

        assert.ok(disposable, 'Expected register to return a disposable-like object');
        assert.strictEqual(typeof disposable.dispose, 'function', 'Disposable should have a dispose() method');

        // Calling dispose multiple times should not throw
        disposable.dispose();
        disposable.dispose();
    });

});