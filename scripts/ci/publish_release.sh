#!/usr/bin/env bash
# Recoverable release lifecycle: draft -> single verified EXE -> published.
# A failed upload leaves an unpublished draft that the next run can repair.
set -Eeuo pipefail

: "$RELEASE_TAG"
: "$GITHUB_REPOSITORY"
installer="${INSTALLER_PATH:-release/PyMoviePrint-Setup.exe}"
if [[ ! -s "$installer" ]]; then
  echo "::error title=Missing Windows installer::Expected nonempty $installer" >&2
  exit 1
fi
if [[ "$(basename "$installer")" != "PyMoviePrint-Setup.exe" ]]; then
  echo "::error title=Unexpected installer name::Only PyMoviePrint-Setup.exe may be released" >&2
  exit 1
fi

expected_digest="sha256:$(sha256sum "$installer" | awk '{print $1}')"
trap 'rc=$?; echo "::error title=Release upload/publish failed::Tag $RELEASE_TAG failed at line $LINENO with exit $rc" >&2; exit "$rc"' ERR

# GitHub's GET /releases/tags/{tag} endpoint returns PUBLISHED releases
# only. Drafts must be discovered by the authenticated list releases API.
# github/cli's FetchRelease does a separate GraphQL pending-tag lookup.
read_release() {
  local releases
  releases="$(gh api --paginate --slurp "repos/$GITHUB_REPOSITORY/releases?per_page=100")"
  jq -cer --arg tag "$RELEASE_TAG" '
    [.[][] | select(.tag_name == $tag)] |
    if length > 1 then error("multiple releases carry the same tag") else .[0] // empty end
  ' <<< "$releases"
}

echo "Preparing direct installer release: tag=$RELEASE_TAG file=$installer digest=$expected_digest"
release_json="$(read_release)"
if [[ -n "$release_json" ]]; then
  echo "Existing release found (draft or published); verifying state."
else
  echo "Release absent; creating a recoverable draft."
  gh release create "$RELEASE_TAG" --draft --verify-tag --generate-notes --title "PyMoviePrint $RELEASE_TAG"
  for attempt in 1 2 3 4 5 6 7 8; do
    release_json="$(read_release)"
    [[ -n "$release_json" ]] && break
    echo "Waiting for new draft release to become list-visible (attempt $attempt/8)"
    sleep 1
  done
  [[ -n "$release_json" ]] || {
    echo "::error::Draft was created, but the release listing did not return it; refusing an unsafe retry"
    exit 1
  }
fi
draft="$(printf '%s' "$release_json" | jq -r '.draft')"
assets="$(printf '%s' "$release_json" | jq -r '[.assets[].name] | join(",")')"
actual_digest="$(printf '%s' "$release_json" | jq -r '.assets[0].digest // ""')"

if [[ "$draft" == "false" ]]; then
  if [[ "$assets" != "PyMoviePrint-Setup.exe" || "$actual_digest" != "$expected_digest" ]]; then
    echo "::error title=Published release integrity mismatch::Published release asset differs from tested executable; refusing mutation (assets=$assets digest=$actual_digest expected=$expected_digest)" >&2
    exit 1
  fi
  echo "Already published and verified: tag=$RELEASE_TAG digest=$expected_digest"
  exit 0
fi
if [[ "$draft" != "true" ]]; then
  echo "::error title=Invalid release state::Expected draft=true/false, got $draft" >&2
  exit 1
fi

if [[ -n "$assets" && "$assets" != "PyMoviePrint-Setup.exe" ]]; then
  echo "::error title=Unexpected draft assets::Draft has $assets; refusing to alter unrelated assets" >&2
  exit 1
fi

if [[ "$assets" == "PyMoviePrint-Setup.exe" && "$actual_digest" == "$expected_digest" ]]; then
  echo "Draft already contains the correct installer. No upload needed."
elif [[ "$assets" == "PyMoviePrint-Setup.exe" ]]; then
  echo "::warning title=Repairing stale draft asset::Reuploading mismatched or incomplete installer in an unpublished draft."
  gh release upload "$RELEASE_TAG" "$installer" --clobber
else
  gh release upload "$RELEASE_TAG" "$installer"
fi

release_json="$(read_release)"
assets="$(printf '%s' "$release_json" | jq -r '[.assets[].name] | join(",")')"
actual_digest="$(printf '%s' "$release_json" | jq -r '.assets[0].digest // ""')"
if [[ "$assets" != "PyMoviePrint-Setup.exe" || "$actual_digest" != "$expected_digest" ]]; then
  echo "::error title=Installer integrity not established::Expected one EXE with $expected_digest; got $assets $actual_digest; draft remains unpublished" >&2
  exit 1
fi

gh release edit "$RELEASE_TAG" --draft=false
release_json="$(read_release)"
draft="$(printf '%s' "$release_json" | jq -r '.draft')"
assets="$(printf '%s' "$release_json" | jq -r '[.assets[].name] | join(",")')"
actual_digest="$(printf '%s' "$release_json" | jq -r '.assets[0].digest // ""')"
if [[ "$draft" != "false" || "$assets" != "PyMoviePrint-Setup.exe" || "$actual_digest" != "$expected_digest" ]]; then
  echo "::error title=Published release failed readback::draft=$draft assets=$assets digest=$actual_digest" >&2
  exit 1
fi

echo "Published and read back verified EXE: tag=$RELEASE_TAG digest=$expected_digest"
