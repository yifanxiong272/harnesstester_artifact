let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0004.FsService.prototype.listMany - returns results and truncated_paths appropriately', async function() {
        // Arrange
        const FsService = testpilot_subject.file_0004.FsService;
        const svc = new FsService();

        // stub sessions.get to simulate a valid session
        svc.sessions = {
            get: async (sessionId) => {
                if (sessionId !== 'valid-session') throw new Error('unexpected session');
                return; // success
            }
        };

        // stub list to return different behaviors per path
        svc.list = async (sessionId, opts) => {
            // sanity check that sessionId is forwarded
            if (sessionId !== 'valid-session') throw new Error('bad session id forwarded');
            const p = opts.path;
            return {
                items: [`item-for-${p}`],
                truncated: p === 'path-truncated' // mark this path as truncated
            };
        };

        // Act
        const out = await svc.listMany('valid-session', {
            paths: ['path-a', 'path-truncated'],
            depth: 1,
            limit: 100,
            show_hidden: false,
            follow_gitignore: false,
            exclude_globs: [],
            sort: null,
            include_git_status: false
        });

        // Assert
        assert.ok(out && typeof out === 'object', 'output should be an object');
        // results should contain both paths
        assert.ok(out.results);
        assert.deepStrictEqual(out.results['path-a'], ['item-for-path-a']);
        assert.deepStrictEqual(out.results['path-truncated'], ['item-for-path-truncated']);
        // truncated_paths should include only the truncated one
        assert.ok(Array.isArray(out.truncated_paths), 'truncated_paths should be present and an array');
        assert.strictEqual(out.truncated_paths.length, 1);
        assert.strictEqual(out.truncated_paths[0], 'path-truncated');
        // no partial_errors expected
        assert.strictEqual(out.partial_errors, undefined);
    });

    })