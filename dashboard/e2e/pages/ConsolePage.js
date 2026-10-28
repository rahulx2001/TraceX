import { expect } from "@playwright/test";
import { apiKey } from "../fixtures/env.js";

/** Ops console shell. Waits on locators and URLs, not fixed sleeps. */
export class ConsolePage {
  constructor(page) {
    this.page = page;
    this.body = page.locator("body");
  }

  async seedKey() {
    const key = apiKey();
    await this.page.addInitScript((value) => {
      localStorage.setItem("frontline_api_key", value);
    }, key);
  }

  trackErrors() {
    const errors = [];
    this.page.on("pageerror", (error) => errors.push(String(error)));
    return errors;
  }

  async gotoHash(hash) {
    await this.page.goto(`/ui/#${hash}`);
    await expect(this.body).toBeVisible();
  }

  /** mod+k is Meta or Control. Control works in Chrome on macOS and Linux. */
  async openPalette() {
    await this.page.keyboard.press("Control+k");
    await expect(this.page.getByRole("dialog", { name: "Command palette" })).toBeVisible();
  }

  /**
   * "g" then a letter. pendingG is React state, so the second key must land
   * after a commit. Two animation frames cover that without a fixed sleep.
   */
  async chord(secondKey) {
    await this.page.keyboard.press("g");
    await this.page.evaluate(
      () =>
        new Promise((resolve) => {
          requestAnimationFrame(() => requestAnimationFrame(resolve));
        }),
    );
    await this.page.keyboard.press(secondKey);
  }
}
