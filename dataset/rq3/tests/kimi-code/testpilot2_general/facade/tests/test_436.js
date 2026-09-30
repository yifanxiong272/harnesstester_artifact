let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0007.registerFsRoutes registers expected routes', function() {
        const app = {
            postCalled: false,
            getCalled: false,
            post(path, options, handler) {
                this.postCalled = true;
                this.postRoute = { path, options, handler };
            },
            get(path, options, handler) {
                this.getCalled = true;
                this.getRoute = { path, options, handler };
            }
        };
        const ix = {}; // not used for registration
        testpilot_subject.file_0007.registerFsRoutes(app, ix);

        assert.strictEqual(app.postCalled, true, 'app.post should have been called');
        assert.strictEqual(app.getCalled, true, 'app.get should have been called');
        assert.strictEqual(typeof app.postRoute.handler, 'function', 'post handler should be a function');
        assert.strictEqual(typeof app.getRoute.handler, 'function', 'get handler should be a function');

        // paths should match what the code registers
        assert.strictEqual(app.postRoute.path, '/sessions/:session_id/:tail');
        assert.strictEqual(app.getRoute.path, '/sessions/:session_id/fs/*');
    });

    })