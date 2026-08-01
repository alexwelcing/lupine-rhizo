import test from "node:test";
import assert from "node:assert/strict";
import { forwardContentType } from "./index.js";

test("forwards valid OTLP protobuf and JSON content types", () => {
  assert.equal(forwardContentType("application/x-protobuf"), "application/x-protobuf");
  assert.equal(forwardContentType("application/json; charset=utf-8"), "application/json");
});

test("fails closed on unsupported content types", () => {
  assert.throws(() => forwardContentType("text/plain"), /unsupported OTLP content-type/);
  assert.throws(() => forwardContentType(undefined), /unsupported OTLP content-type/);
});
