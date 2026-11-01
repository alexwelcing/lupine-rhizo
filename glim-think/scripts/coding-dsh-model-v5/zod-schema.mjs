// Registration-boundary projection for the pinned Zod 4.4.3 output only.
// Zod adds non-JSON Standard Schema helpers at one root property. Preserve all
// JSON-schema data, but do not register those nonenumerable runtime functions.
function check(value, code) { if (!value) throw new Error(code); }
function ownData(object, key) {
  const descriptor = Object.getOwnPropertyDescriptor(object, key);
  check(descriptor && Object.hasOwn(descriptor, 'value'), 'ZOD_SCHEMA_METADATA_ACCESSOR');
  return descriptor.value;
}
function exactKeys(object, names) {
  check(object && Object.getPrototypeOf(object) === Object.prototype, 'ZOD_SCHEMA_METADATA_OBJECT');
  const keys = Reflect.ownKeys(object);
  check(keys.length === names.length && keys.every(k => typeof k === 'string' && names.includes(k)), 'ZOD_SCHEMA_METADATA_KEYS');
  for (const key of keys) {
    const d = Object.getOwnPropertyDescriptor(object, key);
    check(Object.hasOwn(d, 'value') && d.enumerable, 'ZOD_SCHEMA_METADATA_FIELD');
  }
}
function jsonCopy(value, depth = 0, budget = { nodes: 0 }) {
  check(depth <= 48 && ++budget.nodes <= 30000, 'ZOD_SCHEMA_JSON_BOUND');
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return value;
  if (typeof value === 'number') { check(Number.isFinite(value) && !Object.is(value, -0), 'ZOD_SCHEMA_JSON_NUMBER'); return value; }
  check(value && typeof value === 'object', 'ZOD_SCHEMA_NON_JSON');
  const array = Array.isArray(value), proto = Object.getPrototypeOf(value);
  check(array ? proto === Array.prototype : proto === Object.prototype || proto === null, 'ZOD_SCHEMA_JSON_PROTOTYPE');
  const descriptors = Object.getOwnPropertyDescriptors(value), keys = Reflect.ownKeys(descriptors);
  check(keys.every(k => typeof k === 'string'), 'ZOD_SCHEMA_JSON_SYMBOL');
  if (array) {
    check(value.length <= 30000 && keys.length === value.length + 1, 'ZOD_SCHEMA_JSON_ARRAY');
    return Array.from({ length: value.length }, (_, index) => {
      const d = descriptors[String(index)];
      check(d && Object.hasOwn(d, 'value') && d.enumerable, 'ZOD_SCHEMA_JSON_ARRAY_FIELD');
      return jsonCopy(d.value, depth + 1, budget);
    });
  }
  const out = {};
  for (const key of keys) {
    const d = descriptors[key];
    check(Object.hasOwn(d, 'value') && d.enumerable, 'ZOD_SCHEMA_JSON_HIDDEN_OR_ACCESSOR');
    check(!['__proto__', 'constructor', 'prototype'].includes(key), 'ZOD_SCHEMA_JSON_RESERVED');
    Object.defineProperty(out, key, { value: jsonCopy(d.value, depth + 1, budget), enumerable: true, writable: true, configurable: true });
  }
  return out;
}

export function projectPinnedZodSchema(raw, expectedStandard) {
  check(raw && Object.getPrototypeOf(raw) === Object.prototype, 'ZOD_SCHEMA_ROOT');
  const descriptor = Object.getOwnPropertyDescriptor(raw, '~standard');
  check(descriptor && Object.hasOwn(descriptor, 'value') && descriptor.enumerable === false
    && descriptor.configurable === false && descriptor.writable === false, 'ZOD_SCHEMA_METADATA_DESCRIPTOR');
  const meta = descriptor.value;
  exactKeys(meta, ['validate', 'vendor', 'version', 'jsonSchema']);
  check(ownData(meta, 'vendor') === 'zod' && ownData(meta, 'version') === 1, 'ZOD_SCHEMA_METADATA_IDENTITY');
  const validate = ownData(meta, 'validate');
  check(typeof validate === 'function' && expectedStandard && typeof expectedStandard === 'object'
    && ownData(expectedStandard, 'vendor') === 'zod' && ownData(expectedStandard, 'version') === 1
    && validate === ownData(expectedStandard, 'validate'), 'ZOD_SCHEMA_METADATA_ORIGIN');
  const methods = ownData(meta, 'jsonSchema');
  exactKeys(methods, ['input', 'output']);
  check(typeof ownData(methods, 'input') === 'function' && typeof ownData(methods, 'output') === 'function', 'ZOD_SCHEMA_METADATA_METHODS');
  const candidate = {};
  for (const key of Reflect.ownKeys(raw)) {
    if (key === '~standard') continue;
    check(typeof key === 'string', 'ZOD_SCHEMA_JSON_SYMBOL');
    // Retain the descriptor until validation; do not silently omit another
    // hidden property or evaluate an accessor during copying.
    Object.defineProperty(candidate, key, Object.getOwnPropertyDescriptor(raw, key));
  }
  const out = jsonCopy(candidate);
  check(Buffer.byteLength(JSON.stringify(out)) <= 256 * 1024, 'ZOD_SCHEMA_JSON_BYTES');
  return out;
}
