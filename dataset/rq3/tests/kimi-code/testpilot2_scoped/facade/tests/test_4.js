let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const svcPath = testpilot_subject &&
                    testpilot_subject.file_0001 &&
                    testpilot_subject.file_0001.FsWatcherService &&
                    testpilot_subject.file_0001.FsWatcherService.$di$dependencies &&
                    testpilot_subject.file_0001.FsWatcherService.$di$dependencies[0];

    assert.ok(svcPath, 'expected testpilot_subject.file_0001.FsWatcherService.$di$dependencies[0] to exist');

    const serviceDecorator = svcPath.id;
    assert.equal(typeof serviceDecorator, 'function', 'expected .id to be a function');

    it('throws if called with argument count !== 3', function() {
        // Cases with wrong number of arguments
        const badArgs = [
            [],           // 0 args
            [1],          // 1 arg
            [1,2],        // 2 args
            [1,2,3,4],    // 4 args
            [1,2,3,4,5]   // 5 args
        ];
        badArgs.forEach(args => {
            assert.throws(
                () => { serviceDecorator.apply(null, args); },
                /@IServiceName-decorator can only be used to decorate a parameter/,
                `expected throw for args length ${args.length}`
            );
        });
    });

    })