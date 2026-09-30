let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create a minimal fake "program" that registerCompletionCli can operate on.
    function makeProgramStub() {
        return {
            _commands: [],
            command(name) {
                const cmd = {
                    name,
                    descriptionCalledWith: null,
                    addHelpTextCalledWith: null,
                    addOptionArg: null,
                    optionsCalled: [],
                    actionHandler: null,
                    description(text) {
                        this.descriptionCalledWith = text;
                        return this;
                    },
                    addHelpText(position, fn) {
                        this.addHelpTextCalledWith = { position, fn };
                        return this;
                    },
                    // capture the Option object (commander.Option) that is passed in
                    addOption(opt) {
                        this.addOptionArg = opt;
                        return this;
                    },
                    // capture arbitrary option(...) calls (store args arrays)
                    option(...args) {
                        this.optionsCalled.push(args);
                        return this;
                    },
                    action(fn) {
                        this.actionHandler = fn;
                        return this;
                    }
                };
                this._commands.push(cmd);
                return cmd;
            },
            // some code paths may call program.name(); provide a harmless value
            name() { return "testprog"; }
        };
    }

    it('registerCompletionCli registers a "completion" command with description', function() {
        const program = makeProgramStub();
        const { file_0015 } = testpilot_subject;
        assert.ok(file_0015 && typeof file_0015.registerCompletionCli === 'function', 'registerCompletionCli must exist');

        // Call the function to register the command on our fake program
        file_0015.registerCompletionCli(program);

        // Ensure exactly one command was added and it's named "completion"
        assert.strictEqual(program._commands.length, 1, 'one command should be registered');
        const cmd = program._commands[0];
        assert.strictEqual(cmd.name, 'completion', 'registered command must be named "completion"');

        // Ensure the description was set and contains the expected short text
        assert.ok(typeof cmd.descriptionCalledWith === 'string', 'description should be provided as string');
        assert.ok(cmd.descriptionCalledWith.indexOf('Generate shell completion script') !== -1,
            'description should mention "Generate shell completion script"');
    });

    })