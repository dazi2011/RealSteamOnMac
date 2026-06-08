import assert from "node:assert/strict";
import { createRequire } from "node:module";
import test from "node:test";

const require = createRequire(import.meta.url);
const { decideOverviewPatch } = require("../ui/realsteamonmac_ui.js");

test("normalizes an allowlisted backend-ready invalid-platform app", () => {
  assert.deepEqual(
    decideOverviewPatch({
      allowlisted: true,
      detailsStatus: 9,
      overviewStatus: 14,
      hasAnyLocalContent: false,
    }),
    { normalize: true },
  );
});

test("fails closed while the native backend is still invalid", () => {
  assert.deepEqual(
    decideOverviewPatch({
      allowlisted: true,
      detailsStatus: 14,
      overviewStatus: 14,
      hasAnyLocalContent: false,
    }),
    { normalize: false },
  );
});

test("does not change a non-allowlisted app", () => {
  assert.deepEqual(
    decideOverviewPatch({
      allowlisted: false,
      detailsStatus: 9,
      overviewStatus: 14,
      hasAnyLocalContent: false,
    }),
    { normalize: false },
  );
});

test("does not change an app with local content", () => {
  assert.deepEqual(
    decideOverviewPatch({
      allowlisted: true,
      detailsStatus: 9,
      overviewStatus: 14,
      hasAnyLocalContent: true,
    }),
    { normalize: false },
  );
});

for (const overviewStatus of [3, 4, 5, 7, 9, 10, 11, 12, 13]) {
  test(`preserves active or non-invalid overview status ${overviewStatus}`, () => {
    assert.deepEqual(
      decideOverviewPatch({
        allowlisted: true,
        detailsStatus: 9,
        overviewStatus,
        hasAnyLocalContent: false,
      }),
      { normalize: false },
    );
  });
}
