let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0006.createWebFetchTool', function() {
    // helper that tries several common ways to invoke the returned tool
    async function invokeTool(tool, path) {
        // If tool is a function, call it directly
        if (typeof tool === 'function') {
            return tool(path);
        }
        // If tool exposes common method names, try them
        const tryNames = ['fetch', 'request', 'get', 'call'];
        for (let name of tryNames) {
            if (tool && typeof tool[name] === 'function') {
                return tool[name](path);
            }
        }
        // If tool is an object that looks like a simple wrapper with .run or .do
        if (tool && typeof tool.run === 'function') {
            return tool.run(path);
        }
        if (tool && typeof tool.do === 'function') {
            return tool.do(path);
        }
        // If none matched, just return the tool (so tests can assert something)
        return tool;
    }

    it('should create a tool (function or object) without throwing', function() {
        // Basic creation should not throw for empty options or undefined
        assert.doesNotThrow(() => {
            let t1 = testpilot_subject.file_0006.createWebFetchTool({});
            let t2 = testpilot_subject.file_0006.createWebFetchTool({}); // repeated call
            // returned tool should be function or object
            assert.ok(t1 && (typeof t1 === 'function' || typeof t1 === 'object'));
            assert.ok(t2 && (typeof t2 === 'function' || typeof t2 === 'object'));
        });
    });

    })