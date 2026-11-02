/** Plain recovery messages; technical detail stays in diagnostics, not the task. */
export function operatorError(error, action = "complete this action") {
  const status = Number(error?.status || String(error?.message || error || "").match(/\b([45]\d\d)\b/)?.[1]);
  if (status === 401) return "Your session has expired. Sign in again, then retry. Your draft is still here.";
  if (status === 403) return "Your current access does not allow this action. Sign in with an authorized account or ask your supervisor. Your draft is still here.";
  if (status === 404) return "This record is no longer available. Refresh the list and select it again.";
  if (status === 400 || status === 422) return "Some details could not be accepted. Check the fields and try again. Your draft is still here.";
  if (status === 413) return "This file is too large. Choose a photo no larger than 8 MB and retry.";
  if (status === 429) return "The service is busy. Wait a moment, then retry. Your draft is still here.";
  return `Could not ${action}. Check your connection and retry. Your draft is still here.`;
}

export function noteAuthor(author) {
  if (!author || author === "operator") return "Shared operator account";
  return author;
}
