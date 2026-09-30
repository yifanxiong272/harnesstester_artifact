let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('calls removePaths for each session and deletes the connection entry', function() {
        // Create an object that inherits the prototype without running constructor
        const svc = Object.create(testpilot_subject.file_0001.FsWatcherService.prototype);

        // Prepare connections map: connectionId -> Map(sessionId -> refsMap)
        svc.connections = new Map();
        const refs1 = new Map([['p1', 1], ['p2', 2]]);
        const refs2 = new Map([['p3', 3]]);
        svc.connections.set('conn1', new Map([['s1', refs1], ['s2', refs2]]));

        // Spy on removePaths calls
        const calls = [];
        svc.removePaths = function(sessionId, connectionId, paths) {
            calls.push({ sessionId, connectionId, paths });
        };

        // Invoke
        svc.forgetConnection('conn1');

        // Assertions: removePaths called once per session with correct args
        assert.strictEqual(calls.length, 2, 'removePaths should be called for each session');
        const bySession = {};
        calls.forEach(c => bySession[c.sessionId] = c);

        assert.ok(bySession['s1'], 's1 should have been processed');
        assert.ok(bySession['s2'], 's2 should have been processed');

        // paths should match keys from the refs maps (order preserved by Map)
        assert.deepStrictEqual(bySession['s1'].paths, ['p1', 'p2']);
        assert.deepStrictEqual(bySession['s2'].paths, ['p3']);

        // Connection entry should be removed
        assert.strictEqual(svc.connections.has('conn1'), false, 'connection should be deleted');
    });

    })