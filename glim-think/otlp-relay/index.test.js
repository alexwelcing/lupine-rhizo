import test from "node:test";
import assert from "node:assert/strict";
import { forwardOtlpPayload } from "./index.js";

const TRACE_ID = "00112233445566778899aabbccddeeff";
const SPAN_ID = "1020304050607080";
const JSON_TRACE = Buffer.from(JSON.stringify({
  resourceSpans: [{
    resource: { attributes: [{ key: "service.name", value: { stringValue: "tasks-consumer" } }] },
    scopeSpans: [{
      scope: { name: "mlip.flywheel" },
      spans: [{
        traceId: TRACE_ID,
        spanId: SPAN_ID,
        name: "mlip.flywheel.cloud_cell",
        kind: 1,
        startTimeUnixNano: "1785589200000000000",
        endTimeUnixNano: "1785589200000000000",
        status: { code: 1 },
      }],
    }],
  }],
}));

function decodeFields(buffer) {
  const fields = new Map();
  let offset = 0;
  const readVarint = () => {
    let value = 0;
    let shift = 0;
    while (offset < buffer.length) {
      const byte = buffer[offset++];
      value += (byte & 0x7f) * (2 ** shift);
      if ((byte & 0x80) === 0) return value;
      shift += 7;
    }
    throw new Error("truncated protobuf varint");
  };
  while (offset < buffer.length) {
    const tag = readVarint();
    const fieldNumber = tag >>> 3;
    const wireType = tag & 7;
    let value;
    if (wireType === 0) value = readVarint();
    else if (wireType === 1) { value = buffer.subarray(offset, offset + 8); offset += 8; }
    else if (wireType === 2) {
      const length = readVarint();
      value = buffer.subarray(offset, offset + length);
      offset += length;
    } else if (wireType === 5) { value = buffer.subarray(offset, offset + 4); offset += 4; }
    else throw new Error(`unsupported protobuf wire type ${wireType}`);
    if (!fields.has(fieldNumber)) fields.set(fieldNumber, []);
    fields.get(fieldNumber).push(value);
  }
  return fields;
}

function decodeFirstSpan(buffer) {
  const resourceSpan = decodeFields(buffer).get(1)[0];
  const scopeSpan = decodeFields(resourceSpan).get(2)[0];
  return decodeFields(decodeFields(scopeSpan).get(2)[0]);
}

test("passes valid OTLP protobuf through unchanged", () => {
  const body = Buffer.from([0x0a, 0x00]);
  assert.deepEqual(forwardOtlpPayload("application/x-protobuf", body), {
    contentType: "application/x-protobuf",
    body,
  });
});

test("transcodes OTLP JSON to protobuf while preserving hex trace and span IDs", () => {
  const forwarded = forwardOtlpPayload("application/json; charset=utf-8", JSON_TRACE);
  assert.equal(forwarded.contentType, "application/x-protobuf");
  assert.ok(Buffer.isBuffer(forwarded.body));
  const span = decodeFirstSpan(forwarded.body);
  assert.equal(span.get(1)[0].toString("hex"), TRACE_ID);
  assert.equal(span.get(2)[0].toString("hex"), SPAN_ID);
});

test("fails closed on unsupported content types", () => {
  assert.throws(() => forwardOtlpPayload("text/plain", Buffer.from("x")), /unsupported OTLP content-type/);
  assert.throws(() => forwardOtlpPayload(undefined, Buffer.from("x")), /unsupported OTLP content-type/);
});

test("fails closed on malformed OTLP JSON and malformed IDs", () => {
  assert.throws(() => forwardOtlpPayload("application/json", Buffer.from("{bad")), /invalid OTLP JSON/);
  const malformed = JSON.parse(JSON_TRACE.toString());
  malformed.resourceSpans[0].scopeSpans[0].spans[0].traceId = "not-hex";
  assert.throws(
    () => forwardOtlpPayload("application/json", Buffer.from(JSON.stringify(malformed))),
    /traceId must be 32 hexadecimal characters/,
  );
  malformed.resourceSpans[0].scopeSpans[0].spans[0].traceId = "0".repeat(32);
  assert.throws(
    () => forwardOtlpPayload("application/json", Buffer.from(JSON.stringify(malformed))),
    /traceId must not be all zero/,
  );
  malformed.resourceSpans[0].scopeSpans[0].spans[0].traceId = TRACE_ID;
  malformed.resourceSpans[0].scopeSpans[0].spans[0].spanId = "0".repeat(16);
  assert.throws(
    () => forwardOtlpPayload("application/json", Buffer.from(JSON.stringify(malformed))),
    /spanId must not be all zero/,
  );
});

test("fails closed instead of silently dropping span events or links", () => {
  for (const field of ["events", "links"]) {
    const unsupported = JSON.parse(JSON_TRACE.toString());
    unsupported.resourceSpans[0].scopeSpans[0].spans[0][field] = [{}];
    assert.throws(
      () => forwardOtlpPayload("application/json", Buffer.from(JSON.stringify(unsupported))),
      new RegExp(`${field} are not supported`),
    );
  }
});

test("fails closed instead of silently dropping unsupported OTLP JSON fields", () => {
  for (const mutate of [
    (request) => { request.resourceSpans[0].schemaUrl = "https://resource.schema"; },
    (request) => { request.resourceSpans[0].resource.droppedAttributesCount = 1; },
    (request) => { request.resourceSpans[0].scopeSpans[0].schemaUrl = "https://scope.schema"; },
    (request) => {
      request.resourceSpans[0].scopeSpans[0].scope.attributes = [
        { key: "scope.attr", value: { stringValue: "would-be-dropped" } },
      ];
    },
    (request) => { request.resourceSpans[0].scopeSpans[0].scope.droppedAttributesCount = 1; },
    (request) => { request.resourceSpans[0].scopeSpans[0].spans[0].traceState = "vendor=value"; },
    (request) => { request.resourceSpans[0].scopeSpans[0].spans[0].flags = 0x100; },
    (request) => {
      request.resourceSpans[0].resource.attributes = [
        { key: "duplicate", value: { stringValue: "first" } },
        { key: "duplicate", value: { stringValue: "second" } },
      ];
    },
    (request) => { request.resourceSpans[0].unknownField = "must-not-disappear"; },
  ]) {
    const unsupported = JSON.parse(JSON_TRACE.toString());
    mutate(unsupported);
    assert.throws(
      () => forwardOtlpPayload("application/json", Buffer.from(JSON.stringify(unsupported))),
      /not supported by JSON transcoding|unsupported field/,
    );
  }
});

test("fails closed on malformed OTLP enum, count, integer, and timestamp values", () => {
  for (const [mutate, expected] of [
    [(request) => { request.resourceSpans[0].scopeSpans[0].spans[0].kind = "garbage"; }, /kind must be an integer/],
    [(request) => { request.resourceSpans[0].scopeSpans[0].spans[0].kind = 7; }, /kind must be between 0 and 6/],
    [(request) => { request.resourceSpans[0].scopeSpans[0].spans[0].status.code = "garbage"; }, /status.code must be an integer/],
    [(request) => { request.resourceSpans[0].scopeSpans[0].spans[0].status.code = 3; }, /status.code must be between 0 and 2/],
    [(request) => { request.resourceSpans[0].scopeSpans[0].spans[0].status.message = 7; }, /status.message must be a string/],
    [(request) => { request.resourceSpans[0].scopeSpans[0].spans[0].droppedAttributesCount = -1; }, /droppedAttributesCount must be an unsigned 32-bit integer/],
    [(request) => { request.resourceSpans[0].scopeSpans[0].spans[0].droppedEventsCount = 2 ** 32; }, /droppedEventsCount must be an unsigned 32-bit integer/],
    [(request) => {
      request.resourceSpans[0].scopeSpans[0].spans[0].attributes = [
        { key: "bad-int", value: { intValue: null } },
      ];
    }, /intValue must be a safe integer/],
    [(request) => { request.resourceSpans[0].scopeSpans[0].spans[0].startTimeUnixNano = (2n ** 64n).toString(); }, /startTimeUnixNano must fit uint64/],
    [(request) => { request.resourceSpans[0].scopeSpans[0].spans[0].flags = "0"; }, /flags must be an unsigned 32-bit integer/],
  ]) {
    const malformed = JSON.parse(JSON_TRACE.toString());
    mutate(malformed);
    assert.throws(
      () => forwardOtlpPayload("application/json", Buffer.from(JSON.stringify(malformed))),
      expected,
    );
  }
});

test("fails closed when a span ends before it starts", () => {
  const malformed = JSON.parse(JSON_TRACE.toString());
  malformed.resourceSpans[0].scopeSpans[0].spans[0].endTimeUnixNano = "1";
  assert.throws(
    () => forwardOtlpPayload("application/json", Buffer.from(JSON.stringify(malformed))),
    /endTimeUnixNano must not precede startTimeUnixNano/,
  );
});

test("preserves an explicit zero trace-flags value", () => {
  const request = JSON.parse(JSON_TRACE.toString());
  request.resourceSpans[0].scopeSpans[0].spans[0].flags = 0;
  const forwarded = forwardOtlpPayload(
    "application/json",
    Buffer.from(JSON.stringify(request)),
  );
  const span = decodeFirstSpan(forwarded.body);
  assert.equal(span.get(16)[0].readUInt32LE() & 0xff, 0);
});

test("preserves the sampled bit from OTLP JSON trace flags", () => {
  const request = JSON.parse(JSON_TRACE.toString());
  request.resourceSpans[0].scopeSpans[0].spans[0].flags = 1;
  const forwarded = forwardOtlpPayload(
    "application/json",
    Buffer.from(JSON.stringify(request)),
  );
  const span = decodeFirstSpan(forwarded.body);
  assert.equal(span.get(16)[0].readUInt32LE() & 0xff, 1);
});
