import { test, expect } from "@playwright/test";

test("anonymous survey exports a consented CSV without submitting answers to a server", async ({
  page,
}) => {
  const mutations = [];
  page.on("request", (r) => {
    if (r.method() !== "GET") mutations.push(r.url());
  });
  await page.goto("/research/survey.html", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { level: 1 })).toContainText("تتعلّم");
  const submit = page.getByRole("button", {
    name: "تنزيل إجاباتي CSV",
    exact: true,
  });
  await submit.click();
  await expect(page.locator("#consent")).not.toBeChecked();
  await page.locator("#consent").check();
  await page.locator('[name="role"]').selectOption("student");
  await page.locator('[name="fdi_confidence"]').selectOption("3");
  await page.locator('[name="useful_activities"][value="instrument"]').check();
  const download = page.waitForEvent("download");
  await submit.click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(
    /^dentaverse-response-[a-f0-9]{8}\.csv$/,
  );
  const stream = await file.createReadStream();
  let csv = "";
  for await (const chunk of stream) csv += chunk.toString("utf8");
  expect(csv).toContain('"consented"');
  expect(csv).toContain('"yes","student"');
  expect(csv).toContain('"instrument"');
  expect(mutations).toEqual([]);
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
  await expect(page.getByRole("status")).toContainText("برمز");
});
