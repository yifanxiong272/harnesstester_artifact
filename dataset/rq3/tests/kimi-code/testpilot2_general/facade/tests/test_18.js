let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const targetPath = ['file_0002','FsSearchService','None'];

    function getTarget() {
        // navigate safely through the path to the target object
        let obj = testpilot_subject;
        for (const p of targetPath) {
            if (obj == null) return undefined;
            obj = obj[p];
        }
        return obj;
    }

    it('test testpilot_subject.file_0002.FsSearchService.None.dispose exists and is a function', function() {
        const inst = getTarget();
        assert.notStrictEqual(inst, undefined, 'target instance should exist');
        assert.ok(Object.prototype.hasOwnProperty.call(inst, 'dispose'), 'dispose should be own property');
        assert.strictEqual(typeof inst.dispose, 'function', 'dispose should be a function');
    });

    })