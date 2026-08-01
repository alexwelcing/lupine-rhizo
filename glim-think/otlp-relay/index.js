/**
 * Phoenix OTLP egress relay (Cloud Run).
 *
 * Why this exists: app.phoenix.arize.com is Cloudflare-fronted, and Cloudflare
 * short-circuits Cloudflare-Worker → Cloudflare-zone subrequests at the edge,
 * returning a deceptive OTLP-success-shaped `200` while black-holing the
 * spans (proven 2026-05-16 — see ../OBSERVABILITY.md). A request from GCP's
 * network reaches Phoenix's real origin and ingests normally.
 *
 * This service receives the Worker's OTLP protobuf, authenticates it with a
 * shared token (so it is not an open proxy), and forwards it to Phoenix Cloud
 * with the Bearer key + the WAF-allowed OTLP User-Agent. JSON requests are
 * transcoded with OpenTelemetry's protobuf serializer because Phoenix's
 * configured ingress accepts OTLP/HTTP protobuf but rejects JSON with 415.
 */

import { createServer } from "node:http";
import { pathToFileURL } from "node:url";
import { ProtobufTraceSerializer } from "@opentelemetry/otlp-transformer";

const PORT = process.env.PORT || 8080;
const PHOENIX_OTLP_URL = process.env.PHOENIX_OTLP_URL; // .../s/<space>/v1/traces
const PHOENIX_API_KEY = process.env.PHOENIX_API_KEY;
const RELAY_TOKEN = process.env.RELAY_TOKEN;
// Phoenix Cloud's WAF blocks custom/product User-Agents (e.g. "glim-think/*")
// with a 302→/login. The standard OTLP exporter UA is allowed and accurate.
const FORWARD_UA = "OTel-OTLP-Exporter-JavaScript/0.200.0";

function mediaType(value) {
  return String(value || "").split(";", 1)[0].trim().toLowerCase();
}

function requireHexId(value, bytes, field) {
  const pattern = new RegExp(`^[0-9a-fA-F]{${bytes * 2}}$`);
  if (typeof value !== "string" || !pattern.test(value)) {
    throw new Error(`${field} must be ${bytes * 2} hexadecimal characters`);
  }
  if (/^0+$/.test(value)) throw new Error(`${field} must not be all zero`);
  return value.toLowerCase();
}

function rejectUnknownFields(value, allowed, field) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${field} must be an object`);
  }
  for (const key of Object.keys(value)) {
    if (!allowed.has(key)) throw new Error(`${field}.${key} is an unsupported field`);
  }
}

function rejectPresent(value, key, field) {
  if (value[key] !== undefined) {
    throw new Error(`${field}.${key} is not supported by JSON transcoding`);
  }
}

function uint32(value, field) {
  if (value === undefined) return 0;
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0 || value > 0xffff_ffff) {
    throw new Error(`${field} must be an unsigned 32-bit integer`);
  }
  return value;
}

function enumValue(value, field, max) {
  const parsed = value === undefined ? 0 : value;
  if (typeof parsed !== "number" || !Number.isInteger(parsed)) {
    throw new Error(`${field} must be an integer`);
  }
  if (parsed < 0 || parsed > max) {
    throw new Error(`${field} must be between 0 and ${max}`);
  }
  return parsed;
}

function anyValue(value, field) {
  rejectUnknownFields(value, new Set(["stringValue", "boolValue", "intValue", "doubleValue"]), field);
  if (Object.keys(value).length !== 1) throw new Error(`${field} must contain exactly one OTLP value`);
  if (typeof value.stringValue === "string") return value.stringValue;
  if (typeof value.boolValue === "boolean") return value.boolValue;
  if (value.intValue !== undefined) {
    const validType = typeof value.intValue === "number" ||
      (typeof value.intValue === "string" && /^-?(0|[1-9]\d*)$/.test(value.intValue));
    const parsed = validType ? Number(value.intValue) : Number.NaN;
    if (Number.isSafeInteger(parsed)) return parsed;
    throw new Error(`${field}.intValue must be a safe integer`);
  }
  if (typeof value.doubleValue === "number" && Number.isFinite(value.doubleValue)) {
    return value.doubleValue;
  }
  throw new Error(`${field} uses an unsupported OTLP value`);
}

function attributes(values, field) {
  if (values === undefined) return {};
  if (!Array.isArray(values)) throw new Error(`${field} must be an array`);
  const seen = new Set();
  return Object.fromEntries(values.map((entry, index) => {
    rejectUnknownFields(entry, new Set(["key", "value"]), `${field}[${index}]`);
    if (!entry || typeof entry.key !== "string" || !entry.key) {
      throw new Error(`${field}[${index}].key must be a non-empty string`);
    }
    if (seen.has(entry.key)) {
      throw new Error(`${field}[${index}].key duplicate is not supported by JSON transcoding`);
    }
    seen.add(entry.key);
    return [entry.key, anyValue(entry.value, `${field}[${index}].value`)];
  }));
}

function hrTime(value, field) {
  if (typeof value !== "string" || !/^(0|[1-9]\d*)$/.test(value)) {
    throw new Error(`${field} must be an unsigned integer string`);
  }
  const nanos = BigInt(value);
  if (nanos > 0xffff_ffff_ffff_ffffn) throw new Error(`${field} must fit uint64`);
  return {
    nanos,
    value: [Number(nanos / 1_000_000_000n), Number(nanos % 1_000_000_000n)],
  };
}

function readableSpans(request) {
  if (!request || typeof request !== "object" || !Array.isArray(request.resourceSpans)) {
    throw new Error("resourceSpans must be an array");
  }
  rejectUnknownFields(request, new Set(["resourceSpans"]), "request");
  const spans = [];
  request.resourceSpans.forEach((resourceSpans, resourceIndex) => {
    const resourceField = `resourceSpans[${resourceIndex}]`;
    rejectUnknownFields(resourceSpans, new Set(["resource", "scopeSpans", "schemaUrl"]), resourceField);
    rejectPresent(resourceSpans, "schemaUrl", resourceField);
    if (!resourceSpans || !Array.isArray(resourceSpans.scopeSpans)) {
      throw new Error(`resourceSpans[${resourceIndex}].scopeSpans must be an array`);
    }
    const resourceValue = resourceSpans.resource || {};
    rejectUnknownFields(resourceValue, new Set(["attributes", "droppedAttributesCount"]), `${resourceField}.resource`);
    const resourceDroppedAttributes = uint32(
      resourceValue.droppedAttributesCount,
      `${resourceField}.resource.droppedAttributesCount`,
    );
    if (resourceDroppedAttributes !== 0) {
      throw new Error(`${resourceField}.resource.droppedAttributesCount is not supported by JSON transcoding`);
    }
    const resource = {
      attributes: attributes(resourceSpans.resource?.attributes, `resourceSpans[${resourceIndex}].resource.attributes`),
      droppedAttributesCount: resourceDroppedAttributes,
    };
    resourceSpans.scopeSpans.forEach((scopeSpans, scopeIndex) => {
      const scopeSpansField = `${resourceField}.scopeSpans[${scopeIndex}]`;
      rejectUnknownFields(scopeSpans, new Set(["scope", "spans", "schemaUrl"]), scopeSpansField);
      rejectPresent(scopeSpans, "schemaUrl", scopeSpansField);
      if (!scopeSpans || !Array.isArray(scopeSpans.spans)) {
        throw new Error(`resourceSpans[${resourceIndex}].scopeSpans[${scopeIndex}].spans must be an array`);
      }
      const scopeValue = scopeSpans.scope || {};
      rejectUnknownFields(
        scopeValue,
        new Set(["name", "version", "attributes", "droppedAttributesCount"]),
        `${scopeSpansField}.scope`,
      );
      const scopeDroppedAttributes = uint32(
        scopeValue.droppedAttributesCount,
        `${scopeSpansField}.scope.droppedAttributesCount`,
      );
      if (scopeDroppedAttributes !== 0) {
        throw new Error(`${scopeSpansField}.scope.droppedAttributesCount is not supported by JSON transcoding`);
      }
      if (Array.isArray(scopeValue.attributes) && scopeValue.attributes.length > 0) {
        throw new Error(`${scopeSpansField}.scope.attributes are not supported by JSON transcoding`);
      }
      const instrumentationScope = {
        name: String(scopeSpans.scope?.name || ""),
        version: scopeSpans.scope?.version,
        attributes: attributes(scopeSpans.scope?.attributes, `resourceSpans[${resourceIndex}].scopeSpans[${scopeIndex}].scope.attributes`),
      };
      scopeSpans.spans.forEach((span, spanIndex) => {
        const field = `resourceSpans[${resourceIndex}].scopeSpans[${scopeIndex}].spans[${spanIndex}]`;
        rejectUnknownFields(span, new Set([
          "traceId", "spanId", "traceState", "parentSpanId", "flags", "name", "kind",
          "startTimeUnixNano", "endTimeUnixNano", "attributes", "droppedAttributesCount",
          "events", "droppedEventsCount", "links", "droppedLinksCount", "status",
        ]), field);
        rejectPresent(span, "traceState", field);
        const flags = uint32(span.flags, `${field}.flags`);
        if ((flags & ~0xff) !== 0) {
          throw new Error(`${field}.flags contain bits not supported by JSON transcoding`);
        }
        if (!span || typeof span !== "object" || typeof span.name !== "string" || !span.name) {
          throw new Error(`${field}.name must be a non-empty string`);
        }
        const traceId = requireHexId(span.traceId, 16, "traceId");
        const spanId = requireHexId(span.spanId, 8, "spanId");
        const parentSpanId = span.parentSpanId
          ? requireHexId(span.parentSpanId, 8, "parentSpanId")
          : undefined;
        for (const collection of ["events", "links"]) {
          if (span[collection] !== undefined &&
              (!Array.isArray(span[collection]) || span[collection].length > 0)) {
            throw new Error(`${field}.${collection} are not supported by JSON transcoding`);
          }
        }
        const statusValue = span.status || {};
        rejectUnknownFields(statusValue, new Set(["code", "message"]), `${field}.status`);
        const kind = enumValue(span.kind, `${field}.kind`, 6);
        const statusCode = enumValue(statusValue.code, `${field}.status.code`, 2);
        if (statusValue.message !== undefined && typeof statusValue.message !== "string") {
          throw new Error(`${field}.status.message must be a string`);
        }
        const startTime = hrTime(span.startTimeUnixNano, `${field}.startTimeUnixNano`);
        const endTime = hrTime(span.endTimeUnixNano, `${field}.endTimeUnixNano`);
        if (endTime.nanos < startTime.nanos) {
          throw new Error(`${field}.endTimeUnixNano must not precede startTimeUnixNano`);
        }
        spans.push({
          name: span.name,
          kind: kind - 1,
          spanContext: () => ({ traceId, spanId, traceFlags: flags & 0xff, isRemote: false }),
          parentSpanContext: parentSpanId
            ? { traceId, spanId: parentSpanId, traceFlags: flags & 0xff, isRemote: false }
            : undefined,
          startTime: startTime.value,
          endTime: endTime.value,
          status: { code: statusCode, message: statusValue.message },
          attributes: attributes(span.attributes, `${field}.attributes`),
          droppedAttributesCount: uint32(span.droppedAttributesCount, `${field}.droppedAttributesCount`),
          events: [],
          droppedEventsCount: uint32(span.droppedEventsCount, `${field}.droppedEventsCount`),
          links: [],
          droppedLinksCount: uint32(span.droppedLinksCount, `${field}.droppedLinksCount`),
          resource,
          instrumentationScope,
        });
      });
    });
  });
  return spans;
}

export function forwardOtlpPayload(value, body) {
  const type = mediaType(value);
  if (type === "application/x-protobuf") {
    return { contentType: type, body };
  }
  if (type === "application/json") {
    let request;
    try {
      request = JSON.parse(body.toString("utf8"));
    } catch (error) {
      throw new Error(`invalid OTLP JSON: ${String(error)}`);
    }
    return {
      contentType: "application/x-protobuf",
      body: Buffer.from(ProtobufTraceSerializer.serializeRequest(readableSpans(request))),
    };
  }
  throw new Error(`unsupported OTLP content-type: ${value || "missing"}`);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

const server = createServer(async (req, res) => {
  const send = (status, body, headers = {}) => {
    res.writeHead(status, { "content-type": "text/plain", ...headers });
    res.end(body);
  };

  if (req.method === "GET" && req.url === "/healthz") {
    return send(200, "ok");
  }

  if (req.method !== "POST" || !req.url.startsWith("/v1/traces")) {
    return send(404, "not found");
  }

  if (!PHOENIX_OTLP_URL || !PHOENIX_API_KEY || !RELAY_TOKEN) {
    return send(500, "relay misconfigured (missing env)");
  }

  // Shared-secret auth — reject anything without the Worker's relay token.
  if (req.headers["x-relay-token"] !== RELAY_TOKEN) {
    return send(401, "unauthorized");
  }

  let body;
  try {
    body = await readBody(req);
  } catch {
    return send(400, "failed to read body");
  }
  if (body.length === 0) {
    return send(400, "empty body");
  }

  let forwarded;
  try {
    forwarded = forwardOtlpPayload(req.headers["content-type"], body);
  } catch (error) {
    return send(415, String(error.message || error));
  }

  try {
    const upstream = await fetch(PHOENIX_OTLP_URL, {
      method: "POST",
      headers: {
        "content-type": forwarded.contentType,
        accept: "application/x-protobuf",
        "user-agent": FORWARD_UA,
        Authorization: `Bearer ${PHOENIX_API_KEY}`,
      },
      body: forwarded.body,
      redirect: "manual",
    });
    const buf = Buffer.from(await upstream.arrayBuffer());
    // Surface the true upstream result (incl. 3xx) so the Worker exporter's
    // hardened error path can react instead of silently "succeeding".
    res.writeHead(upstream.status, {
      "content-type": upstream.headers.get("content-type") || "application/octet-stream",
      "x-phoenix-upstream-status": String(upstream.status),
    });
    res.end(buf);
  } catch (e) {
    send(502, `relay upstream error: ${String(e)}`);
  }
});

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  server.listen(PORT, () => {
    console.log(`[otlp-relay] listening on :${PORT} → ${PHOENIX_OTLP_URL ? "configured" : "MISSING PHOENIX_OTLP_URL"}`);
  });
}
