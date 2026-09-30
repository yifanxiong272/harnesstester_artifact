import { derefJsonSchema, normalizeKimiToolSchema } from '#/providers/kimi-schema';
import { describe, expect, it, vi } from 'vitest';

describe('derefJsonSchema', () => {
  it('returns schema unchanged when there are no $ref', () => {
    const schema = {
      type: 'object',
      properties: {
        name: { type: 'string' },
        age: { type: 'number' },
      },
      required: ['name'],
    };

    const result = derefJsonSchema(schema);

    expect(result).toEqual({
      type: 'object',
      properties: {
        name: { type: 'string' },
        age: { type: 'number' },
      },
      required: ['name'],
    });
  });

  it('resolves a simple $ref from $defs', () => {
    const schema = {
      type: 'object',
      properties: {
        address: { $ref: '#/$defs/Address' },
      },
      $defs: {
        Address: {
          type: 'object',
          properties: {
            street: { type: 'string' },
            city: { type: 'string' },
          },
        },
      },
    };

    const result = derefJsonSchema(schema);

    expect(result).toEqual({
      type: 'object',
      properties: {
        address: {
          type: 'object',
          properties: {
            street: { type: 'string' },
            city: { type: 'string' },
          },
        },
      },
    });
    // $defs should be removed from the result.
    expect(result['$defs']).toBeUndefined();
  });

  it('preserves sibling keywords alongside $ref (e.g. description)', () => {
    const schema = {
      type: 'object',
      properties: {
        user: {
          $ref: '#/$defs/User',
          description: 'Custom description on the ref site',
        },
      },
      $defs: {
        User: {
          type: 'object',
          properties: {
            name: { type: 'string' },
          },
        },
      },
    };

    const result = derefJsonSchema(schema);

    const user = (result['properties'] as Record<string, Record<string, unknown>>)['user']!;
    // Resolved definition fields are present.
    expect(user['type']).toBe('object');
    expect(user['properties']).toEqual({ name: { type: 'string' } });
    // Local sibling "description" is preserved.
    expect(user['description']).toBe('Custom description on the ref site');
  });

  it('local sibling fields override same-named fields from $defs', () => {
    const schema = {
      type: 'object',
      properties: {
        field: {
          $ref: '#/$defs/Widget',
          // Local override must win over the def's description.
          description: 'local override wins',
        },
      },
      $defs: {
        Widget: {
          type: 'string',
          description: 'description from $defs',
          default: 'hello',
        },
      },
    };

    const result = derefJsonSchema(schema);

    const field = (result['properties'] as Record<string, Record<string, unknown>>)['field']!;
    expect(field['type']).toBe('string');
    // Local sibling wins.
    expect(field['description']).toBe('local override wins');
    // Non-overlapping def fields still flow through.
    expect(field['default']).toBe('hello');
  });

  it('preserves sibling $ref keywords that themselves contain $ref (recursively resolved)', () => {
    const schema = {
      type: 'object',
      properties: {
        entry: {
          $ref: '#/$defs/Wrapper',
          extra: { $ref: '#/$defs/Inner' },
        },
      },
      $defs: {
        Wrapper: {
          type: 'object',
          properties: { a: { type: 'number' } },
        },
        Inner: {
          type: 'object',
          properties: { b: { type: 'boolean' } },
        },
      },
    };

    const result = derefJsonSchema(schema);

    const entry = (result['properties'] as Record<string, Record<string, unknown>>)['entry']!;
    expect(entry['type']).toBe('object');
    expect(entry['properties']).toEqual({ a: { type: 'number' } });
    // Sibling `extra` must have been recursively resolved (not left as a $ref).
    expect(entry['extra']).toEqual({
      type: 'object',
      properties: { b: { type: 'boolean' } },
    });
  });

  it('preserves $defs when cyclic refs remain unresolved', () => {
    // A references B, B references A — classic cycle. resolveNode() leaves
    // a `#/$defs/...` pointer on at least one side; the validator will need
    // $defs to stay around to resolve those dangling pointers.
    const schema = {
      type: 'object',
      properties: {
        a: { $ref: '#/$defs/A' },
      },
      $defs: {
        A: {
          type: 'object',
          properties: {
            next: { $ref: '#/$defs/B' },
          },
        },
        B: {
          type: 'object',
          properties: {
            back: { $ref: '#/$defs/A' },
          },
        },
      },
    };

    const result = derefJsonSchema(schema);

    expect(result).toMatchObject({
      $defs: {
        A: expect.any(Object),
        B: expect.any(Object),
      },
    });

    // Walk the result and confirm at least one remaining $ref points at $defs —
    // i.e. the output is internally consistent, not dangling.
    const jsonText = JSON.stringify(result);
    expect(jsonText).toContain('"$ref":"#/$defs/');
  });

  it('still deletes $defs when there are no cyclic refs', () => {
    // Sanity: a non-cyclic schema with $defs should have its $defs removed
    // after dereferencing (existing behavior must not regress).
    const schema = {
      type: 'object',
      properties: {
        name: { $ref: '#/$defs/Name' },
      },
      $defs: {
        Name: { type: 'string' },
      },
    };

    const result = derefJsonSchema(schema);
    expect(result['$defs']).toBeUndefined();
    expect(result['properties']).toEqual({ name: { type: 'string' } });
  });

  it('resolves nested $ref from $defs', () => {
    const schema = {
      type: 'object',
      properties: {
        person: { $ref: '#/$defs/Person' },
      },
      $defs: {
        Person: {
          type: 'object',
          properties: {
            name: { type: 'string' },
            address: { $ref: '#/$defs/Address' },
          },
        },
        Address: {
          type: 'object',
          properties: {
            street: { type: 'string' },
            city: { type: 'string' },
          },
        },
      },
    };

    const result = derefJsonSchema(schema);

    expect(result).toEqual({
      type: 'object',
      properties: {
        person: {
          type: 'object',
          properties: {
            name: { type: 'string' },
            address: {
              type: 'object',
              properties: {
                street: { type: 'string' },
                city: { type: 'string' },
              },
            },
          },
        },
      },
    });
    expect(result['$defs']).toBeUndefined();
  });

  it('resolves a local $ref from draft-7 definitions', () => {
    const schema = {
      type: 'object',
      properties: {
        mode: { $ref: '#/definitions/Mode' },
      },
      definitions: {
        Mode: { enum: ['fast', 'safe'] },
      },
    };

    const result = derefJsonSchema(schema);

    expect(result).toEqual({
      type: 'object',
      properties: {
        mode: { enum: ['fast', 'safe'] },
      },
    });
    expect(result['definitions']).toBeUndefined();
  });
});

describe('normalizeKimiToolSchema', () => {
  it.each([
    {
      name: 'string enum',
      property: { enum: ['none', 'start', 'end'] },
      expectedType: 'string',
    },
    {
      name: 'integer enum',
      property: { enum: [1, 2, 3] },
      expectedType: 'integer',
    },
    {
      name: 'mixed integer and float enum collapses to number',
      property: { enum: [1.5, 2] },
      expectedType: 'number',
    },
    {
      name: 'boolean enum',
      property: { enum: [true, false] },
      expectedType: 'boolean',
    },
    {
      name: 'single boolean enum',
      property: { enum: [true] },
      expectedType: 'boolean',
    },
    {
      name: 'null-only enum',
      property: { enum: [null] },
      expectedType: 'null',
    },
    {
      name: 'string const',
      property: { const: 'event' },
      expectedType: 'string',
    },
    {
      name: 'integer const',
      property: { const: 3 },
      expectedType: 'integer',
    },
    {
      name: 'number const',
      property: { const: 1.25 },
      expectedType: 'number',
    },
    {
      name: 'boolean const',
      property: { const: true },
      expectedType: 'boolean',
    },
  ])(
    'infers $name property type without mutating the original schema',
    ({ property, expectedType }) => {
      const schema = {
        type: 'object',
        properties: {
          target: property,
        },
      };
      const original = structuredClone(schema);

      const result = normalizeKimiToolSchema(schema);

      expect(result).toEqual({
        type: 'object',
        properties: {
          target: { ...property, type: expectedType },
        },
      });
      expect(schema).toEqual(original);
      expect(result).not.toBe(schema);
    },
  );

  it('leaves explicitly typed enum properties untouched', () => {
    const schema = {
      type: 'object',
      properties: {
        explicit: { type: 'string', enum: ['already-typed'] },
      },
    };

    const result = normalizeKimiToolSchema(schema);

    expect(result).toEqual({
      type: 'object',
      properties: {
        explicit: { type: 'string', enum: ['already-typed'] },
      },
    });
  });

  it('repairs mismatched explicit type when enum values contradict it', () => {
    // Regression: Xcode MCP (xcrun mcpbridge) Version 26.5 (17F42) and later
    // generates schemas where String-backed Swift enums incorrectly carry
    // type: 'object' alongside string enum values. We overwrite the contradictory
    // type and strip object/array structure keys that are no longer relevant.
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const schema = {
      type: 'object',
      properties: {
        operation: {
          type: 'object',
          enum: ['move', 'copy'],
          properties: {
            rawValue: { type: 'string' },
          },
          required: ['rawValue'],
        },
      },
    };

    try {
      const result = normalizeKimiToolSchema(schema);

      expect(result).toEqual({
        type: 'object',
        properties: {
          operation: {
            type: 'string',
            enum: ['move', 'copy'],
          },
        },
      });
      expect(warnSpy).not.toHaveBeenCalled();
    } finally {
      warnSpy.mockRestore();
    }
  });

  it('repairs mismatched explicit type when const value contradicts it', () => {
    const schema = {
      type: 'object',
      properties: {
        mode: { type: 'object', const: 'fast' },
      },
    };

    const result = normalizeKimiToolSchema(schema);

    expect(result).toEqual({
      type: 'object',
      properties: {
        mode: { type: 'string', const: 'fast' },
      },
    });
  });

  it('leaves mixed enum types with explicit type untouched to surface provider error', () => {
    const schema = {
      type: 'object',
      properties: {
        bad: { type: 'object', enum: ['move', 1] },
      },
    };

    // inferTypeFromValues throws for mixed types; we should not overwrite the
    // explicit type so the downstream provider validator can report the issue.
    expect(() => normalizeKimiToolSchema(schema)).not.toThrow();
    const result = normalizeKimiToolSchema(schema);
    expect(result).toEqual({
      type: 'object',
      properties: {
        bad: { type: 'object', enum: ['move', 1] },
      },
    });
  });

  it('infers object and array property types from container enum/const values', () => {
    const schema = {
      type: 'object',
      properties: {
        object_enum: { enum: [{ a: 1 }, { a: 2 }] },
        array_enum: { enum: [[1, 2], [3]] },
        object_const: { const: { kind: 'default' } },
        array_const: { const: [] },
      },
    };

    const result = normalizeKimiToolSchema(schema);

    expect(result).toEqual({
      type: 'object',
      properties: {
        object_enum: { enum: [{ a: 1 }, { a: 2 }], type: 'object' },
        array_enum: { enum: [[1, 2], [3]], type: 'array' },
        object_const: { const: { kind: 'default' }, type: 'object' },
        array_const: { const: [], type: 'array' },
      },
    });
  });

  it('fails fast for mixed enum types instead of emitting an unsupported Kimi type array', () => {
    const schema = {
      type: 'object',
      properties: {
        mixedEnum: { enum: ['auto', 1] },
      },
    };
    const original = structuredClone(schema);

    expect(() => normalizeKimiToolSchema(schema)).toThrow(
      /Mixed JSON Schema enum or const types are not supported/,
    );
    expect(schema).toEqual(original);
  });

  it('infers object and array structure recursively', () => {
    const schema = {
      properties: {
        filters: {
          properties: {
            language: { enum: ['typescript', 'python'] },
            tags: {
              items: { enum: ['bug', 'feature'] },
            },
          },
          required: ['language'],
        },
        edits: {
          items: {
            properties: {
              path: { const: 'src/index.ts' },
              lineNumbers: {
                items: { const: 42 },
              },
            },
          },
        },
      },
    };

    const result = normalizeKimiToolSchema(schema);

    expect(result).toEqual({
      properties: {
        filters: {
          type: 'object',
          properties: {
            language: { enum: ['typescript', 'python'], type: 'string' },
            tags: {
              type: 'array',
              items: { enum: ['bug', 'feature'], type: 'string' },
            },
          },
          required: ['language'],
        },
        edits: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              path: { const: 'src/index.ts', type: 'string' },
              lineNumbers: {
                type: 'array',
                items: { const: 42, type: 'integer' },
              },
            },
          },
        },
      },
    });
  });

  it('uses structural hints before falling back to string on nested typeless schemas', () => {
    const schema = {
      properties: {
        path: { pattern: '^src/' },
        limit: { minimum: 1 },
        freeform: { description: 'Unconstrained external MCP field.' },
        empty: {},
      },
    };

    const result = normalizeKimiToolSchema(schema);

    expect(result).toEqual({
      properties: {
        path: { pattern: '^src/', type: 'string' },
        limit: { minimum: 1, type: 'number' },
        freeform: { description: 'Unconstrained external MCP field.', type: 'string' },
        empty: { type: 'string' },
      },
    });
  });

  it('does not default the root schema itself to string', () => {
    expect(normalizeKimiToolSchema({})).toEqual({});
  });

  it('dereferences and normalizes local definition buckets', () => {
    const schema = {
      type: 'object',
      properties: {
        mode: { $ref: '#/$defs/Mode' },
        retryCount: { $ref: '#/definitions/RetryCount' },
      },
      $defs: {
        Mode: { enum: ['fast', 'safe'] },
      },
      definitions: {
        RetryCount: { const: 3 },
      },
    };

    const result = normalizeKimiToolSchema(schema);

    expect(result).toEqual({
      type: 'object',
      properties: {
        mode: { enum: ['fast', 'safe'], type: 'string' },
        retryCount: { const: 3, type: 'integer' },
      },
    });
  });

  it('normalizes nested child schema positions', () => {
    const thenKeyword = ['th', 'en'].join('');
    const schema = {
      properties: {
        labels: {
          patternProperties: {
            '^x-': { enum: ['yes', 'no'] },
          },
          propertyNames: { pattern: '^x-' },
          additionalProperties: { const: false },
        },
        tuple: {
          prefixItems: [{ enum: ['left', 'right'] }, { const: 2 }],
          contains: { enum: ['needle'] },
        },
        conditional: {
          if: { properties: { kind: { const: 'file' } } },
          [thenKeyword]: { properties: { path: { pattern: '^src/' } } },
          else: { properties: { url: { format: 'uri' } } },
          not: { properties: { blocked: { const: true } } },
        },
      },
    };

    const result = normalizeKimiToolSchema(schema);

    expect(result).toEqual({
      properties: {
        labels: {
          type: 'object',
          patternProperties: {
            '^x-': { enum: ['yes', 'no'], type: 'string' },
          },
          propertyNames: { pattern: '^x-', type: 'string' },
          additionalProperties: { const: false, type: 'boolean' },
        },
        tuple: {
          type: 'array',
          prefixItems: [
            { enum: ['left', 'right'], type: 'string' },
            { const: 2, type: 'integer' },
          ],
          contains: { enum: ['needle'], type: 'string' },
        },
        conditional: {
          if: {
            type: 'object',
            properties: { kind: { const: 'file', type: 'string' } },
          },
          [thenKeyword]: {
            type: 'object',
            properties: { path: { pattern: '^src/', type: 'string' } },
          },
          else: {
            type: 'object',
            properties: { url: { format: 'uri', type: 'string' } },
          },
          not: {
            type: 'object',
            properties: { blocked: { const: true, type: 'boolean' } },
          },
        },
      },
    });
  });

  it('infers parent types from every walked child-schema keyword', () => {
    const schema = {
      properties: {
        dependentSchemasOnly: {
          dependentSchemas: {
            kind: {
              properties: {
                value: { enum: ['file', 'url'] },
              },
            },
          },
        },
        dependenciesOnly: {
          dependencies: {
            kind: {
              properties: {
                enabled: { const: true },
              },
            },
          },
        },
        unevaluatedPropertiesOnly: {
          unevaluatedProperties: { enum: ['allowed'] },
        },
        additionalItemsOnly: {
          additionalItems: { const: 1 },
        },
        unevaluatedItemsOnly: {
          unevaluatedItems: { const: 2 },
        },
        contentSchemaOnly: {
          contentSchema: {
            properties: {
              decoded: { enum: ['payload'] },
            },
          },
        },
      },
    };

    const result = normalizeKimiToolSchema(schema);

    expect(result).toEqual({
      properties: {
        dependentSchemasOnly: {
          type: 'object',
          dependentSchemas: {
            kind: {
              type: 'object',
              properties: {
                value: { enum: ['file', 'url'], type: 'string' },
              },
            },
          },
        },
        dependenciesOnly: {
          type: 'object',
          dependencies: {
            kind: {
              type: 'object',
              properties: {
                enabled: { const: true, type: 'boolean' },
              },
            },
          },
        },
        unevaluatedPropertiesOnly: {
          type: 'object',
          unevaluatedProperties: { enum: ['allowed'], type: 'string' },
        },
        additionalItemsOnly: {
          type: 'array',
          additionalItems: { const: 1, type: 'integer' },
        },
        unevaluatedItemsOnly: {
          type: 'array',
          unevaluatedItems: { const: 2, type: 'integer' },
        },
        contentSchemaOnly: {
          type: 'string',
          contentSchema: {
            type: 'object',
            properties: {
              decoded: { enum: ['payload'], type: 'string' },
            },
          },
        },
      },
    });
  });

  it('preserves combinators while normalizing their schema branches', () => {
    const schema = {
      anyOf: [{ enum: ['auto', 'manual'] }, { const: false }],
      oneOf: [
        {
          properties: {
            strategy: { enum: ['replace', 'insert'] },
          },
        },
      ],
      allOf: [
        {
          items: { const: 1 },
        },
      ],
    };

    const result = normalizeKimiToolSchema(schema);

    expect(result).toEqual({
      anyOf: [
        { enum: ['auto', 'manual'], type: 'string' },
        { const: false, type: 'boolean' },
      ],
      oneOf: [
        {
          type: 'object',
          properties: {
            strategy: { enum: ['replace', 'insert'], type: 'string' },
          },
        },
      ],
      allOf: [
        {
          type: 'array',
          items: { const: 1, type: 'integer' },
        },
      ],
    });
    expect(result).not.toHaveProperty('type');
  });

  it('does not normalize non-record property values (normalizeProperty early return)', () => {
    const schema = {
      properties: {
        container: {
          // 'properties' is a map, but one of its entries is a primitive, not a schema object.
          properties: {
            leaf: 'primitive',
          },
        },
      },
    };
  
    const result = normalizeKimiToolSchema(schema);
  
    // The parent 'container' should be inferred as an object (because it has "properties"),
    // but the non-record child value 'leaf' must remain unchanged and not gain a "type".
    expect(result).toEqual({
      properties: {
        container: {
          type: 'object',
          properties: {
            leaf: 'primitive',
          },
        },
      },
    });
  });


  it('throws when enum contains non-JSON value (undefined) and does not mutate original', () => {
    const schema = {
      type: 'object',
      properties: {
        broken: { enum: [undefined as unknown] },
      },
    };
    const original = structuredClone(schema);
  
    expect(() => normalizeKimiToolSchema(schema)).toThrow(
      /Cannot infer JSON Schema type from non-JSON enum or const value\./,
    );
  
    // ensure the original schema object was not mutated
    expect(schema).toEqual(original);
  });


  it('normalizes items when items is an array (schema-or-array) and sets parent to array', () => {
    const schema = {
      properties: {
        tupleItems: {
          items: [{ const: 1 }, { const: 2 }],
        },
      },
    };
  
    const result = normalizeKimiToolSchema(schema);
  
    expect(result).toEqual({
      properties: {
        tupleItems: {
          type: 'array',
          items: [
            { const: 1, type: 'integer' },
            { const: 2, type: 'integer' },
          ],
        },
      },
    });
  });


  it('returns unresolved $ref as-is when pointer traverses into primitive and preserves $defs', () => {
    const schema = {
      type: 'object',
      properties: {
        // This $ref tries to walk into $defs.A.foo but $defs.A is a primitive (number).
        x: { $ref: '#/$defs/A/foo' },
      },
      $defs: {
        A: 1,
      },
    };
  
    const result = derefJsonSchema(schema);
  
    // The $ref couldn't be resolved and should be left as-is.
    const props = result['properties'] as Record<string, Record<string, unknown>>;
    expect(props['x']).toEqual({ $ref: '#/$defs/A/foo' });
  
    // Because an unresolved $ref points into $defs, the $defs bucket must be preserved.
    expect(result['$defs']).toEqual({ A: 1 });
  });


  it('resolves numeric array indices in local pointers and leaves bad/external refs intact', () => {
    const schema = {
      type: 'object',
      properties: {
        goodIndex: { $ref: '#/$defs/Arr/1' },
        badIndex: { $ref: '#/$defs/Arr/2' },   // out of bounds
        badFormat: { $ref: '#/$defs/Arr/01' }, // leading zero -> invalid numeric part
        external: { $ref: 'http://example.com/schema' }, // non-local ref
      },
      $defs: {
        Arr: ['zero', 'one'],
      },
    };
  
    const result = derefJsonSchema(schema);
  
    // 'goodIndex' should resolve to the array element 'one'
    expect((result['properties'] as Record<string, unknown>)['goodIndex']).toEqual('one');
  
    // 'badIndex' points at '#/$defs/Arr/2' which is out-of-range, so it must remain a $ref
    const bad = (result['properties'] as Record<string, unknown>)['badIndex'] as Record<string, unknown>;
    expect(bad).toBeDefined();
    expect(bad['$ref']).toBe('#/$defs/Arr/2');
  
    // 'badFormat' uses '01' which is invalid per pointer integer rules; it should remain a $ref
    const badFmt = (result['properties'] as Record<string, unknown>)['badFormat'] as Record<string, unknown>;
    expect(badFmt).toBeDefined();
    expect(badFmt['$ref']).toBe('#/$defs/Arr/01');
  
    // External refs should be preserved as-is
    const external = (result['properties'] as Record<string, unknown>)['external'] as Record<string, unknown>;
    expect(external['$ref']).toBe('http://example.com/schema');
  
    // Because we left unresolved $ref(s) into $defs, $defs must remain present in the output.
    expect(result['$defs']).toBeDefined();
  });


  it('does not merge sibling properties when a $ref resolves to an array/primitive', () => {
    const schema = {
      type: 'object',
      properties: {
        listLike: {
          $ref: '#/$defs/List',
          // This sibling description must NOT be preserved because the resolved
          // target is an array (non-object) and merging only occurs for objects.
          description: 'should not be merged',
        },
      },
      $defs: {
        List: ['a', 'b', 'c'],
      },
    };
  
    const result = derefJsonSchema(schema);
  
    // The property should be the array itself (resolved), and the sibling
    // "description" must not have been merged into the array result.
    expect(result).toEqual({
      type: 'object',
      properties: {
        listLike: ['a', 'b', 'c'],
      },
    });
    const list = (result['properties'] as Record<string, unknown>)['listLike'];
    expect(Array.isArray(list)).toBe(true);
    // Confirm no description present on the resolved array node.
    if (typeof list === 'object' && list !== null && !Array.isArray(list)) {
      // This branch should not happen; safeguard in case of regressions.
      expect((list as Record<string, unknown>)['description']).toBeUndefined();
    }
  });


  it('throws on non-object root and preserves # self-references without infinite recursion', () => {
    // Non-object root should cause a clear error from ensureKimiPropertyTypes
    const arrayRoot = [] as unknown as Record<string, unknown>;
    expect(() => normalizeKimiToolSchema(arrayRoot)).toThrow(
      /JSON Schema root must normalize to an object\./,
    );
  
    // A self-reference via '#' should be preserved somewhere in the nested result
    // rather than causing infinite recursion. Confirm the inner preserved $ref is '#'.
    const schema = {
      type: 'object',
      properties: {
        self: { $ref: '#' },
      },
    };
  
    const result = derefJsonSchema(schema);
    // The dereferenced 'self' should contain the nested preserved $ref.
    const nested = (result['properties'] as Record<string, unknown>)['self'] as Record<string, unknown>;
    expect(nested).toBeDefined();
    // After dereferencing, there should be a nested reference back to '#'
    // (i.e. result.properties.self.properties.self.$ref === '#').
    // Drill down safely with optional chaining to avoid crashes in case of regression.
    // We assert that the nested inner $ref exists and equals '#'.
    const innerRef = (nested['properties'] as Record<string, unknown> | undefined)?.['self'] as
      | Record<string, unknown>
      | undefined;
    expect(innerRef).toBeDefined();
    expect(innerRef!['$ref']).toBe('#');
  });

});
