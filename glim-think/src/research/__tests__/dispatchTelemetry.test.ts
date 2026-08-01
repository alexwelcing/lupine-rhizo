import { describe, expect, it } from "vitest";
import { __internal, type TaskPayload } from "../dispatch";

function payload(): TaskPayload {
  return {
    fixture_url: "gs://inputs/eval.json",
    command: "run-cell",
    beat_emit_url: "https://worker.test/feed/beats",
    target_job: "mlip-cell-chgnet",
    telemetry: {
      schema: "lupine.mlip.cloud_cell_span.v1",
      origin: "cloud",
      correlation_id: "campaign-a",
      run_id: "run-a",
      cell_id: "run-a:baseline:energy_volume:chgnet",
      row_id: "energy_volume",
      mlip_id: "chgnet",
    },
    args: [
      "--run-id", "run-a",
      "--cell-id", "run-a:baseline:energy_volume:chgnet",
      "--row-id", "energy_volume",
      "--mlip-id", "chgnet",
    ],
  };
}

describe("cloud telemetry identity validation", () => {
  it.each(["--run-id", "--cell-id", "--row-id", "--mlip-id"])(
    "rejects duplicate %s flags before dispatch",
    (flag) => {
      const candidate = payload();
      candidate.args!.push(flag, "attacker-controlled");
      expect(() => __internal.validatePayload(candidate)).toThrow(`duplicate ${flag} argument`);
    },
  );

  it.each(["--run-id", "--cell-id", "--row-id", "--mlip-id"])(
    "rejects mixed-form duplicate %s flags before dispatch",
    (flag) => {
      const candidate = payload();
      candidate.args!.push(`${flag}=attacker-controlled`);
      expect(() => __internal.validatePayload(candidate)).toThrow(`duplicate ${flag} argument`);
    },
  );

  it.each(["--run-i", "--cell-i", "--row-i", "--mlip-i"])(
    "rejects abbreviated identity flag %s before dispatch",
    (flag) => {
      const candidate = payload();
      candidate.args!.push(flag, "attacker-controlled");
      expect(() => __internal.validatePayload(candidate)).toThrow(
        `${flag} is an abbreviated identity argument`,
      );
    },
  );

  it("rejects malformed and dangling argument arrays before dispatch", () => {
    const nonString = payload() as unknown as { args: unknown[] };
    nonString.args[1] = 42;
    expect(() => __internal.validatePayload(nonString as unknown as TaskPayload)).toThrow(
      "args must be an array of strings",
    );

    const dangling = payload();
    dangling.args = ["--run-id"];
    expect(() => __internal.validatePayload(dangling)).toThrow("missing --run-id argument");
  });
});