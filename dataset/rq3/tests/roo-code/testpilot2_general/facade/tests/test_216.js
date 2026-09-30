let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0006.WorktreeService - constructor and instance basics', function(done) {
        // Ensure the class/constructor exists
        assert.ok(testpilot_subject, 'module should be present');
        const Ctor = testpilot_subject.file_0006 && testpilot_subject.file_0006.WorktreeService;
        assert.ok(Ctor, 'WorktreeService constructor should exist');
        assert.strictEqual(typeof Ctor, 'function', 'WorktreeService should be a constructor function');

        // Create instances and verify identity/independence
        const a = new Ctor();
        const b = new Ctor();
        assert.ok(a && typeof a === 'object', 'instance a should be an object');
        assert.ok(b && typeof b === 'object', 'instance b should be an object');
        assert.ok(a instanceof Ctor, 'a should be instance of constructor');
        assert.ok(b instanceof Ctor, 'b should be instance of constructor');
        assert.notStrictEqual(a, b, 'two instances should be different objects');

        done();
    });

    })