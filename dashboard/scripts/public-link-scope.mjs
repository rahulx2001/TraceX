/** The 30 October source/demo check excludes the owner's later video task. */
export function targets(manifest) {
  const sourceCommit = manifest.submitted_source_commit || manifest.candidate_source_commit;
  if (sourceCommit && !/^[a-f0-9]{40}$/.test(sourceCommit)) throw new Error("Source commit must be a full Git SHA");
  const repository = manifest.repository_url?.replace(/\/$/, "");
  return [
    ["repository", repository],
    ["source_commit", sourceCommit && repository ? `${repository}/tree/${sourceCommit}` : null],
    ["hosted_demo", manifest.hosted_demo_url],
  ];
}

export function summarize(manifest, results) {
  const verified = kind => results.some(r => r.kind === kind && r.status === "anonymous_page_access_verified");
  return {
    scope: "Public source and hosted-demo links; video excluded from this pass. Portal/team still require inspection.",
    excluded: ["video"],
    source_commit: manifest.submitted_source_commit || manifest.candidate_source_commit || null,
    source_commit_kind: manifest.submitted_source_commit ? "submitted" : "candidate",
    source_commit_verified: verified("source_commit"),
    submitted_commit_verified: !!manifest.submitted_source_commit && verified("source_commit"),
    public_links_complete: ["repository", "source_commit", "hosted_demo"].every(verified),
    portal: {
      status: manifest.portal_submission_confirmed ? "owner_recorded_confirmation_requires_verification" : "pending_owner_portal_access",
      configured_url: manifest.portal_url,
      team_list_present: Array.isArray(manifest.team_members) && manifest.team_members.length > 0,
      verified: false,
    },
    // URL accessibility cannot certify portal entries, team or submission.
    complete: false,
  };
}
