import { test, expect } from "./fixtures.js";
import { pathToFileURL } from "node:url";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

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
  // Dismiss the native required-field validation bubble before the next input.
  await page.keyboard.press("Escape");
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
  await expect(page.locator("#result")).toContainText("برمز");
});

test("survey presents twelve questions, resets consent and supports narrow screens and print", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/research/survey.html?discussion=1");
  await expect(page.locator("#questions fieldset")).toHaveCount(12);
  await expect(page.locator("#discussion")).toHaveAttribute("open", "");
  await page.locator('[name="role"]').selectOption("student");
  await page.locator('[name="study_year"]').selectOption("3");
  await page.locator('[name="setting"][value="laboratory"]').check();
  await expect(page.locator("#completion")).toHaveJSProperty("value", 2);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.locator("#consent").check();
  await page.getByRole("button", { name: "بدء إجابة جديدة" }).click();
  await expect(page.locator("#consent")).not.toBeChecked();
  await expect(page.locator('[name="role"]')).toHaveValue("");
  await expect(page.locator("#completion")).toHaveJSProperty("value", 0);
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".print-options").first()).toBeVisible();
  await expect(page.locator('[name="role"]')).toBeHidden();
  await expect(page.locator("#discussion")).toBeHidden();
});

test("standalone survey opens offline and exports without external requests", async ({
  page,
}) => {
  await promisify(execFile)(
    ".venv/Scripts/python.exe",
    ["tools/export_survey.py"],
    {
      cwd: "..",
      windowsHide: true,
    },
  );
  const requests = [];
  page.on("request", (request) => {
    if (/^https?:/.test(request.url())) requests.push(request.url());
  });
  await page.goto(
    pathToFileURL(path.resolve("../data/exports/DentaVerse-Survey.html")).href,
  );
  await expect(page.locator("#questions fieldset")).toHaveCount(12);
  await page.locator("#consent").check();
  await page.locator('[name="open_comment"]').fill("=1+1");
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "تنزيل إجاباتي CSV", exact: true })
    .click();
  const file = await download;
  const stream = await file.createReadStream();
  let csv = "";
  for await (const chunk of stream) csv += chunk.toString("utf8");
  expect(csv).toContain('"\'=1+1"');
  expect(requests).toEqual([]);
});
