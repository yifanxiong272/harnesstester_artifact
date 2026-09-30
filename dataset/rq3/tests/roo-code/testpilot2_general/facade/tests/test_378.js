let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper: try to find where the listener was stored on the workspace instance.
    // We look for an array or a direct function reference that contains/references the listener.
    function findListenerContainer(rootObj, listener) {
        const visited = new Set();

        function inspect(obj, path, depth) {
            if (!obj || typeof obj !== 'object' || visited.has(obj) || depth > 4) return null;
            visited.add(obj);

            for (const key of Object.keys(obj)) {
                try {
                    const val = obj[key];
                    if (Array.isArray(val)) {
                        for (let i = 0; i < val.length; i++) {
                            if (val[i] === listener) {
                                return { parent: obj, key, container: val, index: i, kind: 'array', path: path.concat(key).join('.') };
                            }
                        }
                    } else if (typeof val === 'function') {
                        if (val === listener) {
                            return { parent: obj, key, container: val, kind: 'function', path: path.concat(key).join('.') };
                        }
                    } else if (val && typeof val === 'object') {
                        const r = inspect(val, path.concat(key), depth + 1);
                        if (r) return r;
                    }
                } catch (e) {
                    // ignore property access errors
                }
            }
            return null;
        }

        return inspect(rootObj, [], 0);
    }

    it('should expose onDidOpenTextDocument and return a disposable with dispose()', function() {
        const WorkspaceAPI = testpilot_subject.file_0009 && testpilot_subject.file_0009.WorkspaceAPI;
        assert.equal(typeof WorkspaceAPI, 'function', 'WorkspaceAPI constructor should exist');

        // Provide a safe string path to avoid implementations that expect a path argument.
        const workspace = new WorkspaceAPI(process.cwd());
        assert.ok(workspace, 'workspace instance created');

        assert.equal(typeof workspace.onDidOpenTextDocument, 'function', 'onDidOpenTextDocument should be a function');

        const listener = function() {};
        const disp = workspace.onDidOpenTextDocument(listener);
        assert.ok(disp && (typeof disp.dispose === 'function'), 'onDidOpenTextDocument should return an object with dispose()');
        // Clean up if possible
        try { disp.dispose(); } catch (e) {}
    });

    })