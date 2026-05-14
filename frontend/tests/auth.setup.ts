import { test as setup } from "@playwright/test"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"

const authFile = "playwright/.auth/user.json"

setup("authenticate", async ({ page }) => {
  await page.goto("/login")
  // Use placeholder as fallback to data-testid
  await page.getByPlaceholder("admin@aegis.com").fill(firstSuperuser)
  await page.getByPlaceholder("••••••••").fill(firstSuperuserPassword)
  await page.getByRole("button", { name: /Đăng nhập/i }).click()
  await page.waitForURL("/")
  await page.evaluate(() => localStorage.setItem("is_logged_in", "true"))
  await page.context().storageState({ path: authFile })
})
