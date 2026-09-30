let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Locate the decorator function under test.
    // According to the provided path, it should be here:
    const decorator = testpilot_subject.file_0002.FsSearchService.$di$dependencies[0].id;

    it('should throw if called with wrong number of arguments', function() {
        const expectedMessage = "@IServiceName-decorator can only be used to decorate a parameter";

        // 0 args
        assert.throws(() => { decorator(); }, (err) => {
            return err instanceof Error && /@IServiceName-decorator can only be used to decorate a parameter/.test(err.message);
        });

        // 1 arg
        assert.throws(() => { decorator({}); }, (err) => {
            return err instanceof Error && err.message === expectedMessage;
        });

        // 2 args
        assert.throws(() => { decorator({}, 'key'); }, (err) => {
            return err instanceof Error && err.message === expectedMessage;
        });

        // 4 args (too many)
        assert.throws(() => { decorator({}, 'key', 0, 'extra'); }, (err) => {
            return err instanceof Error && err.message === expectedMessage;
        });
    });

    })