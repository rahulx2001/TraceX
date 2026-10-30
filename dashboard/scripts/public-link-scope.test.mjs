import assert from "node:assert/strict";
import { test } from "node:test";
import { targets, summarize } from "./public-link-scope.mjs";

const manifest = { repository_url: "https://github.com/rahulx2001/TraceX", candidate_source_commit: "a".repeat(40),
  hosted_demo_url: null, video_url: null, submitted_source_commit: null, portal_url: null, team_members: [], portal_submission_confirmed: false };

test("video is excluded; missing hosted demo stays pending and candidate is not a submission", () => {
  assert.deepEqual(targets(manifest).map(([kind]) => kind), ["repository", "source_commit", "hosted_demo"]);
  const results = ["repository", "source_commit"].map(kind => ({ kind, status: "anonymous_page_access_verified" }));
  const report = summarize(manifest, results);
  assert.equal(report.source_commit_verified, true);
  assert.equal(report.submitted_commit_verified, false);
  assert.equal(report.public_links_complete, false);
  assert.equal(report.complete, false);
});

test("accessible links and owner confirmation alone cannot certify portal/team inspection", () => {
  const results = targets(manifest).map(([kind]) => ({ kind, status: "anonymous_page_access_verified" }));
  const report = summarize({ ...manifest, submitted_source_commit: "a".repeat(40), portal_submission_confirmed: true }, results);
  assert.equal(report.public_links_complete, true);
  assert.equal(report.submitted_commit_verified, true);
  assert.equal(report.portal.verified, false);
  assert.equal(report.complete, false);
  assert.throws(() => targets({ ...manifest, candidate_source_commit: "main" }), /full Git SHA/);
});
