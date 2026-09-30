let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create a mock Express-like app that records registrations.
    function createMockApp() {
        const calls = [];
        function record(method, args) {
            // Normalize arguments into an array
            const argsArray = Array.prototype.slice.call(args);
            calls.push({ method: method, args: argsArray });
            // Return something chainable for route().get().post() style if needed
            return record;
        }

        const app = {
            // common HTTP verbs
            get: function() { return record('get', arguments); },
            post: function() { return record('post', arguments); },
            put: function() { return record('put', arguments); },
            delete: function() { return record('delete', arguments); },
            patch: function() { return record('patch', arguments); },
            all: function() { return record('all', arguments); },
            use: function() { return record('use', arguments); },
            // route(path).get(handler).post(handler) style
            route: function(path) {
                return {
                    get: function() { return record('get', [path].concat(Array.prototype.slice.call(arguments))); },
                    post: function() { return record('post', [path].concat(Array.prototype.slice.call(arguments))); },
                    put: function() { return record('put', [path].concat(Array.prototype.slice.call(arguments))); },
                    delete: function() { return record('delete', [path].concat(Array.prototype.slice.call(arguments))); },
                    patch: function() { return record('patch', [path].concat(Array.prototype.slice.call(arguments))); }
                };
            },
            // expose recorded calls for assertions
            _getCalls: function() { return calls; }
        };
        return app;
    }

    // Helper to determine if an item is a function (or array of functions)
    function isFunctionOrArrayOfFunctions(x) {
        if (typeof x === 'function') return true;
        if (Array.isArray(x)) return x.every(isFunctionOrArrayOfFunctions);
        return false;
    }

    it('registers one or more routes with path and handler functions', function() {
        const app = createMockApp();
        const ix = {}; // minimal ix mock; registerFsRoutes should not depend on external resources for route registration
        // Call the function under test
        if (!testpilot_subject || !testpilot_subject.file_0007 || typeof testpilot_subject.file_0007.registerFsRoutes !== 'function') {
            // If the function is missing, fail the test with a clear message.
            assert.fail('testpilot_subject.file_0007.registerFsRoutes is not a function');
        }
        testpilot_subject.file_0007.registerFsRoutes(app, ix);

        const calls = app._getCalls();
        // Must have registered at least one route
        assert(calls.length > 0, 'Expected at least one route registration on the app');

        // Each call should contain at least a path (string or RegExp) and at least one function handler (or middleware)
        calls.forEach(call => {
            // Many Express registrations have signature (path, ...handlers) or (...handlers) (if mounting at root)
            // If the first arg is a string or RegExp, treat it as path
            const args = call.args;
            assert(Array.isArray(args), 'call.args should be an array');

            // If args length is 0, that's unexpected
            assert(args.length > 0, `Registration for method ${call.method} had no arguments`);

            // Accept string or RegExp as path or allow registrations that only provide handlers (no explicit path)
            const firstArg = args[0];
            const hasPath = (typeof firstArg === 'string') || (firstArg instanceof RegExp);

            // Determine list of handler candidates (everything after path if path exists, otherwise all args)
            const handlerCandidates = hasPath ? args.slice(1) : args.slice(0);

            // There should be at least one handler candidate and at least one of them should be a function (or array of functions)
            assert(handlerCandidates.length > 0, `Registration for method ${call.method} had no handler arguments`);
            const hasFunctionHandler = handlerCandidates.some(isFunctionOrArrayOfFunctions);
            assert(hasFunctionHandler, `No function handler found for route registration on method ${call.method}`);
        });
    });

    })