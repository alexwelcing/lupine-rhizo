import { test } from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import { preparePublicActivityImport } from "./prepare-public-activity-import.mjs";

const migration = readFileSync(new URL("../migrations/0021_public_research_activity.sql", import.meta.url), "utf8");
const fixture = () => ({ schema: "lupine.public_research_activity.v1", id: "public-preparation-one", activityId: "public-preparation",
  evidenceKind: "archived_analysis", state: "failed", verification: "pending", title: "Reviewed fixture",
  summary: "It's a reviewed summary; punctuation isn't SQL.", observedAt: "2026-10-01T10:00:00.000Z", reviewedAt: "2026-10-01T11:00:00.000Z",
  datasets: [], findings: [], limitations: ["Synthetic fixture."], nextStep: "Review the failure.", sources: [], hashes: [], repositoryLinks: [], releaseLinks: [], supersedes: null, correctionReason: null });
const feed = (...items) => ({ schema: "lupine.public_research_activity_feed.v1", items, truncated: false });

test("prepared SQL and parameterized statements preserve reviewed text and are idempotent", async () => {
  const value = fixture(); const result = await preparePublicActivityImport(feed(value));
  const db = new DatabaseSync(":memory:");
  try {
    db.exec(migration); db.exec(result.sql); db.exec(result.sql);
    assert.equal(db.prepare("SELECT count(*) n FROM public_research_activity").get().n, 1);
    assert.equal(JSON.parse(db.prepare("SELECT payload FROM public_research_activity").get().payload).summary, value.summary);
    assert.equal(result.statements[0].sql.includes("?"), true);
    assert.equal(result.sql.includes("It's"), false);
    const changed = await preparePublicActivityImport(feed({ ...value, summary: "Changed existing identity." }));
    assert.throws(() => db.exec(changed.sql), /immutable/);
  } finally { db.close(); }
});

test("D1 guards enforce same-state terminal corrections, ancestry and no branch even for separately prepared files", async () => {
  const original = fixture(); const db = new DatabaseSync(":memory:");
  try {
    db.exec(migration); db.exec((await preparePublicActivityImport(feed(original))).sql);
    const correction = { ...original, id: "public-preparation-two", supersedes: original.id, reviewedAt: "2026-10-01T12:00:00.000Z", correctionReason: "Clarified the recorded failure." };
    const reopen = await preparePublicActivityImport(feed({ ...correction, state: "completed" }));
    assert.throws(() => db.exec(reopen.sql), /terminal state conflicts/);
    db.exec((await preparePublicActivityImport(feed(correction))).sql);
    const fork = await preparePublicActivityImport(feed({ ...correction, id: "public-preparation-fork" }));
    assert.throws(() => db.exec(fork.sql), /terminal state conflicts/);
    assert.equal(db.prepare("SELECT count(*) n FROM public_research_activity").get().n, 2);
  } finally { db.close(); }
});

test("the actual runtime schema rejects private fields and invalid batch history", async () => {
  const original = fixture();
  await assert.rejects(preparePublicActivityImport(feed({ ...original, packetJson: "private" })));
  await assert.rejects(preparePublicActivityImport(feed({ ...original, summary: "gs://private-bucket/file" })));
  await assert.rejects(preparePublicActivityImport(feed(original, original)));
  await assert.rejects(preparePublicActivityImport({ ...feed(original), truncated: true }));
  await assert.rejects(preparePublicActivityImport(feed(original, { ...original, id: "bad-next", state: "completed", supersedes: original.id, reviewedAt: "2026-10-01T12:00:00.000Z", correctionReason: "Cannot reopen failure." })));
});
